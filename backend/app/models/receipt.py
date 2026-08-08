from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.car import Car
    from app.models.fuel_refill import FuelRefill
    from app.models.service_record import ServiceRecord


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    service_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_records.id", ondelete="SET NULL"), nullable=True
    )
    fuel_refill_id: Mapped[int | None] = mapped_column(
        ForeignKey("fuel_refills.id", ondelete="SET NULL"), nullable=True
    )

    car: Mapped["Car"] = relationship("Car", back_populates="receipts")
    service_record: Mapped["ServiceRecord | None"] = relationship("ServiceRecord")
    fuel_refill: Mapped["FuelRefill | None"] = relationship("FuelRefill")
