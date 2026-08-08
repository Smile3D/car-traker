# Archive Cleanup: Whole-Archive-At-Once Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the previous per-listing "30 days after this listing's own `archived_at`" cleanup logic with a single shared schedule: the entire Archive (every `sold`/`removed` listing) is wiped in one go, once every 30 days, on one shared clock that survives backend restarts. Remove the now-meaningless per-listing `scheduled_deletion_date` column/field and replace it with a single "next cleanup" date shown once in the banner.

**Architecture:** APScheduler moves from an in-memory job store (which reset the clock on every restart — the bug being fixed) to `SQLAlchemyJobStore` backed by the same Postgres database, so the job's `next_run_time` persists across deploys. The scheduler instance moves out of `main.py` into its own module (`app/services/scheduler.py`) so a new read-only endpoint can inspect the job's `next_run_time` without a circular import. `cleanup_expired_archive` drops its date filter entirely — it deletes every `sold`/`removed` listing on every run, since the run itself is now the only gate. `archived_at` stays on the model (still useful for audit) but no longer drives deletion or exposes a computed field.

**Tech Stack:** FastAPI + SQLAlchemy + APScheduler (`SQLAlchemyJobStore`, `IntervalTrigger`), Nuxt 3 / Vue 3 (Pinia store for the new single-value schedule, mirroring the existing `currencyStore` pattern).

## Global Constraints

- Deletion criterion is now **status only**: every `Listing` with `status IN ('sold', 'removed')` is deleted on every cleanup run, full stop. `archived_at` is not read by the cleanup query anymore.
- The 30-day clock is for the **whole archive**, one shared `next_run_time`, not per-listing. `IntervalTrigger(days=30)` with no explicit `start_date` — its first fire is computed from whenever the job is first added (i.e. first deploy of this change), which is exactly "точка відліку = момент першого деплою" per spec.
- Job persistence: `SQLAlchemyJobStore` on the same Postgres engine (`app.database.engine`) — reuse the existing engine, don't open a second connection pool. APScheduler creates its own table (`apscheduler_jobs` by default) automatically on `scheduler.start()`; no Alembic migration needed for it, it's APScheduler-managed, not one of our ORM models.
- Photo-file deletion, `Client` cascade, and `DealHistory` independence (via `ON DELETE SET NULL`) are unchanged — do not touch that part of `archive_cleanup.py`.
- Remove entirely (not deprecate): `Listing.scheduled_deletion_date` computed field on the backend, the frontend `scheduled_deletion_date` type field, the Archive table's "Буде видалено" column, and the `crm.archive.columns.scheduledDeletion` locale key (uk + ru).
- Banner text — copy verbatim (uk/ru given below), interpolated with `{date}` using the same named-interpolation syntax already used elsewhere in this codebase (e.g. `t('listingDetails.photoUploadPartialFailure', { count: failedPhotoUploadCount })`).
- Date formatting for `{date}`: reuse the existing `d(date, 'short')` i18n formatter already used throughout (do not hand-roll date formatting).
- After every locale-file edit: re-validate JSON *and* restart the frontend dev container before declaring a translation key broken — this exact session already burned time on a false "translation bug" that was actually a stale dev-server process (see the prior investigation). Don't repeat that: restart proactively as part of Task 6's verification, not reactively after seeing raw keys on the page.
- Follow existing code style: full descriptive names, no abbreviations, comments only where they explain *why*.

---

### Task 1: Backend — `cleanup_expired_archive` deletes the whole archive, no date filter

**Files:**
- Modify: `backend/app/services/archive_cleanup.py`

**Interfaces:**
- Produces: `cleanup_expired_archive() -> None` (same signature, new behavior — no longer reads `archived_at`).

- [ ] **Step 1: Remove the cutoff/date-filter logic**

Replace the whole file's query section — change:

```python
ARCHIVE_RETENTION = timedelta(days=30)
ARCHIVED_STATUSES = ("sold", "removed")
```

to (drop the now-unused retention constant, `ARCHIVED_STATUSES` stays):

```python
ARCHIVED_STATUSES = ("sold", "removed")
```

And change `cleanup_expired_archive`'s body from:

