from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_admin, require_company_member
from app.models.sales_plan import SalesPlan
from app.models.user import User
from app.schemas.sales_plan import SalesPlanProgressOut, SalesPlanUpsertInput
from app.services.sales_plan_progress import count_sold_deals, parse_year_month, resolve_percent, resolve_status

router = APIRouter(prefix="/sales-plans", tags=["sales-plans"])


def _progress_row(employee: User, plan: SalesPlan | None, actual_count: int) -> SalesPlanProgressOut:
    target_count = plan.target_count if plan is not None else None
    return SalesPlanProgressOut(
        sales_plan_id=plan.id if plan is not None else None,
        employee_id=employee.id,
        employee_first_name=employee.first_name,
        employee_last_name=employee.last_name,
        employee_email=employee.email,
        is_company_total=False,
        target_count=target_count,
        actual_count=actual_count,
        percent=resolve_percent(target_count, actual_count),
        status=resolve_status(target_count, actual_count),
    )


@router.post("", response_model=SalesPlanProgressOut, status_code=status.HTTP_201_CREATED)
def upsert_sales_plan(
    plan_input: SalesPlanUpsertInput,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> SalesPlanProgressOut:
    employee = (
        database_session.query(User)
        .filter(
            User.id == plan_input.employee_id,
            User.company_id == current_user.company_id,
            User.role == "employee",
        )
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    month_start = parse_year_month(plan_input.month)

    plan = (
        database_session.query(SalesPlan)
        .filter(SalesPlan.employee_id == employee.id, SalesPlan.month == month_start)
        .first()
    )

    if plan is not None:
        plan.target_count = plan_input.target_count
        plan.created_by = current_user.id
    else:
        plan = SalesPlan(
            company_id=current_user.company_id,
            employee_id=employee.id,
            month=month_start,
            target_count=plan_input.target_count,
            created_by=current_user.id,
        )
        database_session.add(plan)

    database_session.commit()
    database_session.refresh(plan)

    actual_count = count_sold_deals(employee.id, month_start, database_session)
    return _progress_row(employee, plan, actual_count)


@router.get("", response_model=list[SalesPlanProgressOut])
def list_sales_plans(
    month: str | None = Query(None, description="YYYY-MM, defaults to the current month"),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[SalesPlanProgressOut]:
    month_start = parse_year_month(month) if month is not None else date.today().replace(day=1)

    if current_user.role == "employee":
        target_employees = [current_user]
    else:
        target_employees = (
            database_session.query(User)
            .filter(
                User.company_id == current_user.company_id,
                User.role == "employee",
                User.is_active.is_(True),
            )
            .order_by(User.created_at.desc())
            .all()
        )

    plans_by_employee_id = {
        plan.employee_id: plan
        for plan in (
            database_session.query(SalesPlan)
            .filter(SalesPlan.company_id == current_user.company_id, SalesPlan.month == month_start)
            .all()
        )
    }

    rows = [
        _progress_row(employee, plans_by_employee_id.get(employee.id), count_sold_deals(employee.id, month_start, database_session))
        for employee in target_employees
    ]

    # Owner-only aggregate row, appended last — always the sum of the
    # individual rows above (never a separately stored/queried figure), so it
    # can never drift out of sync with them.
    if current_user.role != "employee":
        individual_targets = [row.target_count for row in rows if row.target_count is not None]
        company_target = sum(individual_targets) if individual_targets else None
        company_actual = sum(row.actual_count for row in rows)
        rows.append(SalesPlanProgressOut(
            sales_plan_id=None,
            employee_id=None,
            employee_first_name=None,
            employee_last_name=None,
            employee_email=None,
            is_company_total=True,
            target_count=company_target,
            actual_count=company_actual,
            percent=resolve_percent(company_target, company_actual),
            status=resolve_status(company_target, company_actual),
        ))

    return rows


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_plan(
    plan_id: int,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> None:
    plan = (
        database_session.query(SalesPlan)
        .filter(SalesPlan.id == plan_id, SalesPlan.company_id == current_user.company_id)
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales plan not found")

    database_session.delete(plan)
    database_session.commit()
