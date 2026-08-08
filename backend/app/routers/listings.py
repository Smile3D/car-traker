from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_actionable_listing, get_owned_listing, require_company_member
from app.models.client import Client
from app.models.client_stage import ClientStage
from app.models.deal_history import DealHistory
from app.models.listing import Listing
from app.models.user import User
from app.routers.client_stages import ensure_default_stages
from app.schemas.listing import (
    ListingBulkDeleteInput,
    ListingBulkDeleteResult,
    ListingCreate,
    ListingDelete,
    ListingOut,
    ListingStatus,
    ListingUpdate,
    MarkListingOnServiceInput,
    MarkListingSoldInput,
)
from app.services.listing_authorization import is_listing_locked_for_employee

router = APIRouter(prefix="/listings", tags=["listings"])

SELLER_FIELD_NAMES = {
    "seller_name",
    "seller_phone",
    "seller_email",
    "seller_social_media",
    "seller_lead_source",
    "employee_id",
}


def _get_owned_active_employee_or_error(employee_id: int, current_user: User, database_session: Session) -> User:
    employee = (
        database_session.query(User)
        .filter(User.id == employee_id, User.company_id == current_user.company_id, User.role == "employee")
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot assign an inactive employee",
        )
    return employee


def _validate_discount_amount(listing: Listing) -> None:
    if listing.discount_amount is not None and listing.discount_amount > listing.sale_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Discount amount cannot exceed the sale price",
        )


def _employee_display_name(employee: User) -> str:
    full_name = " ".join(part for part in (employee.first_name, employee.last_name) if part)
    return full_name or employee.email


def _record_deal_history(listing: Listing, deal_type: str, database_session: Session) -> None:
    """Snapshots the listing/seller/buyer/employee data as it stands right
    now — plain copied values, not references (except employee_id, which is
    deliberately also kept live for future per-employee stats). Called once,
    right at the moment a listing closes; never updated afterwards even if
    the underlying Listing/Client/User rows change or are deleted later."""
    seller_client = (
        database_session.query(Client)
        .filter(Client.listing_id == listing.id, Client.client_type == "seller")
        .first()
    )
    assert seller_client is not None

    buyer_client = (
        database_session.query(Client)
        .filter(Client.listing_id == listing.id, Client.client_type == "buyer")
        .first()
    )

    employee: User | None = None
    if seller_client.employee_id is not None:
        employee = database_session.query(User).filter(User.id == seller_client.employee_id).first()

    deal_history_entry = DealHistory(
        company_id=listing.company_id,
        listing_id=listing.id,
        deal_type=deal_type,
        brand=listing.brand,
        model=listing.model,
        year=listing.year,
        vin=listing.vin,
        seller_name=seller_client.name,
        seller_phone=seller_client.phone,
        buyer_name=buyer_client.name if buyer_client is not None else None,
        buyer_phone=buyer_client.phone if buyer_client is not None else None,
        seller_lead_source=seller_client.lead_source,
        buyer_lead_source=buyer_client.lead_source if buyer_client is not None else None,
        final_price=(listing.sale_price - (listing.discount_amount or 0)) if deal_type == "sold" else None,
        purchase_price=listing.purchase_price,
        additional_expenses=listing.additional_expenses,
        date_added=listing.date_added,
        employee_name=_employee_display_name(employee) if employee is not None else None,
        employee_id=employee.id if employee is not None else None,
        date_closed=listing.date_sold if listing.date_sold is not None else date.today(),
    )
    database_session.add(deal_history_entry)


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing_create: ListingCreate,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> Listing:
    listing_data = listing_create.model_dump(exclude=SELLER_FIELD_NAMES)
    date_added = listing_data.pop("date_added")

    new_listing = Listing(**listing_data, company_id=current_user.company_id)
    if date_added is not None:
        new_listing.date_added = date_added

    # Both the listing and its seller client are created in the same
    # transaction (no commit happens until the very end) — if creating
    # either one fails, get_db's session.close() rolls back everything
    # that was staged, so a listing is never left without its seller.
    database_session.add(new_listing)
    database_session.flush()

    ensure_default_stages(current_user.company_id, "seller", database_session)
    first_seller_stage = (
        database_session.query(ClientStage)
        .filter(ClientStage.company_id == current_user.company_id, ClientStage.client_type == "seller")
        .order_by(ClientStage.order)
        .first()
    )
    assert first_seller_stage is not None

    if current_user.role == "employee":
        # Employees always self-assign — any employee_id in the request body
        # is ignored, since only owners may assign listings to other employees.
        assigned_employee_id = current_user.id
    else:
        assigned_employee_id = None
        if listing_create.employee_id is not None:
            assigned_employee_id = _get_owned_active_employee_or_error(
                listing_create.employee_id, current_user, database_session
            ).id

    seller_client = Client(
        company_id=current_user.company_id,
        listing_id=new_listing.id,
        client_type="seller",
        name=listing_create.seller_name,
        phone=listing_create.seller_phone,
        email=listing_create.seller_email,
        social_media=listing_create.seller_social_media,
        lead_source=listing_create.seller_lead_source,
        stage_id=first_seller_stage.id,
        employee_id=assigned_employee_id,
    )
    database_session.add(seller_client)

    database_session.commit()
    database_session.refresh(new_listing)

    return new_listing


