from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.fuel_refill import FuelRefill
    from app.models.receipt import Receipt
    from app.models.service_record import ServiceRecord
    from app.models.user import User


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    brand: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    year: Mapped[str] = mapped_column(String(255))
    mileage: Mapped[str] = mapped_column(String(255))
    vin: Mapped[str] = mapped_column(String(255))
    fuel_type: Mapped[str] = mapped_column(String(20), server_default="petrol")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="cars")
    service_records: Mapped[list["ServiceRecord"]] = relationship(
        "ServiceRecord", back_populates="car", cascade="all, delete-orphan"
    )
    fuel_refills: Mapped[list["FuelRefill"]] = relationship(
        "FuelRefill", back_populates="car", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        "Receipt", back_populates="car", cascade="all, delete-orphan"
    )