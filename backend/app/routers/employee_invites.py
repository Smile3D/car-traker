from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee_invite import EmployeeInvite
from app.schemas.employee_invite import InvitePreviewOut

router = APIRouter(prefix="/invites", tags=["employee-invites"])


def _get_valid_invite_or_error(token: str, database_session: Session) -> EmployeeInvite:
    invite = database_session.query(EmployeeInvite).filter(EmployeeInvite.token == token).first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.is_revoked or invite.used_at is not None or invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invite is no longer valid")

    return invite


@router.get("/{token}", response_model=InvitePreviewOut)
def get_invite_preview(token: str, database_session: Session = Depends(get_db)) -> InvitePreviewOut:
    invite = _get_valid_invite_or_error(token, database_session)

    return InvitePreviewOut(
        company_name=invite.company.name,
        position_name=invite.position.name if invite.position is not None else None,
    )
