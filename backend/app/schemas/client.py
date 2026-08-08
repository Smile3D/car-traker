import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ClientType = Literal["seller", "buyer"]
LeadSource = Literal["tiktok", "instagram", "facebook", "referral", "saw_ad_online"]

UKRAINIAN_PHONE_PATTERN = re.compile(r"^(\+380\d{9}|0\d{9})$")


def normalize_and_validate_phone(phone: str) -> str:
    normalized_phone = re.sub(r"[\s\-()]", "", phone)
    if not UKRAINIAN_PHONE_PATTERN.match(normalized_phone):
        raise ValueError("Phone number must be in the format +380XXXXXXXXX or 0XXXXXXXXX")
    return normalized_phone


class ClientCreate(BaseModel):
    listing_id: int
    client_type: ClientType

    name: str = Field(min_length=2, max_length=100)
    phone: str
    email: EmailStr | None = None
    social_media: str | None = None

    stage_id: int | None = None
    notes: str | None = None
    lead_source: LeadSource | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_and_validate_phone(value)


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = None
    email: EmailStr | None = None
    social_media: str | None = None
    stage_id: int | None = None
    employee_id: int | None = None
    notes: str | None = None
    lead_source: LeadSource | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_phone(value)


class ClientDelete(BaseModel):
    """Optional context for why a client was removed — shown to the deleting
    user in the moment only. Not persisted anywhere (no deletion log/journal
    yet — deliberately out of scope, see the future "employee action
    history" feature)."""

    reason: str | None = None


class ClientEmployeeSummary(BaseModel):
    """Minimal responsible-employee info embedded in ClientOut, so the
    frontend can show a name on a client card without a separate
    GET /employees round-trip."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str | None
    last_name: str | None
    email: str


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    listing_id: int
    client_type: ClientType

    name: str
    phone: str
    email: str | None
    social_media: str | None

    stage_id: int
    employee_id: int | None
    employee: ClientEmployeeSummary | None
    notes: str | None
    lead_source: LeadSource | None

    created_at: datetime