```python
def cleanup_expired_archive() -> None:
    cutoff = datetime.now(timezone.utc) - ARCHIVE_RETENTION

    database_session: Session = SessionLocal()
    try:
        expired_listing_ids = [
            listing_id
            for (listing_id,) in database_session.query(Listing.id)
            .filter(
                Listing.status.in_(ARCHIVED_STATUSES),
                Listing.archived_at.isnot(None),
                Listing.archived_at <= cutoff,
            )
            .all()
        ]
    finally:
        database_session.close()

    deleted_ids: list[int] = [
        listing_id for listing_id in expired_listing_ids if _delete_expired_listing(listing_id)
    ]

    logger.info("Archive cleanup: deleted %d listing(s): %s", len(deleted_ids), deleted_ids)
```

to:

```python
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
```

- [ ] **Step 2: Clean up the now-unused import**

`timedelta` is no longer used in this file (only `datetime`, `timezone` remain relevant, and even those may now be unused — check). At the top of the file, change:

```python
from datetime import datetime, timedelta, timezone
```

Check whether `datetime`/`timezone` are still referenced anywhere else in the file (they aren't, since the cutoff computation was the only user) — if not, remove the whole import line. Confirm with:

Run: `cd backend && grep -n "datetime\|timezone" app/services/archive_cleanup.py`
Expected: no matches outside of the import line itself — if so, delete that import line entirely.

- [ ] **Step 3: Verify it imports and runs**

Run: `cd backend && venv/bin/python -c "
import logging
logging.basicConfig(level=logging.INFO)
from app.services.archive_cleanup import cleanup_expired_archive
cleanup_expired_archive()
"`
Expected: a log line reporting deletion of every current `sold`/`removed` listing in the dev DB (there will be several from prior session testing) — no traceback. This is expected and correct now: the whole archive really does get wiped on every manual invocation, which is exactly the new behavior.

---

### Task 2: Backend — move the scheduler into its own module with a persistent job store

**Files:**
- Create: `backend/app/services/scheduler.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `scheduler: AsyncIOScheduler` (module-level singleton), `CLEANUP_JOB_ID: str = "cleanup_expired_archive"`. Task 4's new endpoint imports `scheduler` and `CLEANUP_JOB_ID` from this module — this is exactly why the scheduler moved out of `main.py`, to avoid a circular import (`main.py` already imports the archive router, which would need to import `scheduler` back from `main.py`).

- [ ] **Step 1: Write the new scheduler module**

```python
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import engine

CLEANUP_JOB_ID = "cleanup_expired_archive"

# SQLAlchemyJobStore (not the default in-memory store) so the job's
# next_run_time survives a backend restart/redeploy — otherwise every
# restart would silently reset the 30-day clock back to zero. Reuses the
# app's existing engine/connection pool rather than opening a second one.
scheduler = AsyncIOScheduler(jobstores={"default": SQLAlchemyJobStore(engine=engine)})
```

- [ ] **Step 2: Rewire `main.py` to use it**

Change the top of `backend/app/main.py` from:

```python
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
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
    service_records,
    telegram_integration,
)
from app.services.archive_cleanup import cleanup_expired_archive

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # max_instances=1 (the APScheduler default) means an overrunning previous
    # run causes the next trigger to be skipped rather than run concurrently
    # — sufficient here since this app runs a single uvicorn worker, no
    # distributed lock needed. coalesce=True collapses any missed runs (e.g.
    # the container was down at 03:00) into a single catch-up run instead of
    # firing once per missed day.
    scheduler.add_job(
        cleanup_expired_archive,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_expired_archive",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Car Garage Tracker", lifespan=lifespan)
```

to:

```python
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
```

- [ ] **Step 3: Register the new archive router (created in Task 4) and add its include line**

Further down in the same file, add next to the other `app.include_router(...)` calls (alphabetically first, matching the import block's ordering):

```python
app.include_router(archive.router)
app.include_router(auth.router)
```

(Task 4 creates `app/routers/archive.py` — this step just wires it in; if you're executing tasks in order, come back and confirm this line matches after Task 4 lands. `archive` will fail to import until Task 4's file exists — that's expected and fine mid-plan.)

- [ ] **Step 4: Verify (after Task 4 lands — see that task's own verification step)**

This task's own import check will fail until `app/routers/archive.py` exists (Task 4). Do not treat that as a Task 2 failure — proceed to Task 3 and Task 4, then return here only if something still doesn't import after Task 4's own verification passes.

---

### Task 3: Backend — remove `scheduled_deletion_date` from `ListingOut`

**Files:**
- Modify: `backend/app/schemas/listing.py`

- [ ] **Step 1: Remove the computed field**

Delete this block entirely from `ListingOut`:

```python
    @computed_field
    @property
    def scheduled_deletion_date(self) -> date | None:
        if self.archived_at is None:
            return None
        return (self.archived_at + timedelta(days=30)).date()
