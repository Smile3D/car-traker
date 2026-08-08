# Dashboard Sold/Removed Stats: Switch Source to DealHistory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Dashboard's "Продано" count and "Загальний чистий прибуток (продано)" (and, by the same reasoning, "Знято з продажу" count) drifting to 0 over time — they currently query the live `Listing` table, which the archive-cleanup job (shipped earlier this session) empties of every `sold`/`removed` row every 30 days. Switch them to `DealHistory`, the indestructible snapshot log that survives that cleanup, reusing the exact same company/employee-scoped endpoint the Deal History page already uses so the two pages are guaranteed to agree.

**Architecture:** `DealHistory` currently has no cost data at all (only `final_price`), so `net_profit` can't be computed from it yet. Add `purchase_price`/`additional_expenses` as snapshot columns (nullable, no backfill — pre-cleanup rows and rows whose source `Listing` is already gone have no recoverable cost data), populate them in `_record_deal_history()` going forward, and expose a `net_profit` computed field on `DealHistoryOut` mirroring `ListingOut`'s existing `total_cost`/`net_profit` computed-field pattern exactly. The Dashboard then fetches `useDealHistoryStore` (already role-scoped server-side, same as the Deal History page) instead of deriving sold/removed stats from `useListingStore`.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), Nuxt 3 / Vue 3 + Pinia (frontend).

## Global Constraints

- **No backfill** for the new `purchase_price`/`additional_expenses` columns — confirmed decision. Existing `DealHistory` rows keep both as `NULL`; `net_profit` for those rows resolves to `None`/`null`, not a fabricated value.
- `final_price` (and therefore `net_profit`) is only ever populated for `deal_type == "sold"` — this already exists for `final_price` in `_record_deal_history()`; do not change that convention. A `"removed"` row's `net_profit` computed field must resolve to `None` via the existing "`final_price is None` → no profit" logic, not a special case.
- Employee/owner scoping for the numbers this task touches is achieved **entirely by reusing** the existing `GET /deal-history` endpoint and its existing `require_company_member` + `if current_user.role == "employee": filter by employee_id` logic in `backend/app/routers/deal_history.py` — do not add new scoping logic anywhere, and do not modify that router. Reusing it is what guarantees Dashboard numbers match the Deal History page for the same user.
- Do **not** touch `crm/analytics.vue`'s `totalNetProfit`/`totalMargin` computations — they have the identical latent bug (also computed from `listingStore.listings`), but fixing them was not requested; flag it again at the end, don't fix it silently.
- Do **not** change `draft`/`active`/`reserved` counts on the Dashboard — they read live `Listing` data correctly today (those statuses are never touched by archive cleanup) and must stay exactly as they are.
- `ListingStatusCountsGrid.vue` is shared between `crm/index.vue` (Dashboard) and `crm/analytics.vue` (Analytics) — any change to it must be additive/optional so Analytics' current behavior is completely unaffected (it must not pass the new props, and the component must fall back to today's `listings`-derived sold/removed counts when they're absent).
- Follow existing code style: full descriptive names, no abbreviations, comments only where they explain *why*.

---

### Task 1: Backend — `purchase_price`/`additional_expenses` snapshot columns on `DealHistory`

**Files:**
- Modify: `backend/app/models/deal_history.py`
- Create: `backend/alembic/versions/<generated>_add_cost_snapshot_to_deal_history.py`

**Interfaces:**
- Produces: `DealHistory.purchase_price: Decimal | None`, `DealHistory.additional_expenses: Decimal | None`. Task 2 populates them; Task 3 exposes them + the derived `net_profit`.

- [ ] **Step 1: Add the columns to the model**

In `backend/app/models/deal_history.py`, add after `final_price`:

```python
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    additional_expenses: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
```

- [ ] **Step 2: Generate the migration skeleton**

Run: `cd backend && venv/bin/alembic revision -m "add cost snapshot to deal_history"`
Expected: prints the new file path; note the revision id.

- [ ] **Step 3: Fill in the migration (no backfill — see Global Constraints)**

```python
def upgrade() -> None:
    op.add_column('deal_history', sa.Column('purchase_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('deal_history', sa.Column('additional_expenses', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('deal_history', 'additional_expenses')
    op.drop_column('deal_history', 'purchase_price')
```

- [ ] **Step 4: Apply it**

