from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.car import Car
    from app.models.company import Company


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), server_default="individual")

    # NULL for accounts not part of any company (individual accounts, or a
    # business account that hasn't been linked yet). `role` only means
    # anything when `company_id` is set: 'owner' created the company,
    # 'employee' was invited into it (invite mechanism is a future prompt).
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # The owner defines the company's own list of position names (see the
    # Position model); an employee is assigned one of those, rather than
    # typing a free-text job title.
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)

    # Lets an owner "fire" an employee (deactivate login/access) without
    # deleting their account, preserving assignment history elsewhere.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    # Only meaningful for role="owner" — employees (via invite) and
    # individual accounts get this set True explicitly at creation, since
    # only a fresh business/owner registration goes through the
    # confirm-email flow (see auth.py::register).
    is_email_confirmed: Mapped[bool] = mapped_column(Boolean, server_default="false")

    # Profile fields, relevant mainly to role=employee (shown on the CRM's
    # employee card and on the responsible-employee line of a Client card),
    # but general/nullable so they don't force a meaning onto owner or
    # individual accounts.
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default=text("'[]'::json"))

    # Relative path under settings.upload_dir (e.g. "avatars/{id}/{uuid}.webp"),
    # same convention as ListingPhoto.file_path/Receipt.file_path — not a
    # directly usable URL, fetched via the authenticated GET /auth/me/avatar/file.
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cars: Mapped[list["Car"]] = relationship("Car", back_populates="owner")
    # viewonly: Company.owner_user_id is a separate FK back to users.id, so
    # this relationship is explicitly scoped to company_id to avoid ambiguity.
    company: Mapped["Company | None"] = relationship("Company", foreign_keys=[company_id], viewonly=True)
