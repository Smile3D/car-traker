from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_employee, require_company_admin, require_company_member, require_company_owner
from app.models.deal_history import DealHistory
from app.models.employee_invite import EmployeeInvite
from app.models.position import Position
from app.models.sales_plan import SalesPlan
from app.models.user import User
from app.schemas.employee import EmployeeCurrentMonthPlan, EmployeeOut, EmployeeRoleUpdate, EmployeeStatsOut, EmployeeUpdate
from app.schemas.employee_invite import (
    EmployeeInviteCreate,
    EmployeeInviteCreateOut,
    EmployeeInviteOut,
    EmployeeInviteRevokeInput,
    compute_invite_status,
)
from app.services.sales_plan_progress import count_sold_deals, resolve_percent, resolve_status

router = APIRouter(prefix="/employees", tags=["employees"])

INVITE_VALIDITY = timedelta(days=7)


def _get_owned_position_or_404(position_id: int, current_user: User, database_session: Session) -> Position:
    position = (
        database_session.query(Position)
        .filter(Position.id == position_id, Position.company_id == current_user.company_id)
        .first()
    )
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position


# Registered before GET/PATCH /{employee_id} — "invites" would otherwise be
# swallowed by that route's path pattern before FastAPI ever tries to parse
# it as an int and falls through (it doesn't fall through).
@router.post("/invites", response_model=EmployeeInviteCreateOut, status_code=status.HTTP_201_CREATED)
def create_employee_invite(
    invite_create: EmployeeInviteCreate,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> EmployeeInvite:
    if invite_create.position_id is not None:
        _get_owned_position_or_404(invite_create.position_id, current_user, database_session)

    new_invite = EmployeeInvite(
        company_id=current_user.company_id,
        token=uuid4().hex,
        email=invite_create.email,
        position_id=invite_create.position_id,
        created_by=current_user.id,
        expires_at=datetime.now(timezone.utc) + INVITE_VALIDITY,
    )
    database_session.add(new_invite)
    database_session.commit()
    database_session.refresh(new_invite)

    return new_invite


def _invite_out(invite: EmployeeInvite) -> EmployeeInviteOut:
    invite_status = compute_invite_status(invite.is_revoked, invite.used_at, invite.expires_at)
    return EmployeeInviteOut(
        id=invite.id,
        email=invite.email,
        position_id=invite.position_id,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        used_at=invite.used_at,
        is_revoked=invite.is_revoked,
        cancellation_reason=invite.cancellation_reason,
        # Only an active invite's link can still be used — no point (and a
        # needless secret exposure) in returning the token for one that's
        # already used/revoked/expired.
        token=invite.token if invite_status == "active" else None,
    )


@router.get("/invites", response_model=list[EmployeeInviteOut])
def list_employee_invites(
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> list[EmployeeInviteOut]:
    invites = (
        database_session.query(EmployeeInvite)
        .filter(EmployeeInvite.company_id == current_user.company_id)
        .order_by(EmployeeInvite.created_at.desc())
        .all()
    )
    return [_invite_out(invite) for invite in invites]


@router.patch("/invites/{invite_id}/revoke", response_model=EmployeeInviteOut)
def revoke_employee_invite(
    invite_id: int,
    revoke_input: EmployeeInviteRevokeInput,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> EmployeeInviteOut:
    invite = (
        database_session.query(EmployeeInvite)
        .filter(EmployeeInvite.id == invite_id, EmployeeInvite.company_id == current_user.company_id)
        .first()
    )
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revoke an invite that has already been used",
        )

    invite.is_revoked = True
    invite.cancellation_reason = revoke_input.cancellation_reason
    database_session.commit()
    database_session.refresh(invite)

    return _invite_out(invite)


@router.get("", response_model=list[EmployeeOut])
def list_employees(
    include_inactive: bool = Query(False),
    # Viewing the roster is open to any company member (mirrors the owner's
    # view); editing/deactivating an employee or managing invites/positions
    # stays owner-or-co-founder-only via require_company_admin elsewhere in
    # this file.
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[User]:
    employees_query = database_session.query(User).filter(
        User.company_id == current_user.company_id,
        User.role.in_(("employee", "co_founder")),
    )

    if not include_inactive:
        employees_query = employees_query.filter(User.is_active.is_(True))

    return employees_query.order_by(User.created_at.desc()).all()


@router.get("/{employee_id}", response_model=EmployeeOut)
def read_employee(employee: User = Depends(get_owned_employee)) -> User:
    return employee


# get_owned_employee itself already requires require_company_admin (see its
# definition) — an employee gets 403 here even for their own employee_id,
# by design: this is an owner/co-founder-only performance-review view, not a
# self-serve one (and it excludes the caller's own id regardless of role).
@router.get("/{employee_id}/stats", response_model=EmployeeStatsOut)
def read_employee_stats(
    employee: User = Depends(get_owned_employee),
    database_session: Session = Depends(get_db),
) -> EmployeeStatsOut:
    sold_deals = (
        database_session.query(DealHistory)
        .filter(DealHistory.employee_id == employee.id, DealHistory.deal_type == "sold")
        .all()
    )

    total_sold_count = len(sold_deals)
    checks = [deal.final_price for deal in sold_deals if deal.final_price is not None]
    average_check = float(sum(checks) / len(checks)) if checks else None
    total_profit_brought = float(sum(
        (deal.final_price - deal.purchase_price - deal.additional_expenses)
        for deal in sold_deals
        if deal.final_price is not None and deal.purchase_price is not None and deal.additional_expenses is not None
    ))

    current_month_start = date.today().replace(day=1)
    current_month_plan_row = (
        database_session.query(SalesPlan)
        .filter(SalesPlan.employee_id == employee.id, SalesPlan.month == current_month_start)
        .first()
    )
    current_month_target = current_month_plan_row.target_count if current_month_plan_row is not None else None
    current_month_actual = count_sold_deals(employee.id, current_month_start, database_session)
    current_month_plan = EmployeeCurrentMonthPlan(
        target_count=current_month_target,
        actual_count=current_month_actual,
        percent=resolve_percent(current_month_target, current_month_actual),
        status=resolve_status(current_month_target, current_month_actual),
    )

    past_plans = (
        database_session.query(SalesPlan)
        .filter(SalesPlan.employee_id == employee.id, SalesPlan.month < current_month_start)
        .all()
    )
    plans_completed_count = 0
    plans_missed_count = 0
    for plan in past_plans:
        actual_count = count_sold_deals(employee.id, plan.month, database_session)
        if actual_count >= plan.target_count:
            plans_completed_count += 1
        else:
            plans_missed_count += 1

    total_evaluated_months = plans_completed_count + plans_missed_count
    efficiency_rate = (
        round(plans_completed_count / total_evaluated_months * 100) if total_evaluated_months > 0 else None
    )

    return EmployeeStatsOut(
        started_at=employee.created_at,
        total_sold_count=total_sold_count,
        average_check=average_check,
        total_profit_brought=total_profit_brought,
        current_month_plan=current_month_plan,
        plans_completed_count=plans_completed_count,
        plans_missed_count=plans_missed_count,
        efficiency_rate=efficiency_rate,
    )


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_update: EmployeeUpdate,
    employee: User = Depends(get_owned_employee),
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> User:
    update_data = employee_update.model_dump(exclude_unset=True)

    if "is_active" in update_data and employee.role == "co_founder" and current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the company owner can deactivate or reactivate a co-founder's account",
        )

    if update_data.get("position_id") is not None:
        _get_owned_position_or_404(update_data["position_id"], current_user, database_session)

    for field_name, field_value in update_data.items():
        setattr(employee, field_name, field_value)

    database_session.commit()
    database_session.refresh(employee)

    return employee


@router.patch("/{employee_id}/role", response_model=EmployeeOut)
def update_employee_role(
    employee_id: int,
    role_update: EmployeeRoleUpdate,
    current_user: User = Depends(require_company_owner),
    database_session: Session = Depends(get_db),
) -> User:
    if employee_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    employee = (
        database_session.query(User)
        .filter(
            User.id == employee_id,
            User.company_id == current_user.company_id,
            User.role.in_(("employee", "co_founder")),
        )
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change the role of a deactivated employee",
        )

    if role_update.role == "co_founder" and employee.role != "employee":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee is already a co-founder")
    if role_update.role == "employee" and employee.role != "co_founder":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee is not a co-founder")

    employee.role = role_update.role
    database_session.commit()
    database_session.refresh(employee)

    return employee
