# Analytics Page: Switch Sold/Profit Stats to DealHistory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the exact fix already shipped for the Dashboard to every sold/profit-related stat on `/crm/analytics` — they all currently read live `Listing` rows and will decay toward zero/empty as the archive-cleanup job deletes sold/removed listings. Switch each to `DealHistory`. Add a `date_added` snapshot (+ partial backfill) so `AverageDaysToSellChart` can make the same move — the one chart that was previously blocked on missing data.

**Architecture:** `DealHistory` gains one more snapshot column, `date_added`, following the exact precedent set by the `purchase_price`/`additional_expenses` addition: nullable, populated going forward in `_record_deal_history()`, partially backfilled from any still-live `Listing`. `DealHistoryOut` gains a `days_on_lot` computed field mirroring `ListingOut.days_on_lot`. On the frontend, `analytics.vue` fetches `useDealHistoryStore` (already role-scoped server-side — no manual employee filtering needed for anything sourced from it, unlike the `scopedListings` filter still required for Listing-sourced data) and recomputes every sold/profit metric from `dealHistoryStore.entries`. Three chart components (`MonthlyProfitChart`, `TopProfitListingsChart`, `AverageDaysToSellChart`) change their prop contract from `Listing[]` to `DealHistoryEntry[]` — confirmed via grep that `analytics.vue` is their only consumer, so this is safe. `ListingStatusChart` and `ListingStatusCountsGrid` keep their `Listing[]` prop (still needed for draft/active/reserved) and gain the same optional `soldCountOverride`/`removedCountOverride` props already added to `ListingStatusCountsGrid` for the Dashboard.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), Nuxt 3 / Vue 3 + Pinia + Chart.js/vue-chartjs (frontend).

## Global Constraints

- `activeCount` and `overdueListings` on `analytics.vue` are **not touched** — they already correctly exclude `sold` and concern draft/active/reserved listings only, which are never deleted by archive cleanup.
- `date_added` backfill follows the same rule as the cost-snapshot backfill: **no fabrication**. A row backfills only if its `listing_id` still resolves to a live `Listing` (via JOIN); otherwise it stays `NULL` forever.
- Every DealHistory-sourced metric on this page must match the same metric on the Dashboard for the same user (same underlying store/endpoint, same scoping) — this is the explicit acceptance check at the end.
- `days_on_lot` on `DealHistoryOut` is computed as `date_closed - date_added` (no "today" fallback needed, unlike `ListingOut.days_on_lot`, since a `DealHistory` row is by definition already closed).
- The three charts whose prop contract changes (`MonthlyProfitChart`, `TopProfitListingsChart`, `AverageDaysToSellChart`) are confirmed single-consumer (`analytics.vue` only, verified via grep) — changing their prop type is not a breaking change anywhere else in the app.
- Follow existing code style: full descriptive names, no abbreviations, comments only where they explain *why*.

---

### Task 1: Backend — `date_added` snapshot column + schema migration

**Files:**
- Modify: `backend/app/models/deal_history.py`
- Create: `backend/alembic/versions/<generated>_add_date_added_to_deal_history.py`

**Interfaces:**
- Produces: `DealHistory.date_added: date | None`. Task 2 populates it going forward; Task 3 also backfills it for existing rows; Task 4 exposes it + the derived `days_on_lot`.

- [ ] **Step 1: Add the column to the model**

In `backend/app/models/deal_history.py`, add after `date_closed`:

```python
    date_closed: Mapped[date] = mapped_column(Date)
    date_added: Mapped[date | None] = mapped_column(Date, nullable=True)
```

- [ ] **Step 2: Generate and fill in the migration (schema only, no backfill here — Task 3 handles backfill separately)**

Run: `cd backend && venv/bin/alembic revision -m "add date_added to deal_history"`

```python
def upgrade() -> None:
    op.add_column('deal_history', sa.Column('date_added', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('deal_history', 'date_added')
```

- [ ] **Step 3: Apply and verify**

Run: `cd backend && venv/bin/alembic upgrade head`
Run: `cd backend && venv/bin/python -c "
from app.database import SessionLocal
from app.models.deal_history import DealHistory
session = SessionLocal()
row = session.query(DealHistory).first()
print('date_added:', row.date_added if row else 'no rows')
session.close()
"`
Expected: `date_added: None` (or "no rows") — new column exists, nothing populated yet.

