from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

InviteStatus = Literal["active", "used", "revoked", "expired"]


def compute_invite_status(is_revoked: bool, used_at: datetime | None, expires_at: datetime) -> InviteStatus:
    if is_revoked:
        return "revoked"
    if used_at is not None:
        return "used"
    if expires_at < datetime.now(timezone.utc):
        return "expired"
    return "active"


class InvitePreviewOut(BaseModel):
    """What GET /invites/{token} returns to an unauthenticated visitor —
    deliberately minimal, no email/token/company id."""

    company_name: str | None
    position_name: str | None


class EmployeeInviteCreate(BaseModel):
    email: str | None = None
    position_id: int | None = None


class EmployeeInviteRevokeInput(BaseModel):
    cancellation_reason: str | None = None


class EmployeeInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    position_id: int | None
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    is_revoked: bool
    cancellation_reason: str | None
    # None once the invite is no longer active (used/revoked/expired) — the
    # link it would build is already dead, so there's nothing to re-copy.
    # Built explicitly by the router (never via from_attributes) so a stale
    # invite's token can't leak into the list response by accident.
    token: str | None = None

    @computed_field
    @property
    def status(self) -> InviteStatus:
        return compute_invite_status(self.is_revoked, self.used_at, self.expires_at)


class EmployeeInviteCreateOut(EmployeeInviteOut):
    """Only returned once, right after creation — a freshly created invite
    is always active, so the token is always present here."""

    token: str
