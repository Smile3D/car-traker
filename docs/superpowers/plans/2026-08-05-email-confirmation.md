# Email Confirmation for Owner Registration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require email confirmation before a newly registered company owner (`account_type="business"`, no invite token) can log in, via a Resend-sent confirmation link; employee (invite) and individual registrations are unaffected.

**Architecture:** One new backend table (`email_confirmation_tokens`, modeled on the existing `employee_invites` pattern) plus one new boolean on `users`. `POST /auth/register`'s existing business/no-invite branch creates a token and sends an email instead of returning nothing extra; `POST /auth/login` blocks unconfirmed owners with a structured error; two new endpoints (`POST /auth/confirm-email`, `POST /auth/resend-confirmation`) consume/reissue tokens. The frontend gets one new page, one new shared component, and edits to three existing files, all wired through the existing Pinia auth store and `useApi` error-normalization layer.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (backend); Nuxt 4 + Pinia + `@nuxtjs/i18n` + vee-validate (frontend); Resend REST API via `httpx`.

## Global Constraints

- Employee registration via invite token (`invite_token` present) and individual registration (`account_type="individual"`) get **no** email sent and `is_email_confirmed=True` set explicitly at creation — never rely on the column default alone for these paths.
- `RESEND_API_KEY` lives only in env vars (`.env.example` in both `backend/` and repo root, plus `docker-compose.yml`), never hardcoded. If unset, the app must boot normally and `email_service.py` must log the rendered email instead of calling Resend.
- A Resend API failure must never fail registration — log and swallow it.
- `POST /auth/resend-confirmation` always returns the same generic `200` body regardless of whether the email exists, is already confirmed, or is rate-limited (no user enumeration). Rate limit: 60 seconds since the last token was created for that user, checked via a plain query against `email_confirmation_tokens` — no new infrastructure.
- Error responses from the new/changed endpoints use `detail={"message": str, "code": str, ...}` (a dict, not a plain string) — every other existing endpoint keeps returning a plain string `detail` unchanged.
- Every new user-facing string is a translation key added inside the existing `auth` object in both `frontend/locales/uk.json` and `frontend/locales/ru.json` — never a new top-level block, never hardcoded text. Validate both files as JSON after editing.
- No automated tests exist anywhere in this repo today (confirmed: no `tests/` dir, no pytest in `backend/requirements.txt`, no test runner in `frontend/package.json`) and none are being introduced by this plan — out of scope per the approved spec. Every task's "test" step is a manual verification command instead (`curl` against a running `uvicorn`/`nuxt dev`, or `alembic upgrade/downgrade`).

---

### Task 1: `User.is_email_confirmed` + `EmailConfirmationToken` model

**Files:**
- Modify: `backend/app/models/user.py`
- Create: `backend/app/models/email_confirmation_token.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `User.is_email_confirmed: bool`; `EmailConfirmationToken` (fields: `id`, `user_id`, `token`, `created_at`, `expires_at`, `used_at`, relationship `user`).

- [ ] **Step 1: Add `is_email_confirmed` to `User`**

In `backend/app/models/user.py`, add the field right after `is_active` (same section comment style as the file already uses):

```python
    # Lets an owner "fire" an employee (deactivate login/access) without
    # deleting their account, preserving assignment history elsewhere.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    # Only meaningful for role="owner" — employees (via invite) and
    # individual accounts get this set True explicitly at creation, since
    # only a fresh business/owner registration goes through the
    # confirm-email flow (see auth.py::register).
    is_email_confirmed: Mapped[bool] = mapped_column(Boolean, server_default="false")
```

- [ ] **Step 2: Create the `EmailConfirmationToken` model**

Create `backend/app/models/email_confirmation_token.py`:

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EmailConfirmationToken(Base):
    __tablename__ = "email_confirmation_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")
```

- [ ] **Step 3: Register the model in `models/__init__.py`**

In `backend/app/models/__init__.py`, add the import (alphabetically, right after `DealHistory` and before `EmployeeInvite`) and the `__all__` entry:

```python
from app.models.deal_history import DealHistory
from app.models.email_confirmation_token import EmailConfirmationToken
from app.models.employee_invite import EmployeeInvite
```

```python
__all__ = [
    "Car",
    "Client",
    "ClientStage",
    "Company",
    "DealHistory",
    "EmailConfirmationToken",
    "EmployeeInvite",
    ...
]
```

- [ ] **Step 4: Verify it imports cleanly**