---

### Task 2: Backend — populate `date_added` going forward

**Files:**
- Modify: `backend/app/routers/listings.py`

- [ ] **Step 1: Add it to the `DealHistory(...)` construction in `_record_deal_history`**

Change:

```python
        purchase_price=listing.purchase_price,
        additional_expenses=listing.additional_expenses,
```

to:

```python
        purchase_price=listing.purchase_price,
        additional_expenses=listing.additional_expenses,
        date_added=listing.date_added,
```

(Captured for both `deal_type`s, same reasoning as the cost fields — it's basic Listing metadata, not sale-outcome-specific.)

- [ ] **Step 2: Verify**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 3: Backend — partial backfill of `date_added` for existing rows

**Files:**
- Create: `backend/alembic/versions/<generated>_backfill_deal_history_date_added.py`

**Interfaces:**
- Same JOIN-based recovery pattern as the cost-snapshot backfill migration (`174440c586bb`): only backfills rows whose `Listing` still exists.

- [ ] **Step 1: Generate and fill in the migration**

Run: `cd backend && venv/bin/alembic revision -m "backfill deal history date_added from live listings"`

```python
def upgrade() -> None:
    """Same recovery rule as the purchase_price/additional_expenses backfill
    (see 174440c586bb): only rows whose Listing still exists get a value:
    the JOIN itself excludes anything with listing_id NULL or pointing at an
    already-deleted row. Anything left NULL after this is genuinely gone."""
    op.execute(
        """
        UPDATE deal_history
        SET date_added = listings.date_added
        FROM listings
        WHERE deal_history.listing_id = listings.id
          AND deal_history.listing_id IS NOT NULL
          AND deal_history.date_added IS NULL
        """
    )


def downgrade() -> None:
    """No meaningful downgrade for a data recovery backfill."""
    pass
```

- [ ] **Step 2: Snapshot before/after counts and apply**

Before applying, run: `cd backend && venv/bin/python -c "
from app.database import SessionLocal
from app.models.deal_history import DealHistory
from app.models.listing import Listing
session = SessionLocal()
null_count = session.query(DealHistory).filter(DealHistory.date_added.is_(None)).count()
backfillable = session.query(DealHistory).join(Listing, DealHistory.listing_id == Listing.id).filter(DealHistory.date_added.is_(None)).count()
print('before: null=', null_count, 'backfillable=', backfillable)
session.close()
"`

Run: `cd backend && venv/bin/alembic upgrade head`

Run the same query again (`after: null=... backfillable=...`) — expected: `backfillable` drops to `0`, and `null_count` decreases by exactly however many were backfillable before.

---

### Task 4: Backend — expose `date_added` + `days_on_lot` on `DealHistoryOut`

**Files:**
- Modify: `backend/app/schemas/deal_history.py`

- [ ] **Step 1: Add the plain field**

Change:

```python
    date_closed: date
    created_at: datetime
```

to:

```python
    date_closed: date
    date_added: date | None
    created_at: datetime
```

- [ ] **Step 2: Add the computed field**

Add after the existing `net_profit` computed field:

```python
    @computed_field
    @property
    def days_on_lot(self) -> int | None:
        if self.date_added is None:
            return None
        return (self.date_closed - self.date_added).days
```

- [ ] **Step 3: Verify**

Run: `cd backend && venv/bin/python -c "
from app.schemas.deal_history import DealHistoryOut
import json

entry = DealHistoryOut.model_validate({
    'id': 1, 'listing_id': 1, 'deal_type': 'sold',
    'brand': 'Toyota', 'model': 'Camry', 'year': '2020', 'vin': None,
    'seller_name': 'S', 'seller_phone': '+380501234567', 'buyer_name': None, 'buyer_phone': None,
    'final_price': 15000, 'purchase_price': 10000, 'additional_expenses': 500,
    'employee_name': None, 'employee_id': None,
    'date_closed': '2026-01-20', 'date_added': '2026-01-05', 'created_at': '2026-01-20T00:00:00Z',
})
print(json.loads(entry.model_dump_json())['days_on_lot'])
"`
Expected: `15` (Jan 5 → Jan 20).

---

### Task 5: Backend — end-to-end verification against the live containers

**Files:** none (verification only)

- [ ] **Step 1: Restart backend, confirm clean boot**

Run: `docker restart fs-nuxt-car-garage-tracker-backend-1`, wait, check logs for clean `Application startup complete`.

- [ ] **Step 2: Real API check — sell a listing, confirm `days_on_lot` matches**

Create a listing with a known `date_added` (or let it default to today), mark it sold, `GET /deal-history`, confirm `date_added` and `days_on_lot` are present and correct (0 if sold same day, or the real gap if `date_added` was set explicitly).

---

### Task 6: Frontend — `DealHistoryEntry` type gains `date_added`/`days_on_lot`

**Files:**
- Modify: `frontend/app/types/dealHistory.ts`

- [ ] **Step 1: Add the fields**

Change:

```ts
    date_closed: string
    created_at: string
```

to:

```ts
    date_closed: string
    date_added: string | null
    days_on_lot: number | null
    created_at: string
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "dealHistory" || echo "no errors"`
Expected: `no errors`

---

### Task 7: Frontend — `MonthlyProfitChart` sources from `DealHistoryEntry[]`

**Files:**
- Modify: `frontend/app/components/charts/MonthlyProfitChart.vue`

- [ ] **Step 1: Change the prop type and internal computation**

Change:

```ts
import type { Listing } from '~/types/listings'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ listings: Listing[] }>()

const { t, n } = useI18n()

const soldListings = computed<Listing[]>(() => props.listings.filter((listing) => listing.status === 'sold' && listing.date_sold))

const monthlyProfitTotals = computed<Map<string, number>>(() => {
  const totals = new Map<string, number>()

  for (const listing of soldListings.value) {
    const month = listing.date_sold!.slice(0, 7)
    totals.set(month, (totals.get(month) ?? 0) + listing.net_profit)
  }

  return new Map([...totals.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})
```

to:

```ts
import type { DealHistoryEntry } from '~/types/dealHistory'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ dealHistoryEntries: DealHistoryEntry[] }>()

const { t, n } = useI18n()

const soldDeals = computed<DealHistoryEntry[]>(() =>
  props.dealHistoryEntries.filter((entry) => entry.deal_type === 'sold' && entry.date_closed)
)

const monthlyProfitTotals = computed<Map<string, number>>(() => {
  const totals = new Map<string, number>()

  for (const entry of soldDeals.value) {
    const month = entry.date_closed.slice(0, 7)
    totals.set(month, (totals.get(month) ?? 0) + (entry.net_profit ?? 0))
  }

  return new Map([...totals.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})
```

- [ ] **Step 2: Update the template's empty-state check**

Change `v-if="soldListings.length === 0"` to `v-if="soldDeals.length === 0"`.

- [ ] **Step 3: Verify**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "MonthlyProfitChart" || echo "no errors"`
Expected: `no errors` (analytics.vue will show an error here until Task 11 updates its usage — that's expected mid-plan, not a Task 7 failure).

---

### Task 8: Frontend — `TopProfitListingsChart` sources from `DealHistoryEntry[]`

**Files:**
- Modify: `frontend/app/components/charts/TopProfitListingsChart.vue`

- [ ] **Step 1: Change the prop type and internal computation**

Change:

```ts
import type { Listing } from '~/types/listings'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ listings: Listing[] }>()