```

Keep `archived_at: datetime | None` as a plain field (still useful for audit, per Global Constraints) — do not remove that one.

- [ ] **Step 2: Clean up the now-unused import**

`timedelta` was only used by the removed computed field. Check:

Run: `cd backend && grep -n "timedelta" app/schemas/listing.py`
Expected: no matches — if so, change the top-of-file import from `from datetime import date, datetime, timedelta` back to `from datetime import date, datetime`.

- [ ] **Step 3: Verify**

Run: `cd backend && venv/bin/python -c "
from app.schemas.listing import ListingOut
print('scheduled_deletion_date' in ListingOut.model_fields or 'scheduled_deletion_date' in ListingOut.model_computed_fields)
"`
Expected: `False`

---

### Task 4: Backend — `GET /crm/archive/cleanup-schedule` endpoint

**Files:**
- Create: `backend/app/schemas/archive.py`
- Create: `backend/app/routers/archive.py`

**Interfaces:**
- Consumes: `scheduler`, `CLEANUP_JOB_ID` from `app.services.scheduler` (Task 2); `require_company_member` from `app.dependencies`.
- Produces: `GET /crm/archive/cleanup-schedule` → `{"next_cleanup_at": "<ISO datetime>" | null}`. Frontend Task 8 consumes this.

- [ ] **Step 1: Write the schema**

```python
from datetime import datetime

from pydantic import BaseModel


class ArchiveCleanupScheduleOut(BaseModel):
    next_cleanup_at: datetime | None
```

- [ ] **Step 2: Write the router**

```python
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
```

- [ ] **Step 3: Verify the whole app imports now that Task 2's router registration resolves**

