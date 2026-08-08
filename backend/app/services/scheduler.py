from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import engine

CLEANUP_JOB_ID = "cleanup_expired_archive"

# SQLAlchemyJobStore (not the default in-memory store) so the job's
# next_run_time survives a backend restart/redeploy — otherwise every
# restart would silently reset the 30-day clock back to zero. Reuses the
# app's existing engine/connection pool rather than opening a second one.
scheduler = AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(engine=engine)})