const { t, n } = useI18n()

const topListings = computed<Listing[]>(() =>
  [...props.listings].sort((a, b) => b.net_profit - a.net_profit).slice(0, 10)
)

const chartData = computed<ChartData<'bar'>>(() => ({
  labels: topListings.value.map((listing) => `${listing.brand} ${listing.model}, ${listing.year}`),
  datasets: [
    {
      label: t('crm.analytics.topProfitChart'),
      data: topListings.value.map((listing) => listing.net_profit),
      backgroundColor: CHART_PRIMARY_COLOR,
      borderRadius: 4,
      maxBarThickness: 24,
    },
  ],
}))
```

to:

```ts
import type { DealHistoryEntry } from '~/types/dealHistory'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const props = defineProps<{ dealHistoryEntries: DealHistoryEntry[] }>()

const { t, n } = useI18n()

// Ranking only ever makes sense across completed sales — a draft/active lot
// has no realized profit yet, so sold-only is correct here even though the
// previous Listing-sourced version didn't filter by status at all.
const topDeals = computed<DealHistoryEntry[]>(() =>
  [...props.dealHistoryEntries]
    .filter((entry) => entry.deal_type === 'sold' && entry.net_profit !== null)
    .sort((a, b) => (b.net_profit ?? 0) - (a.net_profit ?? 0))
    .slice(0, 10)
)

