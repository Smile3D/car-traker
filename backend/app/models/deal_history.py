from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DealHistory(Base):
    """An indestructible log of closed deals (sold/removed) — a snapshot at
    the moment of closing, not a live view. Deleting the Listing (or the
    seller/employee involved) never deletes this row, only nulls out the
    listing_id/employee_id references (ON DELETE SET NULL); the copied
    text/number fields are what actually survives for good."""

    __tablename__ = "deal_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))

    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    deal_type: Mapped[str] = mapped_column(String(20))

    brand: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    year: Mapped[str] = mapped_column(String(255))
    vin: Mapped[str | None] = mapped_column(String(255), nullable=True)

    seller_name: Mapped[str] = mapped_column(Text)
    seller_phone: Mapped[str] = mapped_column(Text)
    buyer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_phone: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Snapshot of Client.lead_source at the moment the deal closed — nullable,
    # never backfilled (mirrors lead_source itself having no backfill on
    # Client), so only deals closed after this field existed will have it set.
    seller_lead_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    buyer_lead_source: Mapped[str | None] = mapped_column(String(30), nullable=True)

    final_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    additional_expenses: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # employee_name is the display-name snapshot (always shown); employee_id
    # is a live reference kept only so a future "deals closed per employee"
    # stat can group by id (reliable) instead of by name (can collide/change).
    employee_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    date_closed: Mapped[date] = mapped_column(Date)
    date_added: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