Run (from `backend/`, with the venv from `backend/README.md` step 2 active):
```bash
python -c "from app.models import EmailConfirmationToken, User; print(EmailConfirmationToken.__tablename__, User.is_email_confirmed)"
```
Expected: prints `email_confirmation_tokens InstrumentedAttribute(...)` with no import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/user.py backend/app/models/email_confirmation_token.py backend/app/models/__init__.py
git commit -m "Add EmailConfirmationToken model and User.is_email_confirmed"
```

---

### Task 2: Alembic migration (table + column + backfill)

**Files:**
- Create: `backend/alembic/versions/<generated>_add_email_confirmation.py`

**Interfaces:**
- Consumes: `EmailConfirmationToken.__tablename__`, `User.is_email_confirmed` from Task 1 (schema must match exactly).
- Produces: `email_confirmation_tokens` table + `users.is_email_confirmed` column, both present in the DB after `alembic upgrade head`.

- [ ] **Step 1: Generate the migration file**

From `backend/`, with `.env` pointing at a running local Postgres (`backend/README.md` step 1):
```bash
alembic revision -m "add email confirmation"
```
This creates `backend/alembic/versions/<hash>_add_email_confirmation.py` with `down_revision` auto-set to the current head (`107d512ffbb1`, the `add_sales_plans_table` migration — confirmed by grepping every migration's `down_revision` in the repo, nothing else points past it).

- [ ] **Step 2: Fill in `upgrade()`/`downgrade()`**

Replace the generated (empty) `upgrade()`/`downgrade()` bodies with:

```python
def upgrade() -> None:
    op.create_table(
        'email_confirmation_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='email_confirmation_tokens_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='email_confirmation_tokens_pkey'),
    )
    op.create_index(op.f('ix_email_confirmation_tokens_token'), 'email_confirmation_tokens', ['token'], unique=True)

    op.add_column('users', sa.Column('is_email_confirmed', sa.Boolean(), server_default='false', nullable=False))

    # Every user who registered before this feature shipped is already an
    # active, trusted account (owner, employee, or individual) — only
    # owners registering from here on go through the confirm-email flow.
    op.execute("UPDATE users SET is_email_confirmed = true")


def downgrade() -> None:
    op.drop_column('users', 'is_email_confirmed')
    op.drop_index(op.f('ix_email_confirmation_tokens_token'), table_name='email_confirmation_tokens')
    op.drop_table('email_confirmation_tokens')
```

- [ ] **Step 3: Apply and verify**

```bash
alembic upgrade head
psql "$DATABASE_URL" -c "\d email_confirmation_tokens" -c "SELECT is_email_confirmed, count(*) FROM users GROUP BY 1;"
```
Expected: `email_confirmation_tokens` table exists with a unique index on `token`; every existing row shows `is_email_confirmed = t`.

- [ ] **Step 4: Verify the downgrade path**

```bash
alembic downgrade -1 && alembic upgrade head
```
Expected: both commands succeed with no errors (confirms `downgrade()` is not just a stub that would break a future `alembic downgrade`).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "Add email_confirmation_tokens table and users.is_email_confirmed backfill"
```

---

### Task 3: Settings, `.env.example`, `docker-compose.yml`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `/.env.example` (repo root)
- Modify: `docker-compose.yml`

**Interfaces:**
- Produces: `settings.resend_api_key: str | None`, `settings.frontend_url: str` — consumed by Task 4 (email service) and Task 6 (register endpoint).

- [ ] **Step 1: Add the two settings**

In `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    upload_dir: str = "uploads"

    # Used to build the confirm-email link sent to a new company owner
    # ("{frontend_url}/auth/confirm-email?token=..."). Defaults to the same
    # origin already hardcoded as the CORS allow-origin in main.py.
    frontend_url: str = "http://localhost:3000"

    # Optional: without it, email_service.py logs the confirmation email to
    # the console instead of calling Resend — lets the app run locally
    # before a developer has created a Resend account.
    resend_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 2: Update `backend/.env.example`**

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/car_garage_tracker
SECRET_KEY=change-me-to-a-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:3000
RESEND_API_KEY=
```

- [ ] **Step 3: Update root `/.env.example`**

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=car_garage_tracker

DATABASE_URL=postgresql://postgres:postgres@db:5432/car_garage_tracker
SECRET_KEY=change-me-to-a-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:3000
RESEND_API_KEY=

NUXT_PUBLIC_API_BASE_URL=http://localhost:8000
NUXT_API_BASE_URL_INTERNAL=http://backend:8000
```

- [ ] **Step 4: Wire the two new vars into `docker-compose.yml`**

`docker-compose.yml`'s `backend` service only forwards an explicit allowlist of env vars into the container (`DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`) — a var present in `.env` but missing here never reaches `Settings()`. Add the two new ones:

```yaml
  backend:
    build: ./backend
    environment:
      DATABASE_URL: ${DATABASE_URL}
      SECRET_KEY: ${SECRET_KEY}
      ALGORITHM: ${ALGORITHM}
      ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES}
      FRONTEND_URL: ${FRONTEND_URL}
      RESEND_API_KEY: ${RESEND_API_KEY}
```

- [ ] **Step 5: Verify settings load with the var unset**

```bash
cd backend && python -c "from app.config import settings; print(settings.resend_api_key, settings.frontend_url)"
```
Expected: `None http://localhost:3000` (no `RESEND_API_KEY` in the shell env or `.env` yet) — confirms the app doesn't fail to boot without it.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/.env.example .env.example docker-compose.yml
git commit -m "Add FRONTEND_URL and optional RESEND_API_KEY settings"
```

---

### Task 4: `email_service.py` (Resend integration + dev fallback)

**Files:**
- Create: `backend/app/services/email_service.py`

**Interfaces:**
- Consumes: `settings.resend_api_key` (Task 3).
- Produces: `send_confirmation_email(to_email: str, confirmation_link: str, locale: str) -> None` — consumed by Task 6 and Task 8.

- [ ] **Step 1: Write the service**

Create `backend/app/services/email_service.py`:

```python
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "Car Garage Tracker <onboarding@resend.dev>"

_SUBJECT_BY_LOCALE = {
    "uk": "Підтвердіть email — Car Garage Tracker",
    "ru": "Подтвердите email — Car Garage Tracker",
}


