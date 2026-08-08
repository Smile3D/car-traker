import io
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.company import Company
from app.models.email_confirmation_token import EmailConfirmationToken
from app.models.employee_invite import EmployeeInvite
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ConfirmEmailInput,
    ForgotPasswordInput,
    MessageOut,
    ResendConfirmationInput,
    ResetPasswordInput,
)
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.email_service import send_confirmation_email, send_password_reset_email
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Same limits/allowed types as listing photo and receipt uploads (see
# routers/listing_photos.py, routers/receipts.py) — not shared as a common
# module, matching how those two already duplicate these constants rather
# than importing from one another.
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
AVATAR_WEBP_QUALITY = 80
AVATAR_SIZE_PX = 512

EMAIL_CONFIRMATION_TOKEN_VALIDITY = timedelta(hours=24)
RESEND_CONFIRMATION_COOLDOWN = timedelta(seconds=60)
PASSWORD_RESET_TOKEN_VALIDITY = timedelta(hours=1)
FORGOT_PASSWORD_COOLDOWN = timedelta(minutes=5)

# UserUpdate's field names are the pre-refactor, user-facing names for the
# company profile; they're applied onto the linked Company row, whose
# column names differ slightly ("name" vs "company_name").
USER_UPDATE_TO_COMPANY_FIELD = {
    "company_name": "name",
    "business_phone": "business_phone",
    "business_tax_id": "business_tax_id",
}


def _absolute_avatar_path(relative_path: str) -> Path:
    return Path(settings.upload_dir) / relative_path


def _convert_to_avatar_webp(contents: bytes) -> Image.Image:
    """Same verify/reopen/convert idiom as _convert_to_webp in
    listing_photos.py, plus a center-crop to square (avatars need a fixed
    aspect ratio; listing photos and receipts don't)."""
    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        image = Image.open(io.BytesIO(contents))
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    short_side = min(image.width, image.height)
    left = (image.width - short_side) // 2
    top = (image.height - short_side) // 2
    image = image.crop((left, top, left + short_side, top + short_side))

    if short_side != AVATAR_SIZE_PX:
        image = image.resize((AVATAR_SIZE_PX, AVATAR_SIZE_PX), Image.Resampling.LANCZOS)

    return image


def _get_valid_invite_or_400(invite_token: str, database_session: Session) -> EmployeeInvite:
    invite = database_session.query(EmployeeInvite).filter(EmployeeInvite.token == invite_token).first()
    if invite is None or invite.is_revoked or invite.used_at is not None or invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite link is invalid or has expired",
        )
    return invite


def _create_confirmation_token(user: User, database_session: Session) -> EmailConfirmationToken:
    confirmation_token = EmailConfirmationToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + EMAIL_CONFIRMATION_TOKEN_VALIDITY,
    )
    database_session.add(confirmation_token)
    database_session.commit()
    database_session.refresh(confirmation_token)
    return confirmation_token


def _send_confirmation_email_for_token(user: User, confirmation_token: EmailConfirmationToken, locale: str) -> None:
    confirmation_link = f"{settings.frontend_url}/auth/confirm-email?token={confirmation_token.token}"
    send_confirmation_email(user.email, confirmation_link, locale)


def _create_password_reset_token(user: User, database_session: Session) -> PasswordResetToken:
    password_reset_token = PasswordResetToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_VALIDITY,
    )
    database_session.add(password_reset_token)
    database_session.commit()
    database_session.refresh(password_reset_token)
    return password_reset_token