const chartData = computed<ChartData<'bar'>>(() => ({
  labels: topDeals.value.map((entry) => `${entry.brand} ${entry.model}, ${entry.year}`),
  datasets: [
    {
      label: t('crm.analytics.topProfitChart'),
      data: topDeals.value.map((entry) => entry.net_profit ?? 0),
      backgroundColor: CHART_PRIMARY_COLOR,
      borderRadius: 4,
      maxBarThickness: 24,
    },
  ],
}))
```

- [ ] **Step 2: Update the template's empty-state check**

Change `v-if="listings.length === 0"` to `v-if="topDeals.length === 0"`.

- [ ] **Step 3: Verify**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "TopProfitListingsChart" || echo "no errors"`
Expected: `no errors`

---

### Task 9: Frontend — `AverageDaysToSellChart` sources from `DealHistoryEntry[]`

**Files:**
- Modify: `frontend/app/components/charts/AverageDaysToSellChart.vue`

- [ ] **Step 1: Change the prop type and internal computation**

Change:

```ts
import type { Listing } from '~/types/listings'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale)

const props = defineProps<{ listings: Listing[] }>()

const { t, n } = useI18n()

const soldListings = computed<Listing[]>(() => props.listings.filter((listing) => listing.status === 'sold' && listing.date_sold))

const averageDaysByMonth = computed<Map<string, number>>(() => {
  const daysByMonth = new Map<string, number[]>()

  for (const listing of soldListings.value) {
    const month = listing.date_sold!.slice(0, 7)
    const existingDays = daysByMonth.get(month) ?? []
    existingDays.push(listing.days_on_lot)
    daysByMonth.set(month, existingDays)
  }

  const averages = new Map<string, number>()
  for (const [month, daysList] of daysByMonth) {
    averages.set(month, daysList.reduce((sum, days) => sum + days, 0) / daysList.length)
  }

  return new Map([...averages.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})
```

to:

```ts
import type { DealHistoryEntry } from '~/types/dealHistory'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale)

const props = defineProps<{ dealHistoryEntries: DealHistoryEntry[] }>()

const { t, n } = useI18n()

// days_on_lot is null for any deal recorded before the date_added snapshot
// existed AND whose Listing has since been deleted (unrecoverable) — those
// are excluded here rather than treated as 0, which would silently drag
// the monthly average down.
const soldDealsWithDaysOnLot = computed<DealHistoryEntry[]>(() =>
  props.dealHistoryEntries.filter((entry) => entry.deal_type === 'sold' && entry.date_closed && entry.days_on_lot !== null)
)

const averageDaysByMonth = computed<Map<string, number>>(() => {
  const daysByMonth = new Map<string, number[]>()

  for (const entry of soldDealsWithDaysOnLot.value) {
    const month = entry.date_closed.slice(0, 7)
    const existingDays = daysByMonth.get(month) ?? []
    existingDays.push(entry.days_on_lot!)
    daysByMonth.set(month, existingDays)
  }

  const averages = new Map<string, number>()
  for (const [month, daysList] of daysByMonth) {
    averages.set(month, daysList.reduce((sum, days) => sum + days, 0) / daysList.length)
  }

  return new Map([...averages.entries()].sort(([monthA], [monthB]) => monthA.localeCompare(monthB)))
})
```

- [ ] **Step 2: Update the template's empty-state check**

Change `v-if="soldListings.length === 0"` to `v-if="soldDealsWithDaysOnLot.length === 0"`.

