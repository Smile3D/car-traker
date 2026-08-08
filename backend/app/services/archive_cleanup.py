import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.listing import Listing

logger = logging.getLogger(__name__)

ARCHIVED_STATUSES = ("sold", "removed")


def _delete_listing_photo_files(listing_id: int) -> None:
    listing_upload_dir = Path(settings.upload_dir) / "listing-photos" / str(listing_id)
    shutil.rmtree(listing_upload_dir, ignore_errors=True)


def _delete_expired_listing(listing_id: int) -> bool:
    """Each expired listing gets its own session/transaction — one listing's
    failure must not roll back or block the rest of the run. DealHistory is
    never touched here: it's already independent of Listing via ON DELETE
    SET NULL on employee_id, and Client/ListingPhoto rows cascade-delete at
    the DB level once the Listing row itself is deleted."""
    database_session: Session = SessionLocal()
    try:
        listing = database_session.query(Listing).filter(Listing.id == listing_id).first()
        if listing is None:
            return False

        _delete_listing_photo_files(listing.id)
        database_session.delete(listing)
        database_session.commit()
        return True
    except Exception:
        database_session.rollback()
        logger.exception("Failed to delete expired archived listing id=%s", listing_id)
        return False
    finally:
        database_session.close()


def cleanup_expired_archive() -> None:
    """Runs once every 30 days (see app.services.scheduler) and wipes the
    ENTIRE archive in one go — every sold/removed listing, regardless of how
    long ago it individually got there. There is deliberately no per-listing
    date filter: the 30-day period is the shared run interval itself, not a
    per-listing age check."""
    database_session: Session = SessionLocal()
    try:
        archived_listing_ids = [
            listing_id
            for (listing_id,) in database_session.query(Listing.id)
            .filter(Listing.status.in_(ARCHIVED_STATUSES))
            .all()
        ]
    finally:
        database_session.close()

    deleted_ids: list[int] = [
        listing_id for listing_id in archived_listing_ids if _delete_expired_listing(listing_id)
    ]

    logger.info("Archive cleanup: deleted %d listing(s): %s", len(deleted_ids), deleted_ids)