def _send_password_reset_email_for_token(user: User, password_reset_token: PasswordResetToken, locale: str) -> None:
    reset_link = f"{settings.frontend_url}/auth/reset-password?token={password_reset_token.token}"
    send_password_reset_email(user.email, reset_link, locale)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_create: UserCreate, database_session: Session = Depends(get_db)) -> User:
    existing_user = database_session.query(User).filter(User.email == user_create.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    invite: EmployeeInvite | None = None
    if user_create.invite_token is not None:
        invite = _get_valid_invite_or_400(user_create.invite_token, database_session)

    new_user = User(
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        # An invite token overrides any account_type the client sent — this
        # account joins an existing company, it never creates one.
        account_type=user_create.account_type if invite is None else "individual",
    )
    database_session.add(new_user)
    database_session.flush()

    if invite is not None:
        new_user.company_id = invite.company_id
        new_user.role = "employee"
        new_user.position_id = invite.position_id
        # Accepting an invite is itself sufficient proof of the email —
        # no confirmation email is ever sent for this path.
        new_user.is_email_confirmed = True
        invite.used_at = datetime.now(timezone.utc)
    elif user_create.account_type == "business":
        new_company = Company(owner_user_id=new_user.id)
        database_session.add(new_company)
        database_session.flush()
        new_user.company_id = new_company.id
        new_user.role = "owner"
        # is_email_confirmed stays at its column default (False) — cleared
        # once this owner clicks the confirmation link (see confirm_email()).
    else:
        # Individual (non-company) account — out of scope for email
        # confirmation per the approved spec.
        new_user.is_email_confirmed = True

    database_session.commit()
    database_session.refresh(new_user)

    if invite is None and user_create.account_type == "business":
        confirmation_token = _create_confirmation_token(new_user, database_session)
        _send_confirmation_email_for_token(new_user, confirmation_token, user_create.locale)

    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    database_session: Session = Depends(get_db),
) -> Token:
    user = database_session.query(User).filter(User.email == form_data.username).first()

    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise invalid_credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    if user.role == "owner" and not user.is_email_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Please confirm your email before logging in",
                "code": "email_not_confirmed",
                "email": user.email,
            },
        )

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)


@router.post("/confirm-email", response_model=Token)
def confirm_email(confirm_input: ConfirmEmailInput, database_session: Session = Depends(get_db)) -> Token:
    confirmation_token = (
        database_session.query(EmailConfirmationToken)
        .filter(EmailConfirmationToken.token == confirm_input.token)
        .first()
    )
    if confirmation_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Invalid confirmation link", "code": "invalid"},
        )

    if confirmation_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This confirmation link was already used", "code": "already_used"},
        )

    if confirmation_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This confirmation link has expired", "code": "expired"},
        )

    user = database_session.query(User).filter(User.id == confirmation_token.user_id).first()
    confirmation_token.used_at = datetime.now(timezone.utc)
    user.is_email_confirmed = True
    database_session.commit()

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)