- [ ] **Step 3: Verify**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "AverageDaysToSellChart" || echo "no errors"`
Expected: `no errors`

---

### Task 10: Frontend — `ListingStatusChart` and `ListingStatusCountsGrid` gain the same overrides on this page

**Files:**
- Modify: `frontend/app/components/charts/ListingStatusChart.vue`

**Interfaces:**
- `ListingStatusCountsGrid` already has `soldCountOverride`/`removedCountOverride` (added for the Dashboard) — no change needed there, Task 11 just needs to pass them on this page too.

- [ ] **Step 1: Add the same override props to `ListingStatusChart`**

Change:

```ts
const props = defineProps<{ listings: Listing[] }>()

const { t } = useI18n()

const STATUS_ORDER: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed']

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

const STATUS_ORDER: ListingStatus[] = ['draft', 'active', 'reserved', 'sold', 'removed']

// Same override mechanism as ListingStatusCountsGrid (see that component's
// comment for the full rationale) — sold/removed come from the caller's
// DealHistory-sourced counts when provided, since live Listing rows for
// those statuses get deleted by the archive-cleanup job over time.
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

- [ ] **Step 2: Verify**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "ListingStatusChart" || echo "no errors"`
Expected: `no errors`

---

### Task 11: Frontend — wire `analytics.vue` to DealHistory for every sold/profit metric

**Files:**
- Modify: `frontend/app/pages/crm/analytics.vue`

**Interfaces:**
- Consumes: `useDealHistoryStore` (existing, already role-scoped server-side); the updated chart prop contracts from Tasks 7–10.

- [ ] **Step 1: Fetch deal history and derive scoped sold/removed sets**

Change:

```ts
const authStore = useAuthStore()
const listingStore = useListingStore()

await listingStore.fetchListings()

const isEmployee = computed<boolean>(() => authStore.user?.role === 'employee')

// Scope everything below to "my own listings" for an employee — every KPI,
// chart, and the overdue-deadlines list all derive from this one filtered
// set instead of touching listingStore.listings directly. The aggregation
// logic itself (grouping by month, formulas, etc.) is untouched; only the
// input set changes.
const scopedListings = computed<Listing[]>(() => {
  if (!isEmployee.value) {
    return listingStore.listings
  }
  const currentUserId = authStore.user?.id
  return listingStore.listings.filter((listing) => listing.seller?.employee_id === currentUserId)
})
```

to:

```ts
const authStore = useAuthStore()
const listingStore = useListingStore()
const dealHistoryStore = useDealHistoryStore()

await Promise.all([listingStore.fetchListings(), dealHistoryStore.fetchDealHistory()])

const isEmployee = computed<boolean>(() => authStore.user?.role === 'employee')

// Scope everything below to "my own listings" for an employee — every
// Listing-sourced KPI/chart (current inventory state: active count, overdue
// deadlines, draft/active/reserved counts) derives from this one filtered
// set. Anything DealHistory-sourced (sold/removed counts, profit, margin,
// the profit/days-on-lot charts) does NOT need this filter — the backend
// already scopes GET /deal-history to the employee's own deals, exactly
// like the Deal History page and the Dashboard.
const scopedListings = computed<Listing[]>(() => {
  if (!isEmployee.value) {
    return listingStore.listings
  }
  const currentUserId = authStore.user?.id
  return listingStore.listings.filter((listing) => listing.seller?.employee_id === currentUserId)
})

const soldDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'sold'))
const removedDeals = computed(() => dealHistoryStore.entries.filter((entry) => entry.deal_type === 'removed'))
```

- [ ] **Step 2: Replace `averageMarginPercent` and `totalNetProfit`**

Change:

```ts
const soldListings = computed<Listing[]>(() => scopedListings.value.filter((listing) => listing.status === 'sold'))

const averageMarginPercent = computed<number | null>(() => {
  const listingsWithCost = soldListings.value.filter((listing) => listing.total_cost > 0)
  if (listingsWithCost.length === 0) {
    return null
  }

  const totalMargin = listingsWithCost.reduce((sum, listing) => sum + (listing.net_profit / listing.total_cost) * 100, 0)
  return totalMargin / listingsWithCost.length
})

