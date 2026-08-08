# Archive Auto-Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `sold`/`removed` listing that has sat in the Archive for 30+ days gets physically deleted (row + photos + cascaded Client rows) by a daily background job — `DealHistory` is untouched and remains the permanent record. The Archive page (`/crm/archive`) gets a permanent warning banner explaining this, plus a "Буде видалено" column showing each row's scheduled deletion date.

**Architecture:** A new `Listing.archived_at` column is stamped the moment a listing enters `sold` (in `mark_listing_sold`) or `removed` (in `update_listing`'s existing removed-transition branch). A daily APScheduler job queries listings past the 30-day cutoff and deletes each one in its own transaction, first removing its photo files from disk, then the row itself (DB-level `ON DELETE CASCADE` — already present, verified in Task 1 — cascades to `Client`/`ListingPhoto` rows; `DealHistory.listing_id` is already `ON DELETE SET NULL`). `ListingOut` gains a computed `scheduled_deletion_date` field the frontend renders as-is.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), APScheduler (`AsyncIOScheduler`, in-process, single uvicorn worker — see Global Constraints), Nuxt 3 / Vue 3 (frontend).

## Global Constraints

- Retention window: **30 days** from `archived_at`, checked daily at **03:00 server-local time**.
- `DealHistory` is never touched by the cleanup job or the migration — it already survives listing deletion via `ON DELETE SET NULL` on `employee_id`. Do not modify `app/models/deal_history.py` or `app/routers/deal_history.py`.
- No new DELETE endpoint — cleanup is 100% background/cron-driven. The existing manual bulk-delete (`POST /listings/bulk-delete`) is unrelated and untouched.
- No extra request validation on the cron path — it's internal, not user-facing.
- Deployment is a single `backend` container running a single `uvicorn` process with no `--workers` flag (confirmed in `backend/entrypoint.sh`) — APScheduler's default `max_instances=1` on the job is sufficient to prevent overlapping runs; do not add a distributed/DB-level lock, it would be unused complexity.
- Banner text (verbatim, uk + ru) and column label are given below in Task 8/9 — copy them exactly, do not paraphrase.
- Frontend: static banner (no dismiss), static date column (no live countdown, no separate "days left" column) — per explicit instruction.
- Follow existing code style: full descriptive names, no abbreviations, comments only where they explain *why*.
- All shell commands non-interactive (`-y`/`--yes`/`-m` flags, no prompts).

---

### Task 1: Backend — verify cascade behavior (no code change expected)

**Files:** none (verification only) — `backend/app/models/client.py`, `backend/app/models/listing_photo.py`, `backend/app/models/deal_history.py` already read during planning.

**Why this task exists:** the spec asks to "verify/add ON DELETE CASCADE for Client.listing_id ... if missing." It is already present. This task is a documented checkpoint, not a blind skip.

- [ ] **Step 1: Confirm the three relevant foreign keys**

Run: `cd backend && grep -n "ForeignKey(\"listings" app/models/client.py app/models/listing_photo.py app/models/deal_history.py`
Expected output (already true as of this plan):
```
app/models/client.py:    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
app/models/listing_photo.py:    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
app/models/deal_history.py:    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
```
If any of these differ from the expected output, stop and report — do not proceed to Task 2 until this is confirmed, since Task 6's cleanup job relies on the DB doing the cascade.

---

### Task 2: Backend — `archived_at` column + migration with backfill

**Files:**
- Modify: `backend/app/models/listing.py`
- Create: `backend/alembic/versions/<generated>_add_archived_at_to_listings.py`

**Interfaces:**
- Produces: `Listing.archived_at: datetime | None` (timezone-aware). Task 3 writes to it; Task 6 reads it; Task 7 exposes it via schema.

- [ ] **Step 1: Add the column to the model**

In `backend/app/models/listing.py`, add after `date_sold`:

```python
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

(`DateTime` is already imported at the top of this file; `datetime` needs adding to the existing `from datetime import date, datetime` import — it's already imported, no change needed there.)

- [ ] **Step 2: Generate the migration skeleton**

Run: `cd backend && venv/bin/alembic revision -m "add archived_at to listings"`
Expected: prints the new file path under `alembic/versions/`, something like `Generating .../alembic/versions/<hex>_add_archived_at_to_listings.py`. Note the revision id it prints.

- [ ] **Step 3: Fill in the migration**

Open the generated file and replace `upgrade`/`downgrade` with:

```python
def upgrade() -> None:
    op.add_column('listings', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill so existing sold/removed listings don't all look "just
    # archived at epoch" (which would be fine) or, worse, sit at NULL and
    # get silently skipped by the cleanup job forever. Listings has no
    # updated_at column, so created_at is the documented fallback per spec.
    op.execute(
        """
        UPDATE listings
        SET archived_at = created_at
        WHERE status IN ('sold', 'removed') AND archived_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('listings', 'archived_at')
```

- [ ] **Step 4: Apply the migration against the running dev database**

Run: `cd backend && venv/bin/alembic upgrade head`
Expected: log line ending in the new revision id, no errors.

- [ ] **Step 5: Verify the backfill**

Run: `cd backend && venv/bin/python -c "
from app.database import SessionLocal
from app.models.listing import Listing
session = SessionLocal()
total = session.query(Listing).filter(Listing.status.in_(['sold', 'removed'])).count()
backfilled = session.query(Listing).filter(Listing.status.in_(['sold', 'removed']), Listing.archived_at.isnot(None)).count()
print(f'{backfilled}/{total} sold+removed listings have archived_at set')
session.close()
"`
Expected: `backfilled == total` (every existing sold/removed listing got a value, none left NULL).

---

### Task 3: Backend — stamp `archived_at` on the sold/removed transitions

**Files:**
- Modify: `backend/app/routers/listings.py`

**Interfaces:**
- Consumes: `Listing.archived_at` from Task 2.

- [ ] **Step 1: Update the datetime import**

Change the top-of-file import:

```python
from datetime import date
```

to:

```python
from datetime import date, datetime, timezone
```

- [ ] **Step 2: Stamp it in the removed-transition branch of `update_listing`**

In `update_listing`, change:

```python
    if previous_status != "removed" and listing.status == "removed":
        database_session.flush()
        _record_deal_history(listing, "removed", database_session)
```

to:

```python
    if previous_status != "removed" and listing.status == "removed":
        listing.archived_at = datetime.now(timezone.utc)
        database_session.flush()
        _record_deal_history(listing, "removed", database_session)
```

- [ ] **Step 3: Stamp it in `mark_listing_sold`**

Change:

```python
    listing.status = "sold"
    listing.date_sold = date.today()

    database_session.flush()
    _record_deal_history(listing, "sold", database_session)
```

to:

```python
    listing.status = "sold"
    listing.date_sold = date.today()
    listing.archived_at = datetime.now(timezone.utc)

    database_session.flush()
    _record_deal_history(listing, "sold", database_session)
```

- [ ] **Step 4: Verify manually**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

(Full behavioral verification — that marking sold/removed actually sets a fresh `archived_at` — happens in Task 11's end-to-end pass, since it needs a real listing and DB round-trip.)

---

### Task 4: Backend — add `apscheduler` dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the line**

Append to `backend/requirements.txt`:

```
apscheduler
```

- [ ] **Step 2: Install into the dev venv**

Run: `cd backend && venv/bin/pip install -r requirements.txt`
Expected: `Successfully installed apscheduler-...` (or `Requirement already satisfied` if already present).

- [ ] **Step 3: Verify it imports**

Run: `cd backend && venv/bin/python -c "from apscheduler.schedulers.asyncio import AsyncIOScheduler; from apscheduler.triggers.cron import CronTrigger; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Install into the running dev container too**

The dev stack runs via `docker-compose` with `./backend:/app` bind-mounted — that mount overlays source code, but the container's Python packages live in the image's site-packages (installed at build time), which the bind mount does not touch. A `requirements.txt` change alone will not be picked up by the already-running container, and it will crash on reload with `ModuleNotFoundError` once Task 6 adds the import. Install directly into the running container:

Run: `docker exec <backend-container-name> pip install apscheduler` (find the exact container name via `docker ps --format "{{.Names}}"`, it was `fs-nuxt-car-garage-tracker-backend-1` during planning).
Expected: `Successfully installed apscheduler-...`

---

### Task 5: Backend — `archive_cleanup` service (the daily job body)

**Files:**
- Create: `backend/app/services/archive_cleanup.py`

**Interfaces:**
- Consumes: `SessionLocal` from `app.database`, `Listing` from `app.models.listing`, `settings.upload_dir` from `app.config`.
- Produces: `cleanup_expired_archive() -> None` — a plain (non-async) callable. Task 6 schedules it.

- [ ] **Step 1: Write the module**

```python
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.listing import Listing

logger = logging.getLogger(__name__)

ARCHIVE_RETENTION = timedelta(days=30)
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

- [ ] **Step 2: Verify it imports and runs against the (currently empty-of-expired-rows) dev DB**

Run: `cd backend && venv/bin/python -c "
import logging
logging.basicConfig(level=logging.INFO)
from app.services.archive_cleanup import cleanup_expired_archive
cleanup_expired_archive()
"`
Expected: a log line `Archive cleanup: deleted 0 listing(s): []` (nothing is 30+ days old yet in dev data) and no traceback.

---

### Task 6: Backend — wire the scheduler into the FastAPI app lifespan

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `cleanup_expired_archive` from Task 5.

- [ ] **Step 1: Add imports and the lifespan context manager**

Change the top of `backend/app/main.py` from:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
```

to:

```python
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
```

- [ ] **Step 2: Add the scheduler instance and lifespan function, and wire it into the app**

After the `app.routers import (...)` block and before `app = FastAPI(...)`, add:

```python
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
```

Then change:

```python
app = FastAPI(title="Car Garage Tracker")
```

to:

```python
app = FastAPI(title="Car Garage Tracker", lifespan=lifespan)
```

- [ ] **Step 3: Verify the app starts cleanly with the scheduler**

Run: `cd backend && venv/bin/python -c "
from app.main import app, scheduler
print('app ok, scheduler running:', scheduler.running)
"`
Expected: `app ok, scheduler running: False` (module import alone doesn't trigger the lifespan — that's expected; the real check is Task 11's live-server log check, where `uvicorn` actually runs the lifespan).

---

### Task 7: Backend — expose `scheduled_deletion_date` on `ListingOut`

**Files:**
- Modify: `backend/app/schemas/listing.py`

**Interfaces:**
- Produces: `ListingOut.archived_at: datetime | None` (plain field) and `ListingOut.scheduled_deletion_date: date | None` (computed). Frontend Task 9 consumes `scheduled_deletion_date`.

- [ ] **Step 1: Add the import**

At the top of `backend/app/schemas/listing.py`, `timedelta` needs adding to the existing `from datetime import date, datetime` import:

```python
from datetime import date, datetime, timedelta
```

- [ ] **Step 2: Add the field and computed property**

In `ListingOut`, add `archived_at: datetime | None` next to `date_sold` (both are the "when did this happen" fields for an archived listing):

```python
    date_added: date
    deadline_date: date | None
    date_sold: date | None
    archived_at: datetime | None
```

Then add the computed field, alongside the other `@computed_field` properties (e.g. right after `days_on_lot`):

```python
    @computed_field
    @property
    def scheduled_deletion_date(self) -> date | None:
        if self.archived_at is None:
            return None
        return (self.archived_at + timedelta(days=30)).date()
```

- [ ] **Step 3: Verify the schema round-trips**

Run: `cd backend && venv/bin/python -c "
from datetime import datetime, timezone
from app.schemas.listing import ListingOut
import json

sample = ListingOut.model_validate({
    'id': 1, 'company_id': 1, 'seller': None,
    'brand': 'Toyota', 'model': 'Camry', 'year': '2020', 'mileage': '1000', 'vin': None,
    'body_type': 'sedan', 'transmission': 'automatic', 'engine': '2.0', 'fuel_type': 'petrol', 'color': 'black',
    'condition': 'used', 'condition_description': None, 'trim_level': None,
    'purchase_price': 1000, 'additional_expenses': 0, 'sale_price': 2000, 'discount_amount': None,
    'date_added': '2026-01-01', 'deadline_date': None, 'date_sold': '2026-01-10',
    'archived_at': datetime(2026, 1, 10, tzinfo=timezone.utc),
    'status': 'sold', 'created_at': datetime(2026, 1, 1, tzinfo=timezone.utc),
})
print(json.loads(sample.model_dump_json())['scheduled_deletion_date'])
"`
Expected: `2026-02-09` (30 days after 2026-01-10).

---

### Task 8: Frontend — `WarningBanner` reusable component

**Files:**
- Create: `frontend/app/components/ui/WarningBanner.vue`

**Interfaces:**
- Produces: `<WarningBanner>message via default slot</WarningBanner>` (Nuxt auto-imports from `components/ui/` with no path prefix — confirmed via `nuxt.config.ts`'s `{ path: '~/components', pathPrefix: false }`, same as the existing `<ConfirmDialog>`). No component in this codebase currently fills this role — the existing inline banners (`ForeignListingNotice`, `PhotoUploadWarning`, etc.) are ad-hoc `<div>`s with no shared component, and this is the first one the spec asks to be reusable.

- [ ] **Step 1: Write the component**

```vue
<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <div
    class="flex items-start gap-3 rounded-lg border border-accent/30 border-l-4 border-l-accent bg-accent/10 p-4 text-sm text-accent"
    role="alert"
  >
    <ExclamationTriangleIcon class="mt-0.5 size-5 shrink-0" />
    <p><slot /></p>
  </div>
</template>
```

(`accent` is an existing design token — `--color-accent: 217 119 6` in `app/assets/css/main.css`, an amber/orange, currently unused anywhere in the frontend — verified via `grep -rn "bg-accent\|text-accent\|border-accent" app/components app/pages`, zero hits. It's the natural warning color already in the palette.)

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "WarningBanner" || echo "no errors"`
Expected: `no errors`

---

### Task 9: Frontend — banner + scheduled-deletion column on `/crm/archive`

**Files:**
- Modify: `frontend/app/types/listings.ts`
- Modify: `frontend/app/pages/crm/archive.vue`
- Modify: `frontend/app/components/listings/ListingsTable.vue`
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

**Interfaces:**
- Consumes: `scheduled_deletion_date` from Task 7's `ListingOut`; `WarningBanner` from Task 8.

- [ ] **Step 1: Add the field to the frontend `Listing` type**

In `frontend/app/types/listings.ts`, add next to `date_sold`:

```ts
    date_sold: string | null
    scheduled_deletion_date: string | null
```

- [ ] **Step 2: Add the locale strings**

In `frontend/locales/uk.json`, inside the `crm.archive` object, add (next to `"title"`):

```json
    "autoCleanupWarning": "Лоти автоматично видаляються з архіву через 30 днів після потрапляння сюди. Дані по угоді назавжди зберігаються в розділі «Історія угод».",
```

and inside `crm.archive.columns`, add (next to `"manager"`):

```json
      "scheduledDeletion": "Буде видалено"
```

In `frontend/locales/ru.json`, inside `crm.archive`, add:

```json
    "autoCleanupWarning": "Лоты автоматически удаляются из архива через 30 дней после попадания сюда. Данные по сделке навсегда сохраняются в разделе «История сделок».",
```

and inside `crm.archive.columns`:

```json
      "scheduledDeletion": "Будет удалено"
```

- [ ] **Step 3: Verify locale JSON validity**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('ok')"`
Expected: `ok`

- [ ] **Step 4: Add the banner to `archive.vue`**

In `frontend/app/pages/crm/archive.vue`, add the banner right after the page's `<h1>`/tabs header block and before the empty-state/table content — specifically, right after the closing `</div>` of the header `<div class="flex flex-wrap items-center justify-between gap-3">` block:

```html
    </div>

    <WarningBanner>{{ t('crm.archive.autoCleanupWarning') }}</WarningBanner>

    <!-- ArchiveEmptyState -->
```

(This renders unconditionally on the page — no dismiss state, no `v-if`, per spec.)

- [ ] **Step 5: Add the column to `ListingsTable.vue`**

In the header row's `<template v-else>` block (the archive-variant-only columns), add after the "manager" header:

```html
          <template v-else>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.seller') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.buyer') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.manager') }}</th>
            <th class="px-4 py-3 font-medium">{{ t('crm.archive.columns.scheduledDeletion') }}</th>
          </template>
```

And in the matching body-row `<template v-else>` block, add after the manager `<td>`, reusing the existing `formattedDate` helper already defined in this file (do not duplicate its logic):

```html
          <template v-else>
            <td class="px-4 py-3 text-muted-foreground">{{ sellerNameFor?.(listing) || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">{{ buyerNameFor?.(listing) || '—' }}</td>
            <td class="px-4 py-3 text-muted-foreground">
              {{ getEmployeeDisplayName(listing.seller?.employee, listing.seller?.employee?.email) || '—' }}
            </td>
            <td class="px-4 py-3 text-muted-foreground">{{ formattedDate(listing.scheduled_deletion_date) }}</td>
          </template>
```

(`formattedDate` already returns `'—'` for a null/empty value — see its definition: `const formattedDate = (value: string | null): string => value ? d(new Date(value), 'short') : '—'`. This satisfies the "show a dash, not blank/error" requirement with zero new code.)

- [ ] **Step 6: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "archive.vue\|ListingsTable.vue\|types/listings.ts" || echo "no errors in touched files"`
Expected: `no errors in touched files`

---

### Task 10: Frontend — confirm no other `Listing`-typing consumer breaks

**Files:** none (verification only)

**Why this task exists:** `Listing` (frontend type) gained a required field (`scheduled_deletion_date: string | null`) — every place that constructs a `Listing` object by hand (not just consumes one from the API) needs to still type-check.

- [ ] **Step 1: Full frontend type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json`
Expected: no output (clean). If anything references a hand-built `Listing` object missing the new field, fix it there before proceeding — do not weaken the type (e.g. don't make the field optional) to paper over it.

---

### Task 11: End-to-end verification (the pause requested by the user)

**Files:** none (verification only)

- [ ] **Step 1: Confirm the migration applied and the app boots with the scheduler**

Run: `cd backend && venv/bin/alembic current` — expect the new revision id from Task 2 as `(head)`.
Check the running backend container's logs (`docker logs <backend-container> --tail 20`) after a reload — expect no traceback, clean `Application startup complete`.

- [ ] **Step 2: Confirm `archived_at` gets stamped on real transitions**

Using a test listing (owner-authenticated), call `POST /listings/{id}/mark-sold`, then `GET /listings/{id}` — confirm the response's `archived_at` is a fresh timestamp and `scheduled_deletion_date` is exactly 30 days later. Repeat for a listing transitioned to `removed` via `PATCH /listings/{id}` with `{"status": "removed"}`.

- [ ] **Step 3: Confirm the cleanup job actually deletes an expired listing**

Since waiting 30 real days isn't practical, directly backdate a test listing's `archived_at` in the dev DB (e.g. `UPDATE listings SET archived_at = now() - interval '31 days' WHERE id = <test id>`), then manually invoke `cleanup_expired_archive()` (same one-liner as Task 5 Step 2) and confirm:
- The listing row is gone (`GET /listings/{id}` → 404).
- Its seller `Client` row is gone (cascade).
- Its photo files/directory on disk are gone (if the test listing had photos).
- The corresponding `DealHistory` row (if the listing was `sold`) still exists and is unchanged (`GET /deal-history` still lists it).
- The log line shows the correct count and id.

- [ ] **Step 4: Confirm the scheduler is actually registered on the live server**

Run: `docker exec <backend-container> venv/bin/python -c "
# adjust path if the container's venv differs
"` — or simpler, check the backend container logs for no APScheduler errors at startup, and optionally trigger `scheduler.print_jobs()` is not exposed via HTTP by design (no new endpoint per Global Constraints) — this check is log/code-inspection only, not a new API surface.

- [ ] **Step 5: Frontend visual check on `/crm/archive`**

In the browser: confirm the amber/orange `WarningBanner` renders at the top of the Archive page with the exact uk text, has no close/dismiss button, and the new "Буде видалено" column shows a `DD.MM.YYYY` date for archived listings (or "—" for any that predate the backfill in an unexpected way — should not happen after Task 2's backfill, but verify).

- [ ] **Step 6: Report results**

Confirm every check above passed. If anything fails, fix it and re-run only the failing check.
