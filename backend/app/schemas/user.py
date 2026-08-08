from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.client import normalize_and_validate_phone

AccountType = Literal["individual", "business"]
CompanyRole = Literal["owner", "co_founder", "employee"]
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


class UserUpdate(BaseModel):
    company_name: str | None = None
    business_phone: str | None = None
    business_tax_id: str | None = None

    # Own-profile fields — available to any logged-in user regardless of
    # company membership, unlike the company fields above (owner/employee
    # editing another employee's profile goes through /employees/{id} instead).
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    social_links: list[str] | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_phone(value)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    business_phone: str | None
    business_tax_id: str | None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    account_type: AccountType
    company_id: int | None
    role: CompanyRole | None
    company: CompanyRead | None
    first_name: str | None
    last_name: str | None
    phone: str | None
    social_links: list[str]
    avatar_url: str | None
    created_at: datetime