Run: `cd backend && venv/bin/alembic upgrade head`
Expected: log line ending in the new revision id, no errors.

- [ ] **Step 5: Verify**

Run: `cd backend && venv/bin/python -c "
from app.database import SessionLocal
from app.models.deal_history import DealHistory
session = SessionLocal()
row = session.query(DealHistory).first()
if row is not None:
    print('purchase_price:', row.purchase_price, 'additional_expenses:', row.additional_expenses)
else:
    print('no existing deal_history rows to inspect (fine)')
session.close()
"`
Expected: either prints `purchase_price: None additional_expenses: None` (confirming existing rows are untouched/NULL, no backfill happened) or the "no existing rows" message — both are correct outcomes.

---

### Task 2: Backend — populate the snapshot in `_record_deal_history`

**Files:**
- Modify: `backend/app/routers/listings.py`

- [ ] **Step 1: Add the two fields to the `DealHistory(...)` construction**

In `_record_deal_history`, change:

```python
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
        final_price=(listing.sale_price - (listing.discount_amount or 0)) if deal_type == "sold" else None,
        employee_name=_employee_display_name(employee) if employee is not None else None,
        employee_id=employee.id if employee is not None else None,
        date_closed=listing.date_sold if listing.date_sold is not None else date.today(),
    )
```

to:

```python
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
        final_price=(listing.sale_price - (listing.discount_amount or 0)) if deal_type == "sold" else None,
        purchase_price=listing.purchase_price,
        additional_expenses=listing.additional_expenses,
        employee_name=_employee_display_name(employee) if employee is not None else None,
        employee_id=employee.id if employee is not None else None,
        date_closed=listing.date_sold if listing.date_sold is not None else date.today(),
    )
```

Captured for both `deal_type`s (unlike `final_price`, which stays sold-only) — the cost basis of the car is real regardless of what happened to the deal, and `net_profit`'s own None-on-missing-`final_price` logic (Task 3) already makes a `"removed"` row's profit resolve to `None` without needing a second special case here.

- [ ] **Step 2: Verify**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 3: Backend — expose the cost fields + `net_profit` on `DealHistoryOut`

**Files:**
- Modify: `backend/app/schemas/deal_history.py`

**Interfaces:**
- Produces: `DealHistoryOut.purchase_price: float | None`, `.additional_expenses: float | None`, `.net_profit: float | None` (computed). Frontend Task 5 consumes `net_profit`.

- [ ] **Step 1: Add the plain fields and the import**

Change the top of the file from:

```python
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
```

to:

```python
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field
```

Add `purchase_price`/`additional_expenses` next to `final_price`:

```python
    final_price: float | None
    purchase_price: float | None
    additional_expenses: float | None
```

- [ ] **Step 2: Add the computed field**

Add at the end of the class:

```python
    @computed_field
    @property
    def net_profit(self) -> float | None:
        if self.final_price is None or self.purchase_price is None or self.additional_expenses is None:
            return None
        return self.final_price - self.purchase_price - self.additional_expenses
```

