from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.car import Car


class FuelRefill(Base):
    __tablename__ = "fuel_refills"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))
    refill_date: Mapped[date] = mapped_column(Date)
    fuel_amount: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    mileage: Mapped[int | None] = mapped_column(nullable=True)
    station_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    car: Mapped["Car"] = relationship("Car", back_populates="fuel_refills")
