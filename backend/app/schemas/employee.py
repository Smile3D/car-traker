from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.client import normalize_and_validate_phone
from app.schemas.sales_plan import SalesPlanStatus


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    social_links: list[str] | None = None
    position_id: int | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_and_validate_phone(value)


class EmployeeRoleUpdate(BaseModel):
    role: Literal["co_founder", "employee"]


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str | None
    is_active: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    social_links: list[str]
    position_id: int | None
    created_at: datetime


class EmployeeCurrentMonthPlan(BaseModel):
    target_count: int | None
    actual_count: int
    percent: float | None
    status: SalesPlanStatus


class EmployeeStatsOut(BaseModel):
    """Owner-only performance summary for one employee — see
    routers/employees.py:read_employee_stats. total_sold_count/average_check/
    total_profit_brought are sourced from DealHistory (not live Listing rows),
    same reasoning as the Dashboard/Analytics fix: DealHistory survives the
    30-day archive cleanup, live Listing rows for old sold deals don't."""

    started_at: datetime

    total_sold_count: int
    average_check: float | None
    total_profit_brought: float

    current_month_plan: EmployeeCurrentMonthPlan

    # Past months only (current month is still in progress, not yet a
    # pass/fail) — and only months a plan was actually assigned for, since
    # there's nothing to compare actual_count against otherwise.
    plans_completed_count: int
    plans_missed_count: int
    efficiency_rate: float | None
