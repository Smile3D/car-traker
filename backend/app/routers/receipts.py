import io
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_owned_car
from app.models.car import Car
from app.models.fuel_refill import FuelRefill
from app.models.receipt import Receipt
from app.models.service_record import ServiceRecord
from app.schemas.receipt import ReceiptLinkInput, ReceiptOut

router = APIRouter(prefix="/cars/{car_id}/receipts", tags=["receipts"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
WEBP_QUALITY = 80


def _get_owned_receipt_or_404(receipt_id: int, car: Car, database_session: Session) -> Receipt:
    receipt = (
        database_session.query(Receipt)
        .filter(Receipt.id == receipt_id, Receipt.car_id == car.id)
        .first()
    )
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    return receipt


def _absolute_file_path(relative_path: str) -> Path:
    return Path(settings.upload_dir) / relative_path


def _validate_receipt_link(
    service_record_id: int | None,
    fuel_refill_id: int | None,
    car: Car,
    database_session: Session,
) -> None:
    try:
        ReceiptLinkInput(service_record_id=service_record_id, fuel_refill_id=fuel_refill_id)
    except ValidationError as validation_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(validation_error)
        ) from validation_error

    if service_record_id is not None:
        service_record = (
            database_session.query(ServiceRecord)
            .filter(ServiceRecord.id == service_record_id, ServiceRecord.car_id == car.id)
            .first()
        )
        if service_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service record not found")

    if fuel_refill_id is not None:
        fuel_refill = (
            database_session.query(FuelRefill)
            .filter(FuelRefill.id == fuel_refill_id, FuelRefill.car_id == car.id)
            .first()
        )
        if fuel_refill is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel refill not found")


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    file: UploadFile = File(...),
    description: str | None = Form(None),
    service_record_id: int | None = Form(None),
    fuel_refill_id: int | None = Form(None),
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> Receipt:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: jpg, png, webp",
        )

    _validate_receipt_link(service_record_id, fuel_refill_id, car, database_session)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large (max 10MB)",
        )

    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        image = Image.open(io.BytesIO(contents))
    except UnidentifiedImageError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    car_upload_dir = Path(settings.upload_dir) / "receipts" / str(car.id)
    car_upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4()}.webp"
    relative_path = f"receipts/{car.id}/{filename}"
    image.save(car_upload_dir / filename, "WEBP", quality=WEBP_QUALITY)

    new_receipt = Receipt(
        car_id=car.id,
        file_path=relative_path,
        description=description,
        service_record_id=service_record_id,
        fuel_refill_id=fuel_refill_id,
    )
    database_session.add(new_receipt)
    database_session.commit()
    database_session.refresh(new_receipt)

    return new_receipt


@router.get("", response_model=list[ReceiptOut])
def list_receipts(
    service_record_id: int | None = None,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> list[Receipt]:
    receipts_query = database_session.query(Receipt).filter(Receipt.car_id == car.id)

    if service_record_id is not None:
        receipts_query = receipts_query.filter(Receipt.service_record_id == service_record_id)

    return receipts_query.order_by(Receipt.uploaded_at.desc()).all()


@router.get("/{receipt_id}/file")
def get_receipt_file(
    receipt_id: int,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> FileResponse:
    receipt = _get_owned_receipt_or_404(receipt_id, car, database_session)
    absolute_path = _absolute_file_path(receipt.file_path)

    if not absolute_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt file not found")

    return FileResponse(absolute_path, media_type="image/webp")


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(
    receipt_id: int,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> None:
    receipt = _get_owned_receipt_or_404(receipt_id, car, database_session)

    _absolute_file_path(receipt.file_path).unlink(missing_ok=True)

    database_session.delete(receipt)
    database_session.commit()