@router.post("/resend-confirmation", response_model=MessageOut)
def resend_confirmation(resend_input: ResendConfirmationInput, database_session: Session = Depends(get_db)) -> MessageOut:
    # Always the same response, regardless of what actually happened below —
    # otherwise the response itself would reveal whether an account with
    # this email exists (user enumeration).
    generic_response = MessageOut(
        message="If this account exists and its email is not yet confirmed, a confirmation email has been sent"
    )

    user = database_session.query(User).filter(User.email == resend_input.email).first()
    if user is None or user.is_email_confirmed:
        return generic_response

    latest_token = (
        database_session.query(EmailConfirmationToken)
        .filter(EmailConfirmationToken.user_id == user.id)
        .order_by(EmailConfirmationToken.created_at.desc())
        .first()
    )
    is_rate_limited = (
        latest_token is not None
        and latest_token.created_at > datetime.now(timezone.utc) - RESEND_CONFIRMATION_COOLDOWN
    )
    if is_rate_limited:
        return generic_response

    if latest_token is not None and latest_token.used_at is None:
        latest_token.used_at = datetime.now(timezone.utc)
        database_session.commit()

    confirmation_token = _create_confirmation_token(user, database_session)
    _send_confirmation_email_for_token(user, confirmation_token, "uk")

    return generic_response


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(forgot_password_input: ForgotPasswordInput, database_session: Session = Depends(get_db)) -> MessageOut:
    # Always the same response, regardless of what actually happened below —
    # otherwise the response itself would reveal whether an account with
    # this email exists (user enumeration).
    generic_response = MessageOut(message="If this account exists, a password reset email has been sent")

    user = database_session.query(User).filter(User.email == forgot_password_input.email).first()
    if user is None:
        return generic_response

    latest_token = (
        database_session.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    is_rate_limited = (
        latest_token is not None
        and latest_token.created_at > datetime.now(timezone.utc) - FORGOT_PASSWORD_COOLDOWN
    )
    if is_rate_limited:
        return generic_response

    if latest_token is not None and latest_token.used_at is None:
        latest_token.used_at = datetime.now(timezone.utc)
        database_session.commit()

    password_reset_token = _create_password_reset_token(user, database_session)
    _send_password_reset_email_for_token(user, password_reset_token, forgot_password_input.locale)

    return generic_response


@router.post("/reset-password", response_model=MessageOut)
def reset_password(reset_password_input: ResetPasswordInput, database_session: Session = Depends(get_db)) -> MessageOut:
    password_reset_token = (
        database_session.query(PasswordResetToken)
        .filter(PasswordResetToken.token == reset_password_input.token)
        .first()
    )
    if password_reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Invalid password reset link", "code": "invalid"},
        )

    if password_reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This password reset link was already used", "code": "already_used"},
        )

    if password_reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This password reset link has expired", "code": "expired"},
        )

    user = database_session.query(User).filter(User.id == password_reset_token.user_id).first()
    password_reset_token.used_at = datetime.now(timezone.utc)
    user.hashed_password = hash_password(reset_password_input.new_password)
    database_session.commit()

    return MessageOut(message="Password has been reset successfully")


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> User:
    update_data = user_update.model_dump(exclude_unset=True)

    # Company fields (owner/employee's shared company profile) vs. own-profile
    # fields (first/last name, phone, social links) — the latter apply to any
    # logged-in user, company member or not, unlike the former.
    company_update_data = {
        field_name: field_value for field_name, field_value in update_data.items()
        if field_name in USER_UPDATE_TO_COMPANY_FIELD
    }
    profile_update_data = {
        field_name: field_value for field_name, field_value in update_data.items()
        if field_name not in USER_UPDATE_TO_COMPANY_FIELD
    }

    if company_update_data and current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only members of a company can update company profile fields",
        )

    if company_update_data:
        company = database_session.query(Company).filter(Company.id == current_user.company_id).first()
        for field_name, field_value in company_update_data.items():
            setattr(company, USER_UPDATE_TO_COMPANY_FIELD[field_name], field_value)

    for field_name, field_value in profile_update_data.items():
        setattr(current_user, field_name, field_value)

    if company_update_data or profile_update_data:
        database_session.commit()
        database_session.refresh(current_user)

    return current_user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> User:
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: jpg, png, webp",
        )

    contents = await file.read()
    if len(contents) > MAX_AVATAR_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large (max 10MB)",
        )

    image = _convert_to_avatar_webp(contents)

    avatar_upload_dir = Path(settings.upload_dir) / "avatars" / str(current_user.id)
    avatar_upload_dir.mkdir(parents=True, exist_ok=True)

    # Delete the previous avatar file (if any) only after the new one is
    # validated/processed, so a bad upload never destroys a working avatar.
    previous_avatar_url = current_user.avatar_url

    filename = f"{uuid4()}.webp"
    relative_path = f"avatars/{current_user.id}/{filename}"
    image.save(avatar_upload_dir / filename, "WEBP", quality=AVATAR_WEBP_QUALITY)

    current_user.avatar_url = relative_path
    database_session.commit()
    database_session.refresh(current_user)

    if previous_avatar_url is not None:
        _absolute_avatar_path(previous_avatar_url).unlink(missing_ok=True)

    return current_user


@router.delete("/me/avatar", response_model=UserRead)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> User:
    if current_user.avatar_url is not None:
        _absolute_avatar_path(current_user.avatar_url).unlink(missing_ok=True)
        current_user.avatar_url = None
        database_session.commit()
        database_session.refresh(current_user)

    return current_user


@router.get("/me/avatar/file")
def get_avatar_file(current_user: User = Depends(get_current_user)) -> FileResponse:
    if current_user.avatar_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")

    absolute_path = _absolute_avatar_path(current_user.avatar_url)
    if not absolute_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file not found")

    return FileResponse(absolute_path, media_type="image/webp")
