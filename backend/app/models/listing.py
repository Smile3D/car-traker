from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.listing_photo import ListingPhoto


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))

    brand: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    year: Mapped[str] = mapped_column(String(255))
    mileage: Mapped[str] = mapped_column(String(255))
    vin: Mapped[str | None] = mapped_column(String(255), nullable=True)

    body_type: Mapped[str] = mapped_column(String(100))
    transmission: Mapped[str] = mapped_column(String(100))
    engine: Mapped[str] = mapped_column(String(100))
    fuel_type: Mapped[str] = mapped_column(String(20), server_default="petrol")
    color: Mapped[str] = mapped_column(String(100))

    condition: Mapped[str] = mapped_column(String(20), server_default="used")
    condition_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trim_level: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    additional_expenses: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    date_added: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_sold: Mapped[date | None] = mapped_column(Date, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(20), server_default="draft")

    # Populated when a listing goes on_service (see mark_listing_on_service);
    # deliberately left untouched when it leaves on_service again — this is
    # the history of when/why it was there, not a live "currently on service" flag.
    service_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    service_expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    photos: Mapped[list["ListingPhoto"]] = relationship(
        "ListingPhoto", back_populates="listing", cascade="all, delete-orphan", order_by="ListingPhoto.order"
    )

    # viewonly, at most one row (enforced by Client's partial unique index on
    # listing_id where client_type='seller') — lets ListingOut embed
    # {id, employee_id} without a separate per-listing query from the caller.
    seller: Mapped["Client | None"] = relationship(
        "Client",
        primaryjoin="and_(Listing.id == Client.listing_id, Client.client_type == 'seller')",
        viewonly=True,
        uselist=False,
    )