Run: `cd backend && venv/bin/python -c "from app.main import app, scheduler; print('app ok, scheduler running:', scheduler.running)"`
Expected: `app ok, scheduler running: False` (module import alone doesn't run the lifespan — matches the same expected output style as the original scheduler wiring task).

---

### Task 5: Backend — end-to-end scheduler verification against the live container

**Files:** none (verification only)

- [ ] **Step 1: Restart the backend container so the lifespan actually runs and creates the job store table**

Run: `docker restart fs-nuxt-car-garage-tracker-backend-1` (adjust name if different — check with `docker ps --format "{{.Names}}"`)
Wait for it to come back up, then: `docker logs fs-nuxt-car-garage-tracker-backend-1 --tail 20`
Expected: clean `Application startup complete`, no traceback.

- [ ] **Step 2: Confirm the job store table was created and the job persisted**

Run: `docker exec fs-nuxt-car-garage-tracker-db-1 psql -U <user> -d <db> -c "SELECT id, next_run_time FROM apscheduler_jobs;"` (get `<user>`/`<db>` from `backend/.env`'s `DATABASE_URL`).
Expected: exactly one row, `id = cleanup_expired_archive`, `next_run_time` roughly "now + 30 days" (APScheduler stores it as a POSIX timestamp float — readable via `to_timestamp(next_run_time)` in the query if you want a human-readable check).

- [ ] **Step 3: Confirm the new endpoint reflects the same value**

Using an authenticated request (any company member token): `GET /crm/archive/cleanup-schedule` → `{"next_cleanup_at": "<same timestamp as Step 2, ISO format>"}`.

- [ ] **Step 4: Confirm the persistence fix itself — restart again, confirm `next_run_time` does NOT change**

Run: `docker restart fs-nuxt-car-garage-tracker-backend-1`, wait for it to come back up, re-run Step 3's request.
Expected: **identical** `next_cleanup_at` to Step 3 — this is the actual bug fix being verified: the previous in-memory job store would have reset this to "now + 30 days" on every restart; the new `SQLAlchemyJobStore` must not.

---

### Task 6: Frontend — remove the per-listing "Буде видалено" column

**Files:**
- Modify: `frontend/app/types/listings.ts`
- Modify: `frontend/app/components/listings/ListingsTable.vue`
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

- [ ] **Step 1: Remove the type field**

In `frontend/app/types/listings.ts`, remove this line:

```ts
    scheduled_deletion_date: string | null
```

(leave `date_sold: string | null` above it untouched).

- [ ] **Step 2: Remove the column from `ListingsTable.vue`**

Remove the header cell (currently the last `<th>` in the archive-variant `<template v-else>` header block):

```html
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.scheduledDeletion') }}</th>
```

And remove the matching body cell (currently the last `<td>` in the archive-variant `<template v-else>` row block):

```html
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.scheduled_deletion_date) }}</td>
```

Removing both the header and body cell together keeps column counts matched — no `colspan`/layout fix needed, since this was a plain trailing column in a standard HTML table (removing the last `<th>`/`<td>` pair from every row is layout-neutral).

- [ ] **Step 3: Remove the locale key from both files**

In `frontend/locales/uk.json`, inside `crm.archive.columns`, remove the `"scheduledDeletion": "Буде видалено"` line (remember to remove the trailing comma from the now-last `"manager"` line above it).

In `frontend/locales/ru.json`, same removal (`"scheduledDeletion": "Будет удалено"`, fix the trailing comma on `"manager"`).

- [ ] **Step 4: Verify JSON validity**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('ok')"`
Expected: `ok`

- [ ] **Step 5: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json`
Expected: no output (clean) — confirms no other code still references `scheduled_deletion_date`.

---

### Task 7: Frontend — `ArchiveCleanupSchedule` type + store

**Files:**
- Create: `frontend/app/types/archive.ts`
- Create: `frontend/app/stores/archiveCleanupSchedule.ts`

**Interfaces:**
- Produces: `useArchiveCleanupScheduleStore()` with `{ schedule, isLoading, error, fetchSchedule }` — mirrors the existing `useCurrencyStore` pattern (fetch-once via a `hasFetched` guard, single cached value, no per-navigation refetch). Task 8 consumes this.

- [ ] **Step 1: Write the type**

```ts
export interface ArchiveCleanupSchedule {
    next_cleanup_at: string | null
}
```

- [ ] **Step 2: Write the store**

```ts
import type { ArchiveCleanupSchedule } from '~/types/archive'
import type { ApiError } from '~/composables/useApi'

// One shared value for the whole archive (not per-listing) — fetched once
// per session and cached, mirroring useCurrencyStore's pattern for the same
// kind of "informational, rarely-changing, single global value" data.
export const useArchiveCleanupScheduleStore = defineStore('archiveCleanupSchedule', () => {
    const schedule = ref<ArchiveCleanupSchedule | null>(null)
    const isLoading = ref(false)
    const error = ref<string | null>(null)
    const hasFetched = ref(false)

    const { apiGet } = useApi()

    const fetchSchedule = async (): Promise<void> => {
        if (hasFetched.value) {
            return
        }

        isLoading.value = true
        error.value = null
        try {
            schedule.value = await apiGet<ArchiveCleanupSchedule>('/crm/archive/cleanup-schedule')
        } catch (e) {
            error.value = (e as ApiError).message
        } finally {
            hasFetched.value = true
            isLoading.value = false
        }
    }

    return {
        schedule,
        isLoading,
        error,
        fetchSchedule
    }
})
```

- [ ] **Step 3: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "archiveCleanupSchedule" || echo "no errors"`
Expected: `no errors`

---

### Task 8: Frontend — banner shows the shared `next_cleanup_at` date

**Files:**
- Modify: `frontend/app/pages/crm/archive.vue`
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

**Interfaces:**
- Consumes: `useArchiveCleanupScheduleStore` from Task 7.

- [ ] **Step 1: Fetch the schedule alongside the page's existing data fetches**

In `frontend/app/pages/crm/archive.vue`, add the store:

```ts
const listingStore = useListingStore()
const clientStore = useClientStore()
const archiveCleanupScheduleStore = useArchiveCleanupScheduleStore()
```

Change the existing:

```ts
await Promise.all([listingStore.fetchListings(), clientStore.fetchClients()])
```

to:

```ts
await Promise.all([listingStore.fetchListings(), clientStore.fetchClients(), archiveCleanupScheduleStore.fetchSchedule()])
```

- [ ] **Step 2: Format the date and build the banner text**

Add near the top of the script (the file already destructures `const { t } = useI18n()` — check its current destructure and add `d` if not already present):

```ts
const { t, d } = useI18n()
```

Add a computed for the formatted date, reusing the same `d(new Date(value), 'short')` pattern already used throughout this codebase (e.g. in `ListingsTable.vue`'s `formattedDate`):

```ts
const nextCleanupDateFormatted = computed<string>(() => {
  const nextCleanupAt = archiveCleanupScheduleStore.schedule?.next_cleanup_at
  return nextCleanupAt ? d(new Date(nextCleanupAt), 'short') : '—'
})
```

- [ ] **Step 3: Update the banner usage**

Change:

```html
    <WarningBanner>{{ t('crm.archive.autoCleanupWarning') }}</WarningBanner>
```

to:

```html
    <WarningBanner>{{ t('crm.archive.autoCleanupWarning', { date: nextCleanupDateFormatted }) }}</WarningBanner>
```

- [ ] **Step 4: Update the locale strings**

In `frontend/locales/uk.json`, change the `autoCleanupWarning` value from the old per-listing text to:

```json
      "autoCleanupWarning": "Архів автоматично повністю очищується кожні 30 днів. Наступне очищення: {date}. Дані по угоді назавжди зберігаються в розділі «Історія угод».",
```

In `frontend/locales/ru.json`:

```json
      "autoCleanupWarning": "Архив автоматически полностью очищается каждые 30 дней. Следующая очистка: {date}. Данные по сделке навсегда сохраняются в разделе «История сделок».",
```

`{date}` is vue-i18n's standard named-interpolation syntax — already used elsewhere in this codebase (e.g. `listingDetails.photoUploadPartialFailure`'s `{count}`), so no config change is needed for it to work.

- [ ] **Step 5: Verify JSON validity**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('ok')"`
Expected: `ok`

- [ ] **Step 6: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json`
Expected: no output (clean).

---

### Task 9: End-to-end verification (the pause requested by the user)

**Files:** none (verification only)

- [ ] **Step 1: Restart the frontend dev container**

This session already hit a real bug where a stale Nitro dev process kept serving old compiled i18n messages after a locale-file edit (documented in this repo's prior investigation). Restart proactively rather than debugging a phantom "translation not found" later:

Run: `docker restart fs-nuxt-car-garage-tracker-frontend-1`, wait for it to come back up (`docker logs fs-nuxt-car-garage-tracker-frontend-1 --tail 20` shows a clean startup).

- [ ] **Step 2: Confirm the banner renders with the interpolated date, in both locales, with zero `[intlify]` warnings**

Fetch the SSR HTML for `/crm/archive` (authenticated) and grep for:
- The uk banner text containing "Наступне очищення:" followed by a `DD.MM.YYYY` date (not the literal string `{date}`, not a raw `crm.archive.autoCleanupWarning` key).
- Switch to `ru` (via the `i18n_locale` cookie, same as the previous session's verification) and confirm "Следующая очистка:" with the same date.
- Grep the response for `[intlify]` — expect zero matches in both locales.

- [ ] **Step 3: Confirm the "Буде видалено" column is gone and nothing else in the table broke**

In the same SSR HTML, confirm the archive table's header no longer contains `scheduledDeletion`/"Буде видалено", and the remaining columns (car, status, closed date, final price, net profit, seller, buyer, manager) still render correctly with matched header/row cell counts.

- [ ] **Step 4: Confirm the actual cleanup behavior end-to-end**

Since waiting 30 real days isn't practical: directly invoke `cleanup_expired_archive()` once (same one-liner as Task 1 Step 3) against a dev DB seeded with a mix of sold/removed listings with varying `archived_at` ages (some old, some created seconds ago) — confirm **all** of them get deleted regardless of age, proving the per-listing date filter is truly gone. Then confirm `GET /crm/archive/cleanup-schedule` still returns the same `next_cleanup_at` as before (manually invoking the cleanup function directly, bypassing the scheduler, must not affect the job's own `next_run_time` — only an actual scheduler-triggered fire would advance it).

- [ ] **Step 5: Report results**

Confirm every check above passed. If anything fails, fix it and re-run only the failing check.
