from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SalesPlan(Base):
    """One employee's monthly target (count of cars to sell). The company-wide
    total is never stored — it's always the sum of these rows for a given
    month, computed on read (see routers/sales_plans.py), so it can never
    drift out of sync with the individual plans."""

    __tablename__ = "sales_plans"

    __table_args__ = (
        UniqueConstraint("employee_id", "month", name="uq_sales_plans_employee_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Always the 1st of the month (e.g. date(2026, 8, 1)) — no existing
    # month-period convention elsewhere in this codebase, so this is the
    # simplest option: a plain Date, always normalized to day=1.
    month: Mapped[date] = mapped_column(Date)

    target_count: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
