from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.position import Position
    from app.models.user import User


class EmployeeInvite(Base):
    __tablename__ = "employee_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))

    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Both fields below are optional hints, not enforced restrictions: the
    # invited person can still register with any email, and gets no
    # position assigned if this is left unset (an owner can set one later).
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, server_default="false")
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship("Company")
    position: Mapped["Position | None"] = relationship("Position")
    created_by_user: Mapped["User"] = relationship("User", foreign_keys=[created_by])
