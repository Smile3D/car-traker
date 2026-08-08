from calendar import monthrange
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deal_history import DealHistory
from app.schemas.sales_plan import SalesPlanStatus

"""Shared plan-vs-actual math, used by both GET /sales-plans and
GET /employees/{id}/stats — kept in one place so the two never compute
"was this month's plan met" differently."""


def parse_year_month(value: str) -> date:
    try:
        year_str, month_str = value.split("-")
        return date(int(year_str), int(month_str), 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be in YYYY-MM format")


def month_date_range(month_start: date) -> tuple[date, date]:
    last_day = monthrange(month_start.year, month_start.month)[1]
    return month_start, month_start.replace(day=last_day)


def count_sold_deals(employee_id: int, month_start: date, database_session: Session) -> int:
    month_first_day, month_last_day = month_date_range(month_start)
    return (
        database_session.query(DealHistory)
        .filter(
            DealHistory.employee_id == employee_id,
            DealHistory.deal_type == "sold",
            DealHistory.date_closed >= month_first_day,
            DealHistory.date_closed <= month_last_day,
        )
        .count()
    )


def resolve_status(target_count: int | None, actual_count: int) -> SalesPlanStatus:
    if target_count is None:
        return "no_plan"
    return "completed" if actual_count >= target_count else "in_progress"


def resolve_percent(target_count: int | None, actual_count: int) -> float | None:
    if not target_count:
        return None
    return round(actual_count / target_count * 100)