const totalNetProfit = computed<number>(() => soldListings.value.reduce((sum, listing) => sum + listing.net_profit, 0))
```

to:

```ts
const averageMarginPercent = computed<number | null>(() => {
  const dealsWithCost = soldDeals.value.filter((entry) => {
    const totalCost = (entry.purchase_price ?? 0) + (entry.additional_expenses ?? 0)
    return entry.net_profit !== null && totalCost > 0
  })
  if (dealsWithCost.length === 0) {
    return null
  }

  const totalMargin = dealsWithCost.reduce((sum, entry) => {
    const totalCost = (entry.purchase_price ?? 0) + (entry.additional_expenses ?? 0)
    return sum + ((entry.net_profit ?? 0) / totalCost) * 100
  }, 0)
  return totalMargin / dealsWithCost.length
})

const totalNetProfit = computed<number>(() => soldDeals.value.reduce((sum, entry) => sum + (entry.net_profit ?? 0), 0))
```

Note: `activeCount` and `overdueListings` below this in the file are **unchanged** — they still read `scopedListings`.

- [ ] **Step 3: Pass the overrides to `ListingStatusCountsGrid`**

Change:

```html
      <ListingStatusCountsGrid :listings="scopedListings" />
```

to:

```html
      <ListingStatusCountsGrid
        :listings="scopedListings"
        :sold-count-override="soldDeals.length"
        :removed-count-override="removedDeals.length"
      />
```

- [ ] **Step 4: Update the chart usages**

Change:

```html
      <MonthlyProfitChart v-if="activeChart === 'monthly-profit'" :listings="scopedListings" />
      <ListingStatusChart v-else-if="activeChart === 'status'" :listings="scopedListings" />
      <AverageDaysToSellChart v-else-if="activeChart === 'avg-days'" :listings="scopedListings" />
      <TopProfitListingsChart v-else-if="activeChart === 'top-profit'" :listings="scopedListings" />
```

to:

```html
      <MonthlyProfitChart v-if="activeChart === 'monthly-profit'" :deal-history-entries="soldDeals" />
      <ListingStatusChart
        v-else-if="activeChart === 'status'"
        :listings="scopedListings"
        :sold-count-override="soldDeals.length"
        :removed-count-override="removedDeals.length"
      />
      <AverageDaysToSellChart v-else-if="activeChart === 'avg-days'" :deal-history-entries="soldDeals" />
      <TopProfitListingsChart v-else-if="activeChart === 'top-profit'" :deal-history-entries="soldDeals" />
```

- [ ] **Step 5: Verify full type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json`
Expected: no output (clean) — this is the point where all the mid-plan "expected" errors from Tasks 7–10 should now be resolved.

---

### Task 12: End-to-end verification (the pause requested by the user)

**Files:** none (verification only)

- [ ] **Step 1: Restart the frontend container**

Run: `docker restart fs-nuxt-car-garage-tracker-frontend-1`, wait for clean startup.

- [ ] **Step 2: Compare Analytics vs Dashboard for the same owner and employee**

Using accounts with real sold/removed data (reuse or extend the scenario from the Dashboard task): for the **owner**, confirm `/crm/analytics` "Загальний прибуток за весь час" exactly equals `/crm` "Загальний чистий прибуток (продано)" for that company. For the **employee**, confirm the same equality holds for their personal-scope numbers, and confirm neither page leaks the other role's totals (spot-check via direct API comparison against `GET /deal-history` for each token, same as the Dashboard task's verification).

- [ ] **Step 3: Confirm the charts render without errors**

Visit `/crm/analytics`, switch through all four chart tabs, confirm each renders (or shows its correct empty state if there's no data) with no console errors — particularly `AverageDaysToSellChart`, since it depends on the new `date_added` backfill.

- [ ] **Step 4: Confirm draft/active/reserved-related stats are untouched**

Confirm "Активних лотів" (`activeCount`) and the overdue-deadlines list still reflect live `Listing` data exactly as before — create a `draft`/`active` listing with a past deadline if needed to exercise this.

- [ ] **Step 5: Report the final numbers to the user**

Per the user's request: write the Analytics vs Dashboard comparison numbers in chat, and note explicitly whether they match exactly (expected, since Analytics has no date-range filter on this page) or if you found any discrepancy.
