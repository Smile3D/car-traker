from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.car import Car
    from app.models.service_record_item import ServiceRecordItem


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))
    record_type: Mapped[str] = mapped_column(String(20), server_default="maintenance")
    service_date: Mapped[date] = mapped_column(Date)
    mileage: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    car: Mapped["Car"] = relationship("Car", back_populates="service_records")
    items: Mapped[list["ServiceRecordItem"]] = relationship(
        "ServiceRecordItem", back_populates="service_record", cascade="all, delete-orphan"
    )

    @property
    def total_cost(self) -> Decimal:
        return sum((item.price for item in self.items), Decimal("0"))
