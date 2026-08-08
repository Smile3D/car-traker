import io
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_actionable_listing, get_owned_listing
from app.models.listing import Listing
from app.models.listing_photo import ListingPhoto
from app.schemas.listing_photo import ListingPhotoOut, ListingPhotoReorderInput, ListingPhotoUploadResult

router = APIRouter(prefix="/listings/{listing_id}/photos", tags=["listing-photos"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_PHOTOS_PER_LISTING = 15
MAX_WIDTH_PX = 1600
WEBP_QUALITY = 80


def _absolute_file_path(relative_path: str) -> Path:
    return Path(settings.upload_dir) / relative_path


def _get_owned_photo_or_404(photo_id: int, listing: Listing, database_session: Session) -> ListingPhoto:
    photo = (
        database_session.query(ListingPhoto)
        .filter(ListingPhoto.id == photo_id, ListingPhoto.listing_id == listing.id)
        .first()
    )
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing photo not found")

    return photo


def _convert_to_webp(contents: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(contents))
    image.verify()
    image = Image.open(io.BytesIO(contents))

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    if image.width > MAX_WIDTH_PX:
        new_height = round(image.height * (MAX_WIDTH_PX / image.width))
        image = image.resize((MAX_WIDTH_PX, new_height), Image.Resampling.LANCZOS)

    return image


@router.post("", response_model=ListingPhotoUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_listing_photos(
    files: list[UploadFile] = File(...),
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> ListingPhotoUploadResult:
    existing_count = (
        database_session.query(ListingPhoto).filter(ListingPhoto.listing_id == listing.id).count()
    )

    listing_upload_dir = Path(settings.upload_dir) / "listing-photos" / str(listing.id)

    created_photos: list[ListingPhoto] = []
    errors: list[str] = []
    next_order = existing_count

    for upload_file in files:
        display_name = upload_file.filename or "photo"

        if existing_count + len(created_photos) >= MAX_PHOTOS_PER_LISTING:
            errors.append(f"'{display_name}': photo limit reached ({MAX_PHOTOS_PER_LISTING} per listing)")
            continue

        if upload_file.content_type not in ALLOWED_CONTENT_TYPES:
            errors.append(f"'{display_name}': unsupported file type. Allowed: jpg, png, webp")
            continue

        contents = await upload_file.read()
        if len(contents) > MAX_UPLOAD_SIZE_BYTES:
            errors.append(f"'{display_name}': file is too large (max 10MB)")
            continue

        try:
            image = _convert_to_webp(contents)
        except UnidentifiedImageError:
            errors.append(f"'{display_name}': not a valid image")
            continue
        except Exception:
            errors.append(f"'{display_name}': could not be processed")
            continue

        listing_upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}.webp"
        relative_path = f"listing-photos/{listing.id}/{filename}"
        image.save(listing_upload_dir / filename, "WEBP", quality=WEBP_QUALITY)

        new_photo = ListingPhoto(listing_id=listing.id, file_path=relative_path, order=next_order)
        database_session.add(new_photo)
        created_photos.append(new_photo)
        next_order += 1

    if created_photos:
        database_session.commit()
        for photo in created_photos:
            database_session.refresh(photo)

    return ListingPhotoUploadResult(
        created=[ListingPhotoOut.model_validate(photo) for photo in created_photos],
        errors=errors,
    )


@router.get("", response_model=list[ListingPhotoOut])
def list_listing_photos(
    listing: Listing = Depends(get_owned_listing),
    database_session: Session = Depends(get_db),
) -> list[ListingPhoto]:
    return (
        database_session.query(ListingPhoto)
        .filter(ListingPhoto.listing_id == listing.id)
        .order_by(ListingPhoto.order)
        .all()
    )


@router.get("/{photo_id}/file")
def get_listing_photo_file(
    photo_id: int,
    listing: Listing = Depends(get_owned_listing),
    database_session: Session = Depends(get_db),
) -> FileResponse:
    photo = _get_owned_photo_or_404(photo_id, listing, database_session)
    absolute_path = _absolute_file_path(photo.file_path)

    if not absolute_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing photo file not found")

    return FileResponse(absolute_path, media_type="image/webp")


@router.patch("/reorder", response_model=list[ListingPhotoOut])
def reorder_listing_photos(
    reorder_input: ListingPhotoReorderInput,
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> list[ListingPhoto]:
    photos = (
        database_session.query(ListingPhoto)
        .filter(ListingPhoto.id.in_(reorder_input.photo_ids), ListingPhoto.listing_id == listing.id)
        .all()
    )
    photos_by_id = {photo.id: photo for photo in photos}

    if len(photos_by_id) != len(reorder_input.photo_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more listing photos not found")

    for new_order, photo_id in enumerate(reorder_input.photo_ids):
        photos_by_id[photo_id].order = new_order

    database_session.commit()

    return sorted(photos_by_id.values(), key=lambda photo: photo.order)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing_photo(
    photo_id: int,
    listing: Listing = Depends(get_actionable_listing),
    database_session: Session = Depends(get_db),
) -> None:
    photo = _get_owned_photo_or_404(photo_id, listing, database_session)

    _absolute_file_path(photo.file_path).unlink(missing_ok=True)

    database_session.delete(photo)
    database_session.commit()
