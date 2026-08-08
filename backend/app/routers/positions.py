from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_admin, require_company_member
from app.models.position import Position
from app.models.user import User
from app.schemas.position import PositionCreate, PositionOut, PositionUpdate

router = APIRouter(prefix="/positions", tags=["positions"])


def _get_owned_position_or_404(position_id: int, current_user: User, database_session: Session) -> Position:
    position = (
        database_session.query(Position)
        .filter(Position.id == position_id, Position.company_id == current_user.company_id)
        .first()
    )
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return position


@router.get("", response_model=list[PositionOut])
def list_positions(
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[Position]:
    return (
        database_session.query(Position)
        .filter(Position.company_id == current_user.company_id)
        .order_by(Position.name)
        .all()
    )


@router.post("", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def create_position(
    position_create: PositionCreate,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> Position:
    new_position = Position(company_id=current_user.company_id, name=position_create.name)
    database_session.add(new_position)
    database_session.commit()
    database_session.refresh(new_position)

    return new_position


@router.patch("/{position_id}", response_model=PositionOut)
def update_position(
    position_id: int,
    position_update: PositionUpdate,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> Position:
    position = _get_owned_position_or_404(position_id, current_user, database_session)
    position.name = position_update.name

    database_session.commit()
    database_session.refresh(position)

    return position


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: int,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> None:
    position = _get_owned_position_or_404(position_id, current_user, database_session)

    has_assigned_employees = (
        database_session.query(User)
        .filter(User.position_id == position.id)
        .first()
        is not None
    )
    if has_assigned_employees:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a position that is still assigned to employees. Assign them a different position first.",
        )

    database_session.delete(position)
    database_session.commit()