def _render_confirmation_email_html(confirmation_link: str, locale: str) -> str:
    if locale == "ru":
        heading = "Подтвердите ваш email"
        body = "Чтобы завершить регистрацию в Car Garage Tracker, подтвердите свой email-адрес."
        button_label = "Подтвердить email"
        fallback_label = "Если кнопка не работает, скопируйте эту ссылку в браузер:"
    else:
        heading = "Підтвердіть ваш email"
        body = "Щоб завершити реєстрацію в Car Garage Tracker, підтвердіть свою email-адресу."
        button_label = "Підтвердити email"
        fallback_label = "Якщо кнопка не працює, скопіюйте це посилання в браузер:"

    return f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>{heading}</h2>
      <p>{body}</p>
      <p>
        <a href="{confirmation_link}" style="display: inline-block; padding: 12px 24px; background: #2563eb; color: #ffffff; text-decoration: none; border-radius: 6px;">
          {button_label}
        </a>
      </p>
      <p style="color: #6b7280; font-size: 13px;">{fallback_label}<br>{confirmation_link}</p>
    </div>
    """


def send_confirmation_email(to_email: str, confirmation_link: str, locale: str) -> None:
    subject = _SUBJECT_BY_LOCALE.get(locale, _SUBJECT_BY_LOCALE["uk"])
    html = _render_confirmation_email_html(confirmation_link, locale)

    if settings.resend_api_key is None:
        logger.warning("RESEND_API_KEY is not set — logging the confirmation email instead of sending it")
        logger.info("Confirmation email for %s | Subject: %s | %s", to_email, subject, html)
        return

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": FROM_ADDRESS, "to": [to_email], "subject": subject, "html": html},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Registration must never fail because Resend is down or misconfigured
        # — the user can always retry via POST /auth/resend-confirmation.
        logger.exception("Failed to send confirmation email to %s via Resend", to_email)
```

- [ ] **Step 2: Verify the dev fallback path (no API key)**

```bash
cd backend && python -c "
from app.services.email_service import send_confirmation_email
send_confirmation_email('owner@example.com', 'http://localhost:3000/auth/confirm-email?token=abc', 'uk')
"
```
Expected: a `WARNING` log line about the missing key, then an `INFO` log line containing the rendered HTML — no exception, no network call.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_service.py
git commit -m "Add Resend-backed confirmation email service with dev-mode fallback"
```

---

### Task 5: `UserCreate.locale` + new auth schemas

**Files:**
- Modify: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/auth.py`

**Interfaces:**
- Produces: `UserCreate.locale: Literal["uk", "ru"]` (default `"uk"`); `ConfirmEmailInput(token: str)`; `ResendConfirmationInput(email: EmailStr)`; `MessageOut(message: str)` — all consumed by Task 6/7/8.

- [ ] **Step 1: Add `locale` to `UserCreate`**

In `backend/app/schemas/user.py`, add a `Locale` type alias next to the existing `AccountType`/`CompanyRole` aliases, and the field on `UserCreate`:

```python
AccountType = Literal["individual", "business"]
CompanyRole = Literal["owner", "employee"]
Locale = Literal["uk", "ru"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    account_type: AccountType = "individual"
    # When set, takes priority over account_type entirely: the new user
    # joins the invite's company as role=employee instead of creating their
    # own Company (see the register() handler for the full flow).
    invite_token: str | None = None
    # Which language the confirmation email (if any is sent) is written in —
    # the frontend passes its current i18n locale; defaults to "uk" for any
    # client that doesn't send one.
    locale: Locale = "uk"
```

- [ ] **Step 2: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr


class ConfirmEmailInput(BaseModel):
    token: str


class ResendConfirmationInput(BaseModel):
    email: EmailStr


class MessageOut(BaseModel):
    message: str
```

- [ ] **Step 3: Verify the schemas import and validate**

```bash
cd backend && python -c "
from app.schemas.user import UserCreate
from app.schemas.auth import ConfirmEmailInput, ResendConfirmationInput, MessageOut
print(UserCreate(email='a@b.com', password='12345678').locale)
print(ConfirmEmailInput(token='x'), ResendConfirmationInput(email='a@b.com'), MessageOut(message='ok'))
"
```
Expected: prints `uk` then the three model reprs, no validation errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/user.py backend/app/schemas/auth.py
git commit -m "Add locale to UserCreate and schemas for confirm-email/resend-confirmation"
```

---

### Task 6: `POST /auth/register` — send confirmation email for owner registrations

**Files:**
- Modify: `backend/app/routers/auth.py`

**Interfaces:**
- Consumes: `EmailConfirmationToken` (Task 1), `send_confirmation_email` (Task 4), `UserCreate.locale` (Task 5), `settings.frontend_url` (Task 3).
- Produces: `_create_confirmation_token(user, database_session) -> EmailConfirmationToken` — reused by Task 8's `resend_confirmation`.

- [ ] **Step 1: Add the new imports and constant**

In `backend/app/routers/auth.py`, update the `datetime` import and add the new imports/constant near the top (alongside the existing `ALLOWED_AVATAR_CONTENT_TYPES` block):

```python
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
from app.models.user import User
from app.schemas.auth import ConfirmEmailInput, MessageOut, ResendConfirmationInput
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.email_service import send_confirmation_email
from app.services.security import create_access_token, hash_password, verify_password
```

```python
EMAIL_CONFIRMATION_TOKEN_VALIDITY = timedelta(hours=24)
RESEND_CONFIRMATION_COOLDOWN = timedelta(seconds=60)
```
(place these two lines right after the existing `AVATAR_SIZE_PX = 512` line)

- [ ] **Step 2: Add the two shared helpers**

Add these right after `_get_valid_invite_or_400`:

```python
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
```

- [ ] **Step 3: Update `register()`**

Replace the body of `register()` from the `if invite is not None:` branch onward:

```python
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
```

- [ ] **Step 4: Verify manually**

With `uvicorn app.main:app --reload --port 8000` running and `RESEND_API_KEY` unset (dev-fallback logging):
```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner1@example.com","password":"password123","account_type":"business","locale":"uk"}' | python -m json.tool
```
Expected: `201` with the created user's JSON; the `uvicorn` console shows the dev-fallback log with a `uk`-language email body and a link containing `/auth/confirm-email?token=`.
```bash
psql "$DATABASE_URL" -c "SELECT is_email_confirmed FROM users WHERE email='owner1@example.com';"
```
Expected: `f` (false) — confirms the owner is not yet confirmed.

Then confirm employee/individual paths are untouched — register an individual account the same way with `"account_type":"individual"` and check `is_email_confirmed` is `t` immediately, with no email logged.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "Send confirmation email on business/owner registration"
```

---

### Task 7: `POST /auth/login` — block unconfirmed owners

**Files:**
- Modify: `backend/app/routers/auth.py`

**Interfaces:**
- Consumes: `User.is_email_confirmed`, `User.role` (Task 1).
- Produces: `403` with `detail={"message": str, "code": "email_not_confirmed", "email": str}` for unconfirmed owners — consumed by frontend Task 15.

- [ ] **Step 1: Add the check in `login()`**

Insert this block right after the existing `is_active` check and before `access_token = create_access_token(...)`:

```python
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
```

- [ ] **Step 2: Verify manually**

Using the `owner1@example.com` account created in Task 6 (still unconfirmed):
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -d "username=owner1@example.com&password=password123" | python -m json.tool
```
Expected: `403` with `{"detail": {"message": "...", "code": "email_not_confirmed", "email": "owner1@example.com"}}`.

Then verify an already-confirmed / non-owner account still logs in normally (e.g. the individual account from Task 6, or any employee account) — expect a normal `200` with `access_token`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "Block login for owners with an unconfirmed email"
```

---

### Task 8: `POST /auth/confirm-email` and `POST /auth/resend-confirmation`

**Files:**
- Modify: `backend/app/routers/auth.py`

**Interfaces:**
- Consumes: `ConfirmEmailInput`, `ResendConfirmationInput`, `MessageOut` (Task 5); `_create_confirmation_token`, `_send_confirmation_email_for_token`, `RESEND_CONFIRMATION_COOLDOWN` (Task 6).
- Produces: the two new endpoints — consumed by frontend Tasks 11, 14.

- [ ] **Step 1: Add both endpoints**

Add these after `login()` and before `read_current_user()`:

```python
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
```

- [ ] **Step 2: Verify `confirm-email` manually**

Grab the token logged in Task 6's dev-fallback output for `owner1@example.com`, then:
```bash
curl -s -X POST http://localhost:8000/auth/confirm-email -H "Content-Type: application/json" \
  -d '{"token":"<paste-token-here>"}' | python -m json.tool
```
Expected: `200` with `{"access_token": "...", "token_type": "bearer"}`.
```bash
curl -s -X POST http://localhost:8000/auth/confirm-email -H "Content-Type: application/json" \
  -d '{"token":"<same-token-again>"}' | python -m json.tool
```
Expected: `400` with `code: "already_used"`.
```bash
curl -s -X POST http://localhost:8000/auth/confirm-email -H "Content-Type: application/json" \
  -d '{"token":"not-a-real-token"}' | python -m json.tool
```
Expected: `404` with `code: "invalid"`.

Then verify `owner1@example.com` can now log in normally (Task 7's `curl` again — expect `200` this time).

- [ ] **Step 3: Verify `resend-confirmation` manually**

Register a fresh business account (`owner2@example.com`, same as Task 6's `curl`), then:
```bash
curl -s -X POST http://localhost:8000/auth/resend-confirmation -H "Content-Type: application/json" \
  -d '{"email":"owner2@example.com"}' | python -m json.tool
curl -s -X POST http://localhost:8000/auth/resend-confirmation -H "Content-Type: application/json" \
  -d '{"email":"owner2@example.com"}' | python -m json.tool
curl -s -X POST http://localhost:8000/auth/resend-confirmation -H "Content-Type: application/json" \
  -d '{"email":"does-not-exist@example.com"}' | python -m json.tool
```
Expected: all three return the identical `200` generic message. The `uvicorn` console shows a second dev-fallback email log for the first call only (the immediate second call is rate-limited — no new log line; the nonexistent email never logs anything).

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "Add POST /auth/confirm-email and POST /auth/resend-confirmation"
```

---

### Task 9: Frontend — `useApi.ts` structured error support

**Files:**
- Modify: `frontend/app/composables/useApi.ts`

**Interfaces:**
- Produces: `ApiError.code?: string`, `ApiError.email?: string` — consumed by Tasks 13, 14, 15.

- [ ] **Step 1: Extend `ApiError` and the normalizer**

```typescript
export interface ApiError {
  statusCode: number
  message: string
  code?: string
  email?: string
}

type RequestOptions = Omit<FetchOptions, 'method' | 'baseURL' | 'body'>
type RequestMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
type RequestBody = FetchOptions['body']

interface ValidationErrorItem {
  msg: string
}

interface StructuredErrorDetail {
  message: string
  code?: string
  email?: string
}

function isStructuredErrorDetail(detail: unknown): detail is StructuredErrorDetail {
  return typeof detail === 'object' && detail !== null && 'message' in detail
}

function normalizeApiError(error: unknown): ApiError {
  if (error instanceof FetchError) {
    const statusCode = error.statusCode ?? 500
    const detail = (error.data as { detail?: unknown } | undefined)?.detail

    if (isStructuredErrorDetail(detail)) {
      return { statusCode, message: detail.message, code: detail.code, email: detail.email }
    }

    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? (detail as ValidationErrorItem[]).map((validationError) => validationError.msg).join(', ')
        : error.message

    return { statusCode, message }
  }

  return { statusCode: 500, message: 'Unexpected error, please try again' }
}
```

(the rest of the file — `useApi()` and its returned methods — is unchanged)

- [ ] **Step 2: Verify with the running backend**

With `npm run dev` running in `frontend/` and the backend from Task 7 still serving the unconfirmed `owner1@example.com` (re-register a fresh unconfirmed owner if it was already confirmed in Task 8), open the browser devtools console on any page and run:
```javascript
const { apiPost } = useApi()
try { await apiPost('/auth/login', new URLSearchParams({ username: 'owner3@example.com', password: 'password123' })) } catch (e) { console.log(e) }
```
Expected: the logged error object has `code: "email_not_confirmed"` and `email: "owner3@example.com"` alongside `message`/`statusCode`.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/composables/useApi.ts
git commit -m "Support structured {message, code, email} error details in useApi"
```

---

### Task 10: Frontend — i18n keys

**Files:**
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

**Interfaces:**
- Produces: the `auth.confirmEmail.*` key namespace — consumed by Tasks 12, 13, 14, 15.

- [ ] **Step 1: Add `auth.confirmEmail` to `uk.json`**

Inside the existing `"auth": { ... }` object, add a new sibling key after `"register"`:

```json
  "auth": {
    "login": { ... unchanged ... },
    "register": { ... unchanged ... },
    "confirmEmail": {
      "checkEmailTitle": "Перевірте пошту",
      "checkEmailBody": "Ми надіслали лист із підтвердженням на {email}. Перейдіть за посиланням у листі, щоб завершити реєстрацію.",
      "resendButton": "Надіслати лист повторно",
      "resendButtonCooldown": "Надіслати повторно через {seconds} с",
      "resendSuccessMessage": "Лист надіслано ще раз",
      "verifying": "Підтверджуємо email…",
      "errorInvalid": "Посилання для підтвердження недійсне.",
      "errorExpired": "Посилання протерміноване. Надішліть новий лист підтвердження.",
      "errorAlreadyUsed": "Email вже підтверджено. Спробуйте увійти.",
      "resendFormPrompt": "Введіть email, щоб отримати нове посилання",
      "loginBlockTitle": "Підтвердіть email, щоб увійти",
      "loginBlockBody": "Лист із підтвердженням надіслано на {email}."
    }
  },
```

- [ ] **Step 2: Add the matching block to `ru.json`**

```json
  "auth": {
    "login": { ... unchanged ... },
    "register": { ... unchanged ... },
    "confirmEmail": {
      "checkEmailTitle": "Проверьте почту",
      "checkEmailBody": "Мы отправили письмо с подтверждением на {email}. Перейдите по ссылке в письме, чтобы завершить регистрацию.",
      "resendButton": "Отправить письмо повторно",
      "resendButtonCooldown": "Отправить повторно через {seconds} с",
      "resendSuccessMessage": "Письмо отправлено ещё раз",
      "verifying": "Подтверждаем email…",
      "errorInvalid": "Ссылка для подтверждения недействительна.",
      "errorExpired": "Ссылка просрочена. Отправьте новое письмо подтверждения.",
      "errorAlreadyUsed": "Email уже подтверждён. Попробуйте войти.",
      "resendFormPrompt": "Введите email, чтобы получить новую ссылку",
      "loginBlockTitle": "Подтвердите email, чтобы войти",
      "loginBlockBody": "Письмо с подтверждением отправлено на {email}."
    }
  },
```

- [ ] **Step 3: Validate both files as JSON**

```bash
python -m json.tool frontend/locales/uk.json > /dev/null && echo OK
python -m json.tool frontend/locales/ru.json > /dev/null && echo OK
```
Expected: `OK` printed twice, no parse errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/locales/uk.json frontend/locales/ru.json
git commit -m "Add auth.confirmEmail i18n keys (uk/ru)"
```

---

### Task 11: Frontend — auth store actions

**Files:**
- Modify: `frontend/app/stores/auth.ts`

**Interfaces:**
- Consumes: `Token`-shaped `{access_token, token_type}` responses from `/auth/confirm-email` (Task 8); `ApiError` (Task 9).
- Produces: `register(...): Promise<{ requiresEmailConfirmation: boolean }>` (changed return type — Task 13 must update its one call site); `confirmEmail(confirmationToken: string): Promise<void>`; `resendConfirmation(email: string): Promise<void>` — consumed by Tasks 12, 13, 14.

- [ ] **Step 1: Update `register()` and add the two new actions**

```typescript
  async function register(email: string, password: string, accountType: AccountType = 'individual', inviteToken?: string, locale?: string): Promise<{ requiresEmailConfirmation: boolean }> {
    const { apiPost } = useApi()
    await apiPost<User>('/auth/register', { email, password, account_type: accountType, invite_token: inviteToken, locale })

    // Only a fresh business/owner registration (no invite) requires
    // confirming the email before the account can be used — everything
    // else auto-logs-in immediately, same as before this feature.
    const requiresEmailConfirmation = accountType === 'business' && !inviteToken
    if (!requiresEmailConfirmation) {
      await login(email, password)
    }

    return { requiresEmailConfirmation }
  }

  async function confirmEmail(confirmationToken: string): Promise<void> {
    const { apiPost } = useApi()
    const tokenResponse = await apiPost<TokenResponse>('/auth/confirm-email', { token: confirmationToken })
    token.value = tokenResponse.access_token

    await fetchCurrentUser()
  }

  async function resendConfirmation(email: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/resend-confirmation', { email })
  }
```

Add `confirmEmail` and `resendConfirmation` to the store's returned object:

```typescript
  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    confirmEmail,
    resendConfirmation,
    fetchCurrentUser,
    updateBusinessProfile,
    updateOwnProfile,
    uploadAvatar,
    deleteAvatar,
    fetchAvatarImageUrl,
    logout
  }
```

- [ ] **Step 2: Verify the store compiles**

```bash
cd frontend && npx nuxi typecheck 2>&1 | grep -i "stores/auth" || echo "no auth.ts errors"
```
Expected: `no auth.ts errors` (Task 13 will still show an error here until it's updated to match the new `register()` return type — that's expected and resolved in Task 13, not this one).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/stores/auth.ts
git commit -m "Add confirmEmail/resendConfirmation actions; register() signals email-confirmation requirement"
```

---

### Task 12: Frontend — `ResendConfirmationButton` shared component

**Files:**
- Create: `frontend/app/components/auth/ResendConfirmationButton.vue`

**Interfaces:**
- Consumes: `authStore.resendConfirmation` (Task 11); `auth.confirmEmail.*` i18n keys (Task 10).
- Produces: `<ResendConfirmationButton :email="string" />` (global component name, no path prefix — matches this project's `{ path: '~/components', pathPrefix: false }` convention) — consumed by Tasks 13, 14, 15.

- [ ] **Step 1: Write the component**

```vue
<script setup lang="ts">
import type { ApiError } from '~/composables/useApi'

const props = defineProps<{ email: string }>()

const COOLDOWN_SECONDS = 60

const authStore = useAuthStore()
const { t } = useI18n()

const isSending = ref(false)
const remainingSeconds = ref(0)
const errorMessage = ref('')
const successMessage = ref('')

let cooldownIntervalId: ReturnType<typeof setInterval> | undefined

function startCooldown(): void {
  remainingSeconds.value = COOLDOWN_SECONDS
  cooldownIntervalId = setInterval(() => {
    remainingSeconds.value -= 1
    if (remainingSeconds.value <= 0 && cooldownIntervalId) {
      clearInterval(cooldownIntervalId)
    }
  }, 1000)
}

onUnmounted(() => {
  if (cooldownIntervalId) {
    clearInterval(cooldownIntervalId)
  }
})

async function handleResend(): Promise<void> {
  errorMessage.value = ''
  successMessage.value = ''
  isSending.value = true

  try {
    await authStore.resendConfirmation(props.email)
    successMessage.value = t('auth.confirmEmail.resendSuccessMessage')
    startCooldown()
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSending.value = false
  }
}
</script>

<template>
  <div>
    <button
      type="button"
      :disabled="isSending || remainingSeconds > 0"
      class="text-sm font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50"
      @click="handleResend"
    >
      {{ remainingSeconds > 0 ? t('auth.confirmEmail.resendButtonCooldown', { seconds: remainingSeconds }) : t('auth.confirmEmail.resendButton') }}
    </button>
    <p v-if="successMessage" class="mt-1 text-xs text-muted-foreground">{{ successMessage }}</p>
    <p v-if="errorMessage" class="mt-1 text-xs text-destructive">{{ errorMessage }}</p>
  </div>
</template>
```

- [ ] **Step 2: Verify it renders**

Temporarily drop `<ResendConfirmationButton email="test@example.com" />` into `frontend/app/pages/login.vue`'s template (anywhere), run `npm run dev`, open `/login` in a browser, and confirm the button renders with the `auth.confirmEmail.resendButton` text, is clickable, and after clicking shows the success message and starts counting down in the cooldown label. Then remove the temporary line (Task 15 adds the real usage).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/auth/ResendConfirmationButton.vue
git commit -m "Add shared ResendConfirmationButton component"
```

---

### Task 13: Frontend — `register.vue` check-email screen

**Files:**
- Modify: `frontend/app/pages/register.vue`

**Interfaces:**
- Consumes: `authStore.register(...): Promise<{ requiresEmailConfirmation: boolean }>` (Task 11); `<ResendConfirmationButton>` (Task 12); `auth.confirmEmail.*` keys (Task 10).

- [ ] **Step 1: Update the script block**

```typescript
const { t, locale } = useI18n()
const validators = createValidators(t)

const errorMessage = ref('')
const isSubmitting = ref(false)
const showCheckEmailScreen = ref(false)
const registeredEmail = ref('')

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
```

(`useI18n()` now also destructures `locale`; everything else above this point is unchanged)

Replace `onSubmit`:

```typescript
const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const { requiresEmailConfirmation } = await authStore.register(
      values.email,
      values.password,
      isBusinessAccount.value ? 'business' : 'individual',
      inviteToken.value,
      locale.value
    )

    if (requiresEmailConfirmation) {
      registeredEmail.value = values.email
      showCheckEmailScreen.value = true
    } else {
      // A soft onboarding nudge — an invited employee lands straight on
      // Settings to fill in their own profile, but nothing else is blocked;
      // this only fires right after this one registration, never on later logins.
      router.push(inviteToken.value ? '/settings' : getPostAuthRedirectPath(authStore.user?.company_id))
    }
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSubmitting.value = false
  }
})
```

- [ ] **Step 2: Update the template**

Wrap the existing `<h2>`/banners/`<form>` block in a `v-if="!showCheckEmailScreen"` template, and add the check-email screen as a sibling. The full template becomes:

```html
<template>
  <div>
    <template v-if="!showCheckEmailScreen">
      <h2 v-if="isForcedBusiness" class="mb-4 text-center text-lg font-semibold text-foreground">
        {{ t('auth.register.businessHeading') }}
      </h2>

      <!-- InviteBanner -->
      <div
        v-if="invitePreview"
        class="mb-4 flex items-start gap-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm text-foreground"
      >
        <UserGroupIcon class="mt-0.5 size-4 shrink-0 text-primary" />
        <span>
          {{ t('auth.register.inviteBanner', { company: invitePreview.company_name || '—' }) }}
          <template v-if="invitePreview.position_name">
            {{ t('auth.register.invitePosition', { position: invitePreview.position_name }) }}
          </template>
        </span>
      </div>

      <!-- InviteInvalidBanner -->
      <div
        v-else-if="isInviteInvalid"
        class="mb-4 flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      >
        <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
        <div>
          <p>{{ t('auth.register.inviteInvalid') }}</p>
          <NuxtLink to="/register" class="font-medium underline">{{ t('auth.register.regularRegisterLink') }}</NuxtLink>
        </div>
      </div>

      <form v-if="!isInviteInvalid" class="space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="email">{{ t('auth.register.emailLabel') }} <RequiredMark /></label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            aria-required="true"
            :aria-invalid="!!emailError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="emailError" class="mt-1 text-xs text-destructive">{{ emailError }}</p>
        </div>

        <div>
          <label class="block text-sm font-medium text-foreground" for="password">{{ t('auth.register.passwordLabel') }} <RequiredMark /></label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            aria-required="true"
            :aria-invalid="!!passwordError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="passwordError" class="mt-1 text-xs text-destructive">{{ passwordError }}</p>
        </div>

        <!-- BusinessAccountCheckbox: hidden entirely when joining via invite —
             company/role are already fully determined by the invite token. -->
        <label v-if="!isForcedBusiness && !inviteToken" class="flex items-center gap-2 text-sm text-foreground">
          <input
            v-model="isBusinessAccount"
            type="checkbox"
            class="size-4 rounded border-border text-primary focus:ring-1 focus:ring-primary"
          >
          {{ t('auth.register.businessCheckbox') }}
        </label>

        <!-- ErrorAlert -->
        <div
          v-if="errorMessage"
          class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <button
          type="submit"
          :disabled="isSubmitting || !meta.valid"
          class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          {{ isSubmitting ? t('auth.register.submitting') : t('auth.register.submit') }}
        </button>

        <p class="text-center text-sm text-muted-foreground">
          {{ t('auth.register.hasAccount') }}
          <NuxtLink to="/login" class="font-medium text-primary hover:underline">{{ t('auth.register.loginLink') }}</NuxtLink>
        </p>
      </form>
    </template>

    <!-- CheckEmailScreen: shown instead of the form once a fresh
         business/owner registration has triggered a confirmation email. -->
    <div v-else class="space-y-4 text-center">
      <h2 class="text-lg font-semibold text-foreground">{{ t('auth.confirmEmail.checkEmailTitle') }}</h2>
      <p class="text-sm text-muted-foreground">{{ t('auth.confirmEmail.checkEmailBody', { email: registeredEmail }) }}</p>
      <ResendConfirmationButton :email="registeredEmail" />
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify the typecheck error from Task 11 is now gone**

```bash
cd frontend && npx nuxi typecheck 2>&1 | grep -i "register.vue" || echo "no register.vue errors"
```
Expected: `no register.vue errors`.

- [ ] **Step 3: Verify manually in the browser**

With `npm run dev` and the backend both running: go to `/register?type=business`, fill in a fresh email/password, submit. Expected: the form is replaced by the "check email" screen showing the submitted email; the resend button works (60s cooldown starts after clicking). Then register a plain individual account (no `?type=business`) and confirm it still redirects straight to `/garage` as before (no check-email screen).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/register.vue
git commit -m "Show check-email screen after business/owner registration"
```

---

### Task 14: Frontend — `/auth/confirm-email` page

**Files:**
- Create: `frontend/app/pages/auth/confirm-email.vue`

**Interfaces:**
- Consumes: `authStore.confirmEmail` (Task 11); `ApiError.code` (Task 9); `<ResendConfirmationButton>` (Task 12); `getPostAuthRedirectPath` (`frontend/app/utils/authRedirect.ts`, unchanged).

- [ ] **Step 1: Write the page**

```vue
<script setup lang="ts">
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const status = ref<'verifying' | 'error'>('verifying')
const errorCode = ref('')
const manualEmail = ref('')

const tokenFromQuery = computed<string | undefined>(() => typeof route.query.token === 'string' ? route.query.token : undefined)

if (tokenFromQuery.value) {
  try {
    await authStore.confirmEmail(tokenFromQuery.value)
    router.push(getPostAuthRedirectPath(authStore.user?.company_id))
  } catch (error) {
    status.value = 'error'
    errorCode.value = (error as ApiError).code ?? 'invalid'
  }
} else {
  status.value = 'error'
  errorCode.value = 'invalid'
}

const errorMessageKey = computed<string>(() => {
  if (errorCode.value === 'expired') return 'auth.confirmEmail.errorExpired'
  if (errorCode.value === 'already_used') return 'auth.confirmEmail.errorAlreadyUsed'
  return 'auth.confirmEmail.errorInvalid'
})
</script>

<template>
  <div class="space-y-4 text-center">
    <p v-if="status === 'verifying'" class="text-sm text-muted-foreground">{{ t('auth.confirmEmail.verifying') }}</p>

    <div v-else class="space-y-3">
      <p class="text-sm text-destructive">{{ t(errorMessageKey) }}</p>

      <div class="space-y-2 text-left">
        <label class="block text-sm font-medium text-foreground" for="manual-email">{{ t('auth.login.emailLabel') }}</label>
        <input
          id="manual-email"
          v-model="manualEmail"
          type="email"
          class="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p class="text-xs text-muted-foreground">{{ t('auth.confirmEmail.resendFormPrompt') }}</p>
        <ResendConfirmationButton v-if="manualEmail" :email="manualEmail" />
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify the success path**

Register a fresh business account via the UI (Task 13), copy the confirmation link from the backend's dev-fallback console log, and open it in the browser. Expected: a brief "verifying" state, then an automatic redirect to `/crm` (or `/garage` if `company_id` is somehow absent), and `authStore.isAuthenticated` is `true`.

- [ ] **Step 3: Verify the error paths**

Visit `/auth/confirm-email` with no `token` query param — expected: the `errorInvalid` message with the manual-email resend form. Visit it again with the same (now used) token from Step 2 — expected: `errorAlreadyUsed`. Visit it with a made-up token — expected: `errorInvalid`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/auth/confirm-email.vue
git commit -m "Add /auth/confirm-email page"
```

---

### Task 15: Frontend — `login.vue` unconfirmed-email block

**Files:**
- Modify: `frontend/app/pages/login.vue`

**Interfaces:**
- Consumes: `ApiError.code`/`ApiError.email` (Task 9); `<ResendConfirmationButton>` (Task 12).

- [ ] **Step 1: Update the script block**

```typescript
const errorMessage = ref('')
const unconfirmedEmail = ref('')
const isSubmitting = ref(false)

const authStore = useAuthStore()
const router = useRouter()

const { meta, handleSubmit } = useForm()

const { value: email, errorMessage: emailError } = useField<string>('email', validators.email, { initialValue: '' })
const { value: password, errorMessage: passwordError } = useField<string>('password', validators.required, { initialValue: '' })

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  unconfirmedEmail.value = ''
  isSubmitting.value = true

  try {
    await authStore.login(values.email, values.password)
    router.push(getPostAuthRedirectPath(authStore.user?.company_id))
  } catch (error) {
    const apiError = error as ApiError
    if (apiError.code === 'email_not_confirmed') {
      unconfirmedEmail.value = apiError.email ?? values.email
    } else {
      errorMessage.value = apiError.message
    }
  } finally {
    isSubmitting.value = false
  }
})
```

- [ ] **Step 2: Update the template**

Replace the existing `<!-- ErrorAlert -->` block with:

```html
    <!-- UnconfirmedEmailBlock -->
    <div
      v-if="unconfirmedEmail"
      class="flex flex-col gap-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm text-foreground"
      role="alert"
    >
      <div>
        <p class="font-medium">{{ t('auth.confirmEmail.loginBlockTitle') }}</p>
        <p class="text-muted-foreground">{{ t('auth.confirmEmail.loginBlockBody', { email: unconfirmedEmail }) }}</p>
      </div>
      <ResendConfirmationButton :email="unconfirmedEmail" />
    </div>

    <!-- ErrorAlert -->
    <div
      v-else-if="errorMessage"
      class="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
      role="alert"
    >
      <ExclamationTriangleIcon class="mt-0.5 size-4 shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>
```

- [ ] **Step 3: Verify manually**

Register a fresh business account (leave it unconfirmed), then try to log in with its credentials on `/login`. Expected: the "confirm your email" block appears (not the generic error), showing the email and a working resend button. Then try logging in with wrong credentials for any account — expected: the plain `errorMessage` alert still appears as before.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/login.vue
git commit -m "Show confirm-email block on login when email_not_confirmed"
```
