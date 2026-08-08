from datetime import datetime

from pydantic import BaseModel


class ArchiveCleanupScheduleOut(BaseModel):
    next_cleanup_at: datetime | None
