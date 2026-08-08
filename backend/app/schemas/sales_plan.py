from typing import Literal

from pydantic import BaseModel, Field

SalesPlanStatus = Literal["no_plan", "in_progress", "completed"]


class SalesPlanUpsertInput(BaseModel):
    employee_id: int
    month: str = Field(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    target_count: int = Field(gt=0)


class SalesPlanProgressOut(BaseModel):
    """One row of GET /sales-plans — either a real employee's plan/progress,
    or (owner only, appended last) the synthetic company-wide aggregate row
    with employee_* fields null and is_company_total=True."""

    sales_plan_id: int | None
    employee_id: int | None
    employee_first_name: str | None
    employee_last_name: str | None
    employee_email: str | None
    is_company_total: bool

    target_count: int | None
    actual_count: int
    percent: float | None
    status: SalesPlanStatus
