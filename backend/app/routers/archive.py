from fastapi import APIRouter, Depends

from app.dependencies import require_company_member
from app.models.user import User
from app.schemas.archive import ArchiveCleanupScheduleOut
from app.services.scheduler import CLEANUP_JOB_ID, scheduler

router = APIRouter(prefix="/crm/archive", tags=["archive"])


@router.get("/cleanup-schedule", response_model=ArchiveCleanupScheduleOut)
def get_archive_cleanup_schedule(current_user: User = Depends(require_company_member)) -> ArchiveCleanupScheduleOut:
    # One shared schedule for the whole archive, not per-company/per-listing
    # — every company using this backend shares the same cleanup run. Gated
    # behind require_company_member purely to match "logged in" for every
    # other endpoint, not because the value itself is company-specific.
    job = scheduler.get_job(CLEANUP_JOB_ID)
    return ArchiveCleanupScheduleOut(next_cleanup_at=job.next_run_time if job is not None else None)
