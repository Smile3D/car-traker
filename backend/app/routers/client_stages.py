from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_member
from app.models.client import Client
from app.models.client_stage import ClientStage
from app.models.user import User
from app.schemas.client import ClientType
from app.schemas.client_stage import (
    ClientStageCreate,
    ClientStageOut,
    ClientStageReorderInput,
    ClientStageUpdate,
)

router = APIRouter(prefix="/client-stages", tags=["client-stages"])

DEFAULT_SELLER_STAGE_NAMES: list[str] = ["Перший контакт", "Огляд авто", "Узгодження умов", "Авто прийнято", "Угода завершена"]
DEFAULT_BUYER_STAGE_NAMES: list[str] = ["Лід", "Перегляд авто", "Переговори", "Резерв", "Угода закрита", "Відмова"]


def default_stage_names_for_client_type(client_type: ClientType) -> list[str]:
    return DEFAULT_SELLER_STAGE_NAMES if client_type == "seller" else DEFAULT_BUYER_STAGE_NAMES


def ensure_default_stages(company_id: int, client_type: ClientType, database_session: Session) -> None:
    existing_count = (
        database_session.query(ClientStage)
        .filter(ClientStage.company_id == company_id, ClientStage.client_type == client_type)
        .count()
    )
    if existing_count > 0:
        return

    for order, stage_name in enumerate(default_stage_names_for_client_type(client_type)):
        database_session.add(ClientStage(company_id=company_id, client_type=client_type, name=stage_name, order=order))
    # Flush only — no commit here. This is a shared helper called from
    # within other endpoints' own transactions (e.g. POST /listings, which
    # must commit the listing + seller client + default stages together, or
    # not at all); committing here would break that atomicity. Callers that
    # use this as their only write (list_client_stages) commit explicitly.
    database_session.flush()


def get_owned_client_stage(stage_id: int, current_user: User, database_session: Session) -> ClientStage:
    stage = (
        database_session.query(ClientStage)
        .filter(ClientStage.id == stage_id, ClientStage.company_id == current_user.company_id)
        .first()
    )
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client stage not found")
    return stage


@router.get("", response_model=list[ClientStageOut])
def list_client_stages(
    client_type: ClientType = Query(...),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[ClientStage]:
    ensure_default_stages(current_user.company_id, client_type, database_session)
    database_session.commit()
    return (
        database_session.query(ClientStage)
        .filter(ClientStage.company_id == current_user.company_id, ClientStage.client_type == client_type)
        .order_by(ClientStage.order)
        .all()
    )


@router.post("", response_model=ClientStageOut, status_code=status.HTTP_201_CREATED)
def create_client_stage(
    stage_create: ClientStageCreate,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> ClientStage:
    max_order = (
        database_session.query(func.max(ClientStage.order))
        .filter(ClientStage.company_id == current_user.company_id, ClientStage.client_type == stage_create.client_type)
        .scalar()
    )
    next_order = (max_order + 1) if max_order is not None else 0

    new_stage = ClientStage(
        company_id=current_user.company_id,
        client_type=stage_create.client_type,
        name=stage_create.name,
        order=next_order,
    )
    database_session.add(new_stage)
    database_session.commit()
    database_session.refresh(new_stage)

    return new_stage


@router.patch("/reorder", response_model=list[ClientStageOut])
def reorder_client_stages(
    reorder_input: ClientStageReorderInput,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[ClientStage]:
    stages = (
        database_session.query(ClientStage)
        .filter(ClientStage.id.in_(reorder_input.stage_ids), ClientStage.company_id == current_user.company_id)
        .all()
    )
    stages_by_id = {stage.id: stage for stage in stages}

    if len(stages_by_id) != len(reorder_input.stage_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more client stages not found")

    for new_order, stage_id in enumerate(reorder_input.stage_ids):
        stages_by_id[stage_id].order = new_order

    database_session.commit()

    return sorted(stages_by_id.values(), key=lambda stage: stage.order)


@router.patch("/{stage_id}", response_model=ClientStageOut)
def update_client_stage(
    stage_id: int,
    stage_update: ClientStageUpdate,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> ClientStage:
    stage = get_owned_client_stage(stage_id, current_user, database_session)
    stage.name = stage_update.name
    database_session.commit()
    database_session.refresh(stage)

    return stage


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_stage(
    stage_id: int,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> None:
    stage = get_owned_client_stage(stage_id, current_user, database_session)

    has_clients = (
        database_session.query(Client)
        .filter(Client.stage_id == stage.id)
        .first()
        is not None
    )
    if has_clients:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a client stage that still has clients assigned to it",
        )

    database_session.delete(stage)
    database_session.commit()
