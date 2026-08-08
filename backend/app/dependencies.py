import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.car import Car
from app.models.client import Client
from app.models.listing import Listing
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.listing_authorization import ensure_employee_can_act_on_listing
from app.services.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    database_session: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        token_payload = TokenPayload.model_validate(payload)
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        raise credentials_exception

    user = database_session.query(User).filter(User.email == token_payload.subject).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    return user


def get_owned_car(
    car_id: int,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Car:
    car = (
        database_session.query(Car)
        .filter(Car.id == car_id, Car.user_id == current_user.id)
        .first()
    )
    if car is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")

    return car


def require_company_member(current_user: User = Depends(get_current_user)) -> User:
    """Gate for CRM data endpoints: owner and employee both pass, as long
    as they belong to a company. Granular per-role permissions on top of
    this are not implemented yet."""
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available to members of a company",
        )

    return current_user


def require_company_owner(current_user: User = Depends(require_company_member)) -> User:
    """Gate for employee-management and company-settings endpoints: owner only."""
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available to the company owner",
        )

    return current_user


def require_company_admin(current_user: User = Depends(require_company_member)) -> User:
    """Gate for endpoints owner AND co-founder may use — everything that used
    to be owner-only except role assignment and deactivating a co-founder's
    account (those two stay on require_company_owner, strictly)."""
    if current_user.role not in ("owner", "co_founder"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available to the company owner or a co-founder",
        )

    return current_user


def get_owned_listing(
    listing_id: int,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> Listing:
    listing = (
        database_session.query(Listing)
        .filter(Listing.id == listing_id, Listing.company_id == current_user.company_id)
        .first()
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    return listing


def get_actionable_listing(
    listing: Listing = Depends(get_owned_listing),
    current_user: User = Depends(require_company_member),
) -> Listing:
    """Same company-scoped lookup as get_owned_listing, plus the employee
    ownership gate — use this instead of get_owned_listing on any endpoint
    that WRITES to a listing (or its photos); keep get_owned_listing on
    read-only endpoints, since employees can still view every company
    listing, just not act on someone else's."""
    seller_employee_id = listing.seller.employee_id if listing.seller is not None else None
    ensure_employee_can_act_on_listing(seller_employee_id, current_user)
    return listing


def get_owned_client(
    client_id: int,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> Client:
    client = (
        database_session.query(Client)
        .filter(Client.id == client_id, Client.company_id == current_user.company_id)
        .first()
    )
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return client


def get_owned_employee(
    employee_id: int,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> User:
    employee = (
        database_session.query(User)
        .filter(
            User.id == employee_id,
            User.company_id == current_user.company_id,
            User.role.in_(("employee", "co_founder")),
            User.id != current_user.id,
        )
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    return employee
