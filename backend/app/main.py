from contextlib import asynccontextmanager

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    archive,
    auth,
    car_data,
    cars,
    client_stages,
    clients,
    currency,
    deal_history,
    employee_invites,
    employees,
    fuel_refills,
    listing_photos,
    listings,
    positions,
    receipts,
    sales_plans,
    service_records,
    telegram_integration,
)
from app.services.archive_cleanup import cleanup_expired_archive
from app.services.scheduler import CLEANUP_JOB_ID, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()

    # Only add the job the first time it's ever missing from the (persistent)
    # job store — on every later restart it's already there, so re-adding
    # would reset next_run_time back to "30 days from right now" instead of
    # honoring the original schedule. max_instances=1 (APScheduler's default)
    # plus coalesce=True: an overrunning previous run causes the next trigger
    # to be skipped rather than run concurrently (single uvicorn worker, no
    # distributed lock needed), and any missed runs (e.g. the container was
    # down across a 30-day mark) collapse into a single catch-up run.
    if scheduler.get_job(CLEANUP_JOB_ID) is None:
        scheduler.add_job(
            cleanup_expired_archive,
            trigger=IntervalTrigger(days=30),
            id=CLEANUP_JOB_ID,
            max_instances=1,
            coalesce=True,
        )

    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Car Garage Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(archive.router)
app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(service_records.router)
app.include_router(fuel_refills.router)
app.include_router(receipts.router)
app.include_router(listings.router)
app.include_router(listing_photos.router)
app.include_router(clients.router)
app.include_router(employees.router)
app.include_router(employee_invites.router)
app.include_router(positions.router)
app.include_router(client_stages.router)
app.include_router(telegram_integration.router)
app.include_router(car_data.router)
app.include_router(currency.router)
app.include_router(deal_history.router)
app.include_router(sales_plans.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
