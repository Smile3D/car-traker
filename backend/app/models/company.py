from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # USD/UAH reference rate shown in the header — purely informational,
    # nothing in the system converts or stores amounts in USD. "auto" pulls
    # from PrivatBank (cached_auto_rate/_fetched_at, refreshed on read when
    # stale); "manual" uses manual_rate, typed in by the owner.
    rate_source: Mapped[str] = mapped_column(String(10), server_default="auto")
    manual_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    cached_auto_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    cached_auto_rate_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