(Mirrors `ListingOut.net_profit`'s formula exactly — `final_price - purchase_price - additional_expenses` — just guarded for the three ways the snapshot can be incomplete: a `"removed"` deal with no `final_price`, or a pre-migration row with no cost snapshot at all.)

- [ ] **Step 3: Verify — sold deal resolves a real number, removed deal resolves null**

Run: `cd backend && venv/bin/python -c "
from app.schemas.deal_history import DealHistoryOut
import json

sold = DealHistoryOut.model_validate({
    'id': 1, 'listing_id': 1, 'deal_type': 'sold',
    'brand': 'Toyota', 'model': 'Camry', 'year': '2020', 'vin': None,
    'seller_name': 'S', 'seller_phone': '+380501234567', 'buyer_name': None, 'buyer_phone': None,
    'final_price': 15000, 'purchase_price': 10000, 'additional_expenses': 500,
    'employee_name': None, 'employee_id': None,
    'date_closed': '2026-01-10', 'created_at': '2026-01-10T00:00:00Z',
})
print('sold net_profit:', json.loads(sold.model_dump_json())['net_profit'])

removed = DealHistoryOut.model_validate({
    'id': 2, 'listing_id': 2, 'deal_type': 'removed',
    'brand': 'Toyota', 'model': 'Camry', 'year': '2020', 'vin': None,
    'seller_name': 'S', 'seller_phone': '+380501234567', 'buyer_name': None, 'buyer_phone': None,
    'final_price': None, 'purchase_price': 10000, 'additional_expenses': 500,
    'employee_name': None, 'employee_id': None,
    'date_closed': '2026-01-10', 'created_at': '2026-01-10T00:00:00Z',
})
print('removed net_profit:', json.loads(removed.model_dump_json())['net_profit'])

legacy = DealHistoryOut.model_validate({
    'id': 3, 'listing_id': None, 'deal_type': 'sold',
    'brand': 'Toyota', 'model': 'Camry', 'year': '2020', 'vin': None,
    'seller_name': 'S', 'seller_phone': '+380501234567', 'buyer_name': None, 'buyer_phone': None,
    'final_price': 15000, 'purchase_price': None, 'additional_expenses': None,
    'employee_name': None, 'employee_id': None,
    'date_closed': '2026-01-10', 'created_at': '2026-01-10T00:00:00Z',
})
print('legacy (no cost snapshot) net_profit:', json.loads(legacy.model_dump_json())['net_profit'])
"`
Expected:
```
sold net_profit: 4500.0
removed net_profit: None
legacy (no cost snapshot) net_profit: None
```

---

### Task 4: Backend — end-to-end verification against the live containers

**Files:** none (verification only)

- [ ] **Step 1: Restart the backend container**

Run: `docker restart fs-nuxt-car-garage-tracker-backend-1`, wait for it to come back (`docker logs ... --tail 20` shows clean startup, no traceback).

- [ ] **Step 2: Create and sell a listing, confirm `net_profit` comes back correctly through the real API**

Using an authenticated owner token: create a listing (`purchase_price`, `sale_price` of your choosing), `POST /listings/{id}/mark-sold`, then `GET /deal-history` and confirm the new entry's `net_profit` equals `final_price - purchase_price - additional_expenses` for that listing.

- [ ] **Step 3: Confirm a "removed" transition still has `net_profit: null`**

Create a second listing, `PATCH /listings/{id}` with `{"status": "removed"}`, then `GET /deal-history` and confirm that entry has `"final_price": null` and `"net_profit": null`.

- [ ] **Step 4: Confirm employee scoping is unchanged**

`GET /deal-history` as an employee still only returns rows where `employee_id` matches them (this is pre-existing router behavior, not touched by this plan — this step is a regression check, not new functionality).

---

### Task 5: Frontend — `DealHistoryEntry` type gains the new fields

**Files:**
- Modify: `frontend/app/types/dealHistory.ts`

- [ ] **Step 1: Add the fields**

Change:

```ts
    final_price: number | null

    employee_name: string | null
```

to:

```ts
    final_price: number | null
    purchase_price: number | null
    additional_expenses: number | null
    net_profit: number | null

    employee_name: string | null
```

- [ ] **Step 2: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "dealHistory" || echo "no errors"`
Expected: `no errors`

---

### Task 6: Frontend — `ListingStatusCountsGrid` gains optional count overrides

**Files:**
- Modify: `frontend/app/components/listings/ListingStatusCountsGrid.vue`

**Interfaces:**
- Produces: two new optional props, `soldCountOverride?: number` and `removedCountOverride?: number`. When absent (Analytics' usage, unchanged), behavior is identical to today. Task 7 passes them from the Dashboard.

- [ ] **Step 1: Add the props and apply them in the computed**

Change:

```ts
const props = defineProps<{ listings: Listing[] }>()

const { t } = useI18n()

const statusKeys: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed']

const countsByStatus = computed<Record<ListingStatus, number>>(() => {
  const counts: Record<ListingStatus, number> = { draft: 0, active: 0, reserved: 0, sold: 0, removed: 0 }
  for (const listing of props.listings) {
    counts[listing.status] += 1
  }
  return counts
})
```

to:

```ts
const props = defineProps<{
  listings: Listing[]
  soldCountOverride?: number
  removedCountOverride?: number
}>()

const { t } = useI18n()

const statusKeys: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed']

// sold/removed have an override path: the live Listing table gets wiped by
// the archive-cleanup job every 30 days, so a caller with access to the
// indestructible DealHistory log (currently only the Dashboard) passes the
// real historical count in instead of letting it fall back to counting
// (increasingly absent) live Listing rows. draft/active/reserved are never
// touched by that cleanup, so they always come from `listings` — no
// override exists for them because none is needed.
const countsByStatus = computed<Record<ListingStatus, number>>(() => {
  const counts: Record<ListingStatus, number> = { draft: 0, active: 0, reserved: 0, sold: 0, removed: 0 }
  for (const listing of props.listings) {
    counts[listing.status] += 1
  }
  if (props.soldCountOverride !== undefined) {
    counts.sold = props.soldCountOverride
  }
  if (props.removedCountOverride !== undefined) {
    counts.removed = props.removedCountOverride
  }
  return counts
})
```

- [ ] **Step 2: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "ListingStatusCountsGrid" || echo "no errors"`
Expected: `no errors`

---

### Task 7: Frontend — Dashboard sources sold/removed stats from DealHistory

**Files:**
- Modify: `frontend/app/pages/crm/index.vue`

**Interfaces:**
- Consumes: `useDealHistoryStore` (existing store, already role-scoped server-side); `soldCountOverride`/`removedCountOverride` props from Task 6.

- [ ] **Step 1: Fetch deal history alongside listings**

Change:

```ts
const listingStore = useListingStore()

await listingStore.fetchListings()

const totalNetProfitSold = computed<number>(() =>
  listingStore.listings
    .filter((listing) => listing.status === 'sold')
    .reduce((sum, listing) => sum + listing.net_profit, 0)
)
```

to:

```ts
const listingStore = useListingStore()
const dealHistoryStore = useDealHistoryStore()

await Promise.all([listingStore.fetchListings(), dealHistoryStore.fetchDealHistory()])

// Sourced from DealHistory, not Listing — the archive-cleanup job (every 30
// days) deletes every sold/removed Listing row, so counting live Listings
// here would drift toward zero over time. DealHistory is the indestructible
// snapshot log designed to survive exactly that. Reusing the same store the
// Deal History page uses also means it's already scoped identically
// (owner sees the whole company, employee sees only their own deals) —
// these numbers are guaranteed to match that page for the same user.
const soldDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'sold'))
const removedDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'removed'))

const totalNetProfitSold = computed<number>(() =>
  soldDeals.value.reduce((sum, entry) => sum + (entry.net_profit ?? 0), 0)
)
```

- [ ] **Step 2: Pass the overrides into `ListingStatusCountsGrid`**

Change:

```html
    <ListingStatusCountsGrid :listings="listingStore.listings" />
```

to:

```html
    <ListingStatusCountsGrid
      :listings="listingStore.listings"
      :sold-count-override="soldDeals.length"
      :removed-count-override="removedDeals.length"
    />
```

- [ ] **Step 3: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json`
Expected: no output (clean).

---

### Task 8: End-to-end verification (the pause requested by the user)

**Files:** none (verification only)

- [ ] **Step 1: Restart the frontend container**

Run: `docker restart fs-nuxt-car-garage-tracker-frontend-1`, wait for clean startup in logs.

- [ ] **Step 2: Seed a realistic scenario**

As an owner: create and sell 2 listings with known `purchase_price`/`sale_price`/`additional_expenses` (compute expected `net_profit` by hand for each), create and remove 1 listing. Note the owner's `company_id`.

As an employee in the same company: create and sell 1 listing (self-assigned).

- [ ] **Step 3: Compare Dashboard numbers against Deal History, for both roles**

As the **owner**: open `/crm` and `/crm/deal-history` (or query both endpoints directly). Confirm:
- Dashboard "Продано" count == Deal History's count of `deal_type: "sold"` rows == 3 (2 owner + 1 employee, since owner sees the whole company).
- Dashboard "Загальний чистий прибуток (продано)" == sum of `net_profit` across those 3 sold entries == your hand-computed total.
- Dashboard "Знято з продажу" count == 1.

As the **employee**: confirm Dashboard "Продано" count == 1 (only their own deal, matching what `/crm/deal-history` shows them under `personalScopeSubtitle`), and confirm the "Загальний чистий прибуток" card is still fully absent for this role (unrelated `isOwner` gate from earlier work, must still hold).

- [ ] **Step 4: Confirm draft/active/reserved are untouched**

Create one `draft` and one `active` listing; confirm both counts on the Dashboard grid increment normally and are unaffected by anything in this plan.

- [ ] **Step 5: Report the final numbers to the user**

Per the user's request, write the resulting Dashboard numbers (owner view) in chat for them to confirm against their own expectations.
