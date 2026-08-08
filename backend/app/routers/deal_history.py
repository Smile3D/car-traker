from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_member
from app.models.deal_history import DealHistory
from app.models.user import User
from app.schemas.deal_history import DealHistoryOut, DealType

router = APIRouter(prefix="/deal-history", tags=["deal-history"])


# Read-only, deliberately — no PATCH/DELETE endpoints exist for this entity.
# It's meant to be an indestructible log; the only way rows disappear is if
# the company itself is gone (no ON DELETE for company_id currently needed
# since companies aren't deleted in this app).
@router.get("", response_model=list[DealHistoryOut])
def list_deal_history(
    deal_type: DealType | None = Query(None),
    employee_id: int | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[DealHistory]:
    deal_history_query = database_session.query(DealHistory).filter(DealHistory.company_id == current_user.company_id)

    # An employee only ever sees their own deals — this overrides whatever
    # employee_id might have been passed in, it's not just a default.
    if current_user.role == "employee":
        deal_history_query = deal_history_query.filter(DealHistory.employee_id == current_user.id)
    elif employee_id is not None:
        deal_history_query = deal_history_query.filter(DealHistory.employee_id == employee_id)

    if deal_type is not None:
        deal_history_query = deal_history_query.filter(DealHistory.deal_type == deal_type)

    if search:
        like_pattern = f"%{search}%"
        deal_history_query = deal_history_query.filter(
            or_(DealHistory.seller_name.ilike(like_pattern), DealHistory.buyer_name.ilike(like_pattern))
        )

    return deal_history_query.order_by(DealHistory.date_closed.desc(), DealHistory.id.desc()).all()