@router.post("/bulk-delete", response_model=ListingBulkDeleteResult)
def bulk_delete_listings(
    bulk_delete_input: ListingBulkDeleteInput,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> ListingBulkDeleteResult:
    listings_to_consider = (
        database_session.query(Listing)
        .options(joinedload(Listing.seller))
        .filter(Listing.id.in_(bulk_delete_input.ids), Listing.company_id == current_user.company_id)
        .all()
    )

    deletable_ids: list[int] = []
    skipped_messages: list[str] = []
    for listing in listings_to_consider:
        seller_employee_id = listing.seller.employee_id if listing.seller is not None else None
        if is_listing_locked_for_employee(seller_employee_id, current_user):
            skipped_messages.append(
                f"Лот «{listing.brand} {listing.model}» закріплений за іншим співробітником і був пропущений"
            )
            continue
        deletable_ids.append(listing.id)

    deleted_count = 0
    if deletable_ids:
        deleted_count = (
            database_session.query(Listing)
            .filter(Listing.id.in_(deletable_ids))
            .delete(synchronize_session=False)
        )
        database_session.commit()

    return ListingBulkDeleteResult(deleted_count=deleted_count, deleted_ids=deletable_ids, skipped=skipped_messages)


@router.get("", response_model=list[ListingOut])
def list_listings(
    status_filter: ListingStatus | None = Query(None, alias="status"),
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> list[Listing]:
    # joinedload avoids an N+1 (one seller + one employee lookup per listing)
    # — ListingOut embeds seller.employee_id/seller.employee so the frontend
    # can filter "my own listings" (Analytics, for an employee) and show the
    # responsible manager's name (Archive) without a separate round-trip.
    listings_query = (
        database_session.query(Listing)
        .options(joinedload(Listing.seller).joinedload(Client.employee))
        .filter(Listing.company_id == current_user.company_id)
    )

    if status_filter is not None:
        listings_query = listings_query.filter(Listing.status == status_filter)

    return listings_query.order_by(Listing.created_at.desc()).all()


@router.get("/{listing_id}", response_model=ListingOut)
def read_listing(listing: Listing = Depends(get_owned_listing)) -> Listing:
    return listing


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_update: ListingUpdate,
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> Listing:
    previous_status = listing.status

    for field_name, field_value in listing_update.model_dump(exclude_unset=True).items():
        setattr(listing, field_name, field_value)

    _validate_discount_amount(listing)

    # Entering "reserved" requires a buyer Client to already exist for this
    # listing — there's no Listing.buyer_id column; the buyer relationship
    # is (and was already, before this feature) entirely represented by a
    # Client row with client_type='buyer' scoped to this listing_id (see
    # _record_deal_history below, which already reads it the same way).
    # Leaving "reserved" for something else is untouched — same as any other
    # status transition, the buyer Client (if any) simply stays as-is.
    if previous_status != "reserved" and listing.status == "reserved":
        buyer_exists = (
            database_session.query(Client)
            .filter(Client.listing_id == listing.id, Client.client_type == "buyer")
            .first()
            is not None
        )
        if not buyer_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неможливо забронювати лот без покупця",
            )

    # "sold" only ever happens through mark_listing_sold below — the create/
    # edit form's status dropdown never even offers it as an option for a
    # listing that isn't already sold.
    if previous_status != "removed" and listing.status == "removed":
        listing.archived_at = datetime.now(timezone.utc)
        database_session.flush()
        _record_deal_history(listing, "removed", database_session)

    database_session.commit()
    database_session.refresh(listing)

    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
    delete_request: ListingDelete | None = Body(default=None),
) -> None:
    # delete_request.reason (if provided) is intentionally not persisted —
    # see ListingDelete's docstring.
    database_session.delete(listing)
    database_session.commit()


@router.post("/{listing_id}/mark-sold", response_model=ListingOut)
def mark_listing_sold(
    mark_sold_input: MarkListingSoldInput,
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> Listing:
    if mark_sold_input.final_sale_price is not None:
        # final_sale_price arrives as a plain float (MarkListingSoldInput),
        # but sale_price is a Numeric/Decimal column — assigning the float
        # directly leaves it as a float in memory until the next DB refresh,
        # so the very next line's discount_amount arithmetic below (already
        # a Decimal, loaded from the DB) would raise
        # `unsupported operand type(s) for -: 'float' and 'decimal.Decimal'`
        # the moment a listing with a discount_amount gets a custom final price.
        listing.sale_price = Decimal(str(mark_sold_input.final_sale_price))

    listing.status = "sold"
    listing.date_sold = date.today()
    listing.archived_at = datetime.now(timezone.utc)

    database_session.flush()
    _record_deal_history(listing, "sold", database_session)

    database_session.commit()
    database_session.refresh(listing)

    return listing


@router.post("/{listing_id}/mark-on-service", response_model=ListingOut)
def mark_listing_on_service(
    mark_on_service_input: MarkListingOnServiceInput,
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> Listing:
    listing.status = "on_service"
    listing.service_note = mark_on_service_input.service_note
    listing.service_start_date = mark_on_service_input.service_start_date
    listing.service_expected_end_date = mark_on_service_input.service_expected_end_date

    database_session.commit()
    database_session.refresh(listing)

    return listing


@router.post("/{listing_id}/return-to-work", response_model=ListingOut)
def return_listing_to_work(
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> Listing:
    """Flips status back to active — service_note/service_start_date/
    service_expected_end_date are deliberately left as-is (history of the
    completed service stay), not cleared. See Listing.service_note."""
    listing.status = "active"

    database_session.commit()
    database_session.refresh(listing)

    return listing
