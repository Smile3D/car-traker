from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.service_record import ServiceRecord


class ServiceRecordItem(Base):
    __tablename__ = "service_record_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_record_id: Mapped[int] = mapped_column(ForeignKey("service_records.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    service_record: Mapped["ServiceRecord"] = relationship("ServiceRecord", back_populates="items")
