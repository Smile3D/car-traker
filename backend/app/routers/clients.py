from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_client, require_company_member
from app.models.client import Client
from app.models.client_stage import ClientStage
from app.models.listing import Listing
from app.models.user import User
from app.routers.client_stages import ensure_default_stages
from app.schemas.client import ClientCreate, ClientDelete, ClientOut, ClientType, ClientUpdate
from app.services.listing_authorization import ensure_employee_can_act_on_listing

router = APIRouter(prefix="/clients", tags=["clients"])


def _get_owned_listing_or_404(listing_id: int, current_user: User, database_session: Session) -> Listing:
    listing = (
        database_session.query(Listing)
        .filter(Listing.id == listing_id, Listing.company_id == current_user.company_id)
        .first()
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


def _get_owned_client_stage_or_404(stage_id: int, current_user: User, database_session: Session) -> ClientStage:
    stage = (
        database_session.query(ClientStage)
        .filter(ClientStage.id == stage_id, ClientStage.company_id == current_user.company_id)
        .first()
    )
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client stage not found")
    return stage


def _resolve_stage_for_create(client_create: ClientCreate, current_user: User, database_session: Session) -> ClientStage:
    if client_create.stage_id is not None:
        stage = _get_owned_client_stage_or_404(client_create.stage_id, current_user, database_session)
        if stage.client_type != client_create.client_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Client stage does not belong to client_type '{client_create.client_type}'",
            )
        return stage

    ensure_default_stages(current_user.company_id, client_create.client_type, database_session)
    first_stage = (
        database_session.query(ClientStage)
        .filter(ClientStage.company_id == current_user.company_id, ClientStage.client_type == client_create.client_type)
        .order_by(ClientStage.order)
        .first()
    )
    assert first_stage is not None
    return first_stage


def _get_owned_employee_or_404(employee_id: int, current_user: User, database_session: Session) -> User:
    employee = (
        database_session.query(User)
        .filter(User.id == employee_id, User.company_id == current_user.company_id, User.role == "employee")
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


def _ensure_listing_has_no_seller(listing_id: int, database_session: Session) -> None:
    existing_seller = (
        database_session.query(Client)
        .filter(Client.listing_id == listing_id, Client.client_type == "seller")
        .first()
    )
    if existing_seller is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This listing already has a seller client",
        )


# Mirrors _ensure_listing_has_no_seller — same one-per-listing cap, now
# enforced for buyers too. Defense in depth alongside the DB-level partial
# unique index (ix_clients_unique_buyer_per_listing); this check exists so
# the API returns a clear 409 instead of surfacing a raw IntegrityError.
def _ensure_listing_has_no_buyer(listing_id: int, database_session: Session) -> None:
    existing_buyer = (
        database_session.query(Client)
        .filter(Client.listing_id == listing_id, Client.client_type == "buyer")
        .first()
    )
    if existing_buyer is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У цього лота вже є покупець",
        )


# Defense in depth for a direct API request bypassing the UI — the frontend's
# primary safeguard is hiding sold/removed listings from the buyer form's
# listing selector entirely (they're closed deals, adding a buyer to one
# makes no sense).
def _ensure_listing_not_archived_for_buyer(listing: Listing) -> None:
    if listing.status in ("sold", "removed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо додати покупця до вже закритого лота",
        )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    client_create: ClientCreate,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> Client:
    listing = _get_owned_listing_or_404(client_create.listing_id, current_user, database_session)

    if client_create.client_type == "seller":
        _ensure_listing_has_no_seller(client_create.listing_id, database_session)
    elif client_create.client_type == "buyer":
        _ensure_listing_not_archived_for_buyer(listing)
        _ensure_listing_has_no_buyer(client_create.listing_id, database_session)

    stage = _resolve_stage_for_create(client_create, current_user, database_session)

    client_data = client_create.model_dump(exclude={"stage_id"})
    new_client = Client(**client_data, company_id=current_user.company_id, stage_id=stage.id)
    database_session.add(new_client)
    database_session.commit()
    database_session.refresh(new_client)

    return new_client


@router.get("", response_model=list[ClientOut])
def list_clients(
    client_type: ClientType | None = Query(None),
    employee_id: int | None = Query(None),
    listing_id: int | None = Query(None),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[Client]:
    clients_query = database_session.query(Client).filter(Client.company_id == current_user.company_id)

    if client_type is not None:
        clients_query = clients_query.filter(Client.client_type == client_type)

    if employee_id is not None:
        clients_query = clients_query.filter(Client.employee_id == employee_id)

    if listing_id is not None:
        clients_query = clients_query.filter(Client.listing_id == listing_id)

    return clients_query.order_by(Client.created_at.desc()).all()


@router.get("/{client_id}", response_model=ClientOut)
def read_client(client: Client = Depends(get_owned_client)) -> Client:
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_update: ClientUpdate,
    client: Client = Depends(get_owned_client),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> Client:
    if client.client_type == "seller":
        ensure_employee_can_act_on_listing(client.employee_id, current_user)

    update_data = client_update.model_dump(exclude_unset=True)

    if update_data.get("stage_id") is not None:
        stage = _get_owned_client_stage_or_404(update_data["stage_id"], current_user, database_session)
        if stage.client_type != client.client_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Client stage does not belong to client_type '{client.client_type}'",
            )

    if "employee_id" in update_data and update_data["employee_id"] is not None:
        _get_owned_employee_or_404(update_data["employee_id"], current_user, database_session)

    for field_name, field_value in update_data.items():
        setattr(client, field_name, field_value)

    database_session.commit()
    database_session.refresh(client)

    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client: Client = Depends(get_owned_client),
    database_session: Session = Depends(get_db),
    delete_request: ClientDelete | None = Body(default=None),
) -> None:
    # delete_request.reason (if provided) is intentionally not persisted —
    # see ClientDelete's docstring.
    database_session.delete(client)
    database_session.commit()
