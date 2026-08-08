from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Client(Base):
    __tablename__ = "clients"

    # A listing may have at most one seller-type client AND at most one
    # buyer-type client — each enforced independently via its own partial
    # unique index (plain unique on listing_id alone would incorrectly
    # couple the two caps together).
    __table_args__ = (
        Index(
            "ix_clients_unique_seller_per_listing",
            "listing_id",
            unique=True,
            postgresql_where=text("client_type = 'seller'"),
        ),
        Index(
            "ix_clients_unique_buyer_per_listing",
            "listing_id",
            unique=True,
            postgresql_where=text("client_type = 'buyer'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))

    client_type: Mapped[str] = mapped_column(String(20))

    name: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_media: Mapped[str | None] = mapped_column(Text, nullable=True)

    stage_id: Mapped[int] = mapped_column(ForeignKey("client_stages.id"))
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nullable — existing clients predate this field and are never
    # backfilled; applies identically regardless of client_type (seller or
    # buyer), since the source of the lead doesn't depend on their role.
    lead_source: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # viewonly: lets ClientOut embed {id, first_name, last_name} without a
    # separate GET /employees round-trip from the frontend.
    employee: Mapped["User | None"] = relationship("User", foreign_keys=[employee_id], viewonly=True)
