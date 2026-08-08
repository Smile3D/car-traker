# Employee Listing Ownership Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `role=employee` users from editing, deleting, closing, or drag-repositioning a listing ("лот") that is assigned to a *different* employee, while keeping all read access (Inventory, Kanban, Archive, listing details) exactly as it is today; also fully hide the company-wide "total net profit" card on the Dashboard from employees.

**Architecture:** A single access rule — `current_user.role == 'employee' AND seller.employee_id NOT IN (null, current_user.id)` → forbidden — is centralized in one backend helper module and reused by every write endpoint that touches a listing (listings CRUD/mark-sold, listing photos, and the seller-`Client` PATCH that the Kanban drag uses). The frontend mirrors the same rule to hide affected buttons/drag interactions, but the backend is the actual enforcement boundary; the frontend changes are UX, not security.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Nuxt 3 / Vue 3 + Pinia (frontend), vuedraggable (Kanban).

## Global Constraints

- Exact 403 message (Ukrainian, verbatim, used both as the backend `HTTPException.detail` and the frontend notice text): `Цей лот закріплений за іншим співробітником, ви не можете його редагувати`
- `role=owner` behavior must not change anywhere in this plan — every guard below is `if current_user.role == "employee"`.
- The ownership signal is always read from the seller `Client.employee_id` for the listing in question (`listing.seller.employee_id`, or `client.employee_id` directly when already holding the seller `Client` row) — never introduce a second source of truth.
- **No automated test suite exists in this repo today** (no pytest/vitest configured, no `conftest.py`, `requirements.txt` has no `pytest`). Adding a whole new test framework is out of scope for this fix and wasn't requested. Verification is manual: run both dev servers and exercise the flows described in each task (curl for backend status codes, browser for frontend), matching the manual QA protocol the user asked for at the end of this task. Do not introduce a testing framework as a side effect of this plan.
- Follow existing code style exactly: full descriptive names, no abbreviations, comments only where they explain *why* (see the existing docstring-style comments in `listings.py`/`dependencies.py` as the bar).

---

### Task 1: Backend — shared listing-ownership helper

**Files:**
- Create: `backend/app/services/listing_authorization.py`

**Interfaces:**
- Produces: `is_listing_locked_for_employee(seller_employee_id: int | None, current_user: User) -> bool` and `ensure_employee_can_act_on_listing(seller_employee_id: int | None, current_user: User) -> None` (raises `HTTPException(403)`), plus the constant `LISTING_LOCKED_FOR_EMPLOYEE_DETAIL: str`. Every later task imports from this module — do not duplicate the rule.

- [ ] **Step 1: Write the module**

```python
from fastapi import HTTPException, status

from app.models.user import User

LISTING_LOCKED_FOR_EMPLOYEE_DETAIL = "Цей лот закріплений за іншим співробітником, ви не можете його редагувати"


def is_listing_locked_for_employee(seller_employee_id: int | None, current_user: User) -> bool:
    """True when `current_user` is an employee and the listing's seller Client
    is assigned to a DIFFERENT employee. An unassigned listing (None) and a
    listing assigned to `current_user` themselves are both left unlocked —
    only someone else's assignment blocks access."""
    return (
        current_user.role == "employee"
        and seller_employee_id is not None
        and seller_employee_id != current_user.id
    )


def ensure_employee_can_act_on_listing(seller_employee_id: int | None, current_user: User) -> None:
    if is_listing_locked_for_employee(seller_employee_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=LISTING_LOCKED_FOR_EMPLOYEE_DETAIL)
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd backend && venv/bin/python -c "from app.services.listing_authorization import ensure_employee_can_act_on_listing, is_listing_locked_for_employee, LISTING_LOCKED_FOR_EMPLOYEE_DETAIL; print('ok')"`
Expected: `ok`

---

### Task 2: Backend — `get_actionable_listing` dependency

**Files:**
- Modify: `backend/app/dependencies.py`

**Interfaces:**
- Consumes: `is_listing_locked_for_employee`/`ensure_employee_can_act_on_listing` from Task 1; existing `get_owned_listing`, `require_company_member`.
- Produces: `get_actionable_listing(...) -> Listing` — a FastAPI dependency, drop-in replacement for `get_owned_listing` wherever the endpoint performs a write action instead of a read.

- [ ] **Step 1: Add the import**

In `backend/app/dependencies.py`, add alongside the existing imports:

```python
from app.services.listing_authorization import ensure_employee_can_act_on_listing
```

- [ ] **Step 2: Add the dependency function**

Append after `get_owned_listing`:

```python
def get_actionable_listing(
    listing: Listing = Depends(get_owned_listing),
    current_user: User = Depends(require_company_member),
) -> Listing:
    """Same company-scoped lookup as get_owned_listing, plus the employee
    ownership gate — use this instead of get_owned_listing on any endpoint
    that WRITES to a listing (or its photos); keep get_owned_listing on
    read-only endpoints, since employees can still view every company
    listing, just not act on someone else's."""
    seller_employee_id = listing.seller.employee_id if listing.seller is not None else None
    ensure_employee_can_act_on_listing(seller_employee_id, current_user)
    return listing
```

- [ ] **Step 3: Verify it imports cleanly**

Run: `cd backend && venv/bin/python -c "from app.dependencies import get_actionable_listing; print('ok')"`
Expected: `ok`

---

### Task 3: Backend — gate PATCH/DELETE/mark-sold on `/listings/{id}`

**Files:**
- Modify: `backend/app/routers/listings.py`

**Interfaces:**
- Consumes: `get_actionable_listing` from Task 2.

- [ ] **Step 1: Update the import line**

Change:

```python
from app.dependencies import get_owned_listing, require_company_member
```

to:

```python
from app.dependencies import get_actionable_listing, get_owned_listing, require_company_member
```

- [ ] **Step 2: Swap the dependency on the three write endpoints**

In `update_listing`, `delete_listing`, and `mark_listing_sold`, change the `listing: Listing = Depends(get_owned_listing)` parameter to `listing: Listing = Depends(get_actionable_listing)`. `read_listing` (the GET) keeps `get_owned_listing` unchanged.

- [ ] **Step 3: Verify the app still imports**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 4: Backend — partial-skip bulk delete

**Files:**
- Modify: `backend/app/schemas/listing.py`
- Modify: `backend/app/routers/listings.py`

**Interfaces:**
- Produces: `ListingBulkDeleteResult` now has `deleted_ids: list[int]` and `skipped: list[str]` in addition to the existing `deleted_count`. Frontend Task 8 consumes `deleted_ids` and `skipped`.

- [ ] **Step 1: Extend the schema**

In `backend/app/schemas/listing.py`, change:

```python
class ListingBulkDeleteResult(BaseModel):
    deleted_count: int
```

to:

```python
class ListingBulkDeleteResult(BaseModel):
    deleted_count: int
    deleted_ids: list[int] = []
    skipped: list[str] = []
```

- [ ] **Step 2: Rewrite `bulk_delete_listings`**

In `backend/app/routers/listings.py`, add the import (same line touched in Task 3) — also import `is_listing_locked_for_employee`:

```python
from app.services.listing_authorization import is_listing_locked_for_employee
```

Replace the whole `bulk_delete_listings` function body with:

```python
@router.post("/bulk-delete", response_model=ListingBulkDeleteResult)
def bulk_delete_listings(
    bulk_delete_input: ListingBulkDeleteInput,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> ListingBulkDeleteResult:
    listings_to_consider = (
        database_session.query(Listing)
        .options(joinedload(Listing.seller))
        .filter(Listing.id.in_(bulk_delete_input.ids), Listing.company_id == current_user.company_id)
        .all()
    )

    deletable_ids: list[int] = []
    skipped_messages: list[str] = []
    for listing in listings_to_consider:
        seller_employee_id = listing.seller.employee_id if listing.seller is not None else None
        if is_listing_locked_for_employee(seller_employee_id, current_user):
            skipped_messages.append(
                f"Лот «{listing.brand} {listing.model}» закріплений за іншим співробітником і був пропущений"
            )
            continue
        deletable_ids.append(listing.id)

    deleted_count = 0
    if deletable_ids:
        deleted_count = (
            database_session.query(Listing)
            .filter(Listing.id.in_(deletable_ids))
            .delete(synchronize_session=False)
        )
        database_session.commit()

    return ListingBulkDeleteResult(deleted_count=deleted_count, deleted_ids=deletable_ids, skipped=skipped_messages)
```

- [ ] **Step 3: Verify the app still imports**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 5: Backend — gate listing-photo write endpoints

**Files:**
- Modify: `backend/app/routers/listing_photos.py`

**Interfaces:**
- Consumes: `get_actionable_listing` from Task 2.

- [ ] **Step 1: Update the import line**

Change:

```python
from app.dependencies import get_owned_listing
```

to:

```python
from app.dependencies import get_actionable_listing, get_owned_listing
```

- [ ] **Step 2: Swap the dependency on the write endpoints**

Change `listing: Listing = Depends(get_owned_listing)` to `listing: Listing = Depends(get_actionable_listing)` in `upload_listing_photos`, `reorder_listing_photos`, and `delete_listing_photo`. Leave `list_listing_photos` and `get_listing_photo_file` on `get_owned_listing` (read-only).

- [ ] **Step 3: Verify the app still imports**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 6: Backend — gate the seller-`Client` PATCH (closes the Kanban-drag API hole)

**Why this task exists:** `PATCH /clients/{id}` is what `ClientKanbanBoard.vue` calls when a card is dropped in a new column (`clientStore.updateClient(movedClient.id, { stage_id: stageId })`). Today it has no ownership check at all — any company member can PATCH any client, including reassigning `employee_id` or moving `stage_id` on a seller `Client` (i.e. a "lot") that belongs to someone else. Hiding the drag in the UI (Task 9) is not sufficient on its own; without this task, an employee could still call the endpoint directly.

**Files:**
- Modify: `backend/app/routers/clients.py`

**Interfaces:**
- Consumes: `ensure_employee_can_act_on_listing` from Task 1.

- [ ] **Step 1: Add the import**

```python
from app.services.listing_authorization import ensure_employee_can_act_on_listing
```

- [ ] **Step 2: Guard `update_client` for seller-type clients**

At the very top of `update_client`'s body (before `update_data = ...`), add:

```python
    if client.client_type == "seller":
        ensure_employee_can_act_on_listing(client.employee_id, current_user)
```

This only restricts `client_type == "seller"` (the "lot") — buyer-type clients are a separate relationship, not a "lot", and are unaffected.

- [ ] **Step 3: Verify the app still imports**

Run: `cd backend && venv/bin/python -c "from app.main import app; print('ok')"`
Expected: `ok`

---

### Task 7: Backend — manual verification of every gated endpoint

**Files:** none (verification only)

- [ ] **Step 1: Start the backend**

Run: `cd backend && venv/bin/uvicorn app.main:app --reload` (leave running)

- [ ] **Step 2: Seed and exercise the scenario via curl**

Using the running backend and its existing `/auth/register` + `/auth/login` + `/employee_invites` flow (see `backend/app/routers/auth.py` and `employee_invites.py` for the exact request shapes), create: one owner account with a company, two employee accounts (A and B) invited into that company, and one listing created by/assigned to employee A (`seller.employee_id == A.id`).

Then, authenticated as employee B, confirm:
- `PATCH /listings/{id}` on A's listing → `403` with detail `Цей лот закріплений за іншим співробітником, ви не можете його редагувати`
- `DELETE /listings/{id}` on A's listing → `403`, same detail
- `POST /listings/{id}/mark-sold` on A's listing → `403`, same detail
- `POST /listings/{id}/photos` (upload) on A's listing → `403`, same detail
- `PATCH /listings/{id}/photos/reorder` on A's listing → `403`, same detail
- `DELETE /listings/{id}/photos/{photo_id}` on A's listing → `403`, same detail
- `PATCH /clients/{seller_client_id}` (A's seller client, e.g. `{"stage_id": <some other stage>}`) → `403`, same detail
- `GET /listings/{id}` on A's listing → `200` (read stays open)
- `POST /listings/bulk-delete` with `{"ids": [A's listing id, B's own listing id]}` → `200`, B's own listing gets deleted, A's listing id is **not** in `deleted_ids` and a message about it appears in `skipped`

Then, authenticated as employee A (the assignee) and separately as the owner, repeat the same write calls on A's listing and confirm all return `200`/`204` as before — no regression for the rightful assignee or the owner.

Expected: all of the above match exactly. If any status code or detail differs, stop and fix before moving to the frontend tasks.

- [ ] **Step 3: Also confirm the "unassigned" case**

Create a listing with no seller `employee_id` set (owner-created, no employee assigned). As employee B, `PATCH` it → `200` (unassigned listings are actionable by any employee, per the access rule).

---

### Task 8: Frontend — inventory detail page hides actions on a foreign listing

**Files:**
- Modify: `frontend/app/pages/crm/inventory/[id].vue`
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

**Interfaces:**
- Consumes: `getEmployeeDisplayName` from `~/utils/employeeDisplayName` (existing util, already used in `ListingSellerSection.vue`); `authStore.user` (existing `useAuthStore()`, already instantiated in this file at line 11); `listing.value.seller` (existing `ListingSellerSummary | null` — has `employee_id` and `employee`).

- [ ] **Step 1: Add the import**

At the top of `frontend/app/pages/crm/inventory/[id].vue`, add:

```ts
import { getEmployeeDisplayName } from '~/utils/employeeDisplayName'
```

- [ ] **Step 2: Add the ownership computeds**

Right after the existing `const isArchived = computed<boolean>(...)` block (around line 70), add:

```ts
const isEmployee = computed<boolean>(() => authStore.user?.role === 'employee')

const responsibleEmployeeId = computed<number | null>(() => listing.value?.seller?.employee_id ?? null)

// Mirrors the backend rule in listing_authorization.py: unassigned (null) or
// self-assigned stays actionable; assigned to someone else is locked.
const isForeignListing = computed<boolean>(() =>
  isEmployee.value && responsibleEmployeeId.value !== null && responsibleEmployeeId.value !== authStore.user?.id
)

const responsibleEmployeeName = computed<string | undefined>(() =>
  getEmployeeDisplayName(listing.value?.seller?.employee ?? null, listing.value?.seller?.employee?.email)
)
```

- [ ] **Step 3: Hide the three action buttons**

In the template, change the three buttons' `v-if`:

```html
<button
  v-if="!isEditMode && !isArchived && !isForeignListing"
  ...
  @click="handleEditClick"
>
```

```html
<button
  v-if="listing.status !== 'sold' && !isForeignListing"
  ...
  @click="isMarkSoldModalOpen = true"
>
```

```html
<button
  v-if="!isArchived && !isForeignListing"
  ...
  @click="isDeleteConfirmOpen = true"
>
```

- [ ] **Step 4: Add the notice banner**

Immediately after the closing `</div>` of the `ListingDetailsHeader` block (before `<ListingSellerSection`), add:

```html
<!-- ForeignListingNotice -->
<div
  v-if="isForeignListing"
  class="flex items-center gap-2 rounded-lg border border-border-strong bg-muted/50 p-4 text-sm text-muted-foreground"
  role="status"
>
  <span>
    {{ t('listingDetails.foreignListingNotice') }}<template v-if="responsibleEmployeeName"> ({{ responsibleEmployeeName }})</template>
  </span>
</div>
```

- [ ] **Step 5: Add the locale strings**

In `frontend/locales/uk.json`, inside the `listingDetails` object, add:

```json
"foreignListingNotice": "Цей лот закріплений за іншим співробітником",
```

In `frontend/locales/ru.json`, inside the `listingDetails` object, add:

```json
"foreignListingNotice": "Этот лот закреплён за другим сотрудником",
```

- [ ] **Step 6: Verify JSON stays valid**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('ok')"`
Expected: `ok`

---

### Task 9: Frontend — block Kanban drag of a foreign lot

**Files:**
- Modify: `frontend/app/components/clients/ClientKanbanBoard.vue`

**Interfaces:**
- Consumes: `authStore.user` (already instantiated at line 19); `props.clientType`; vuedraggable's `move` prop (called on every drag-over with `{ draggedContext: { element } }`, return `false` to cancel the drop).

- [ ] **Step 1: Add `useI18n`**

At the top of the `<script setup>` block, add:

```ts
const { t } = useI18n()
```

- [ ] **Step 2: Add the lock check and move handler**

After the existing `const dragError = ref<string | null>(null)` line, add:

```ts
// Mirrors the backend rule in listing_authorization.py: only the "seller"
// board represents lots — the "buyer" board is a different relationship
// and isn't restricted here. Unassigned/self-assigned stays draggable.
function isSellerLockedForCurrentEmployee(client: Client): boolean {
  return (
    props.clientType === 'seller'
    && authStore.user?.role === 'employee'
    && client.employee_id !== null
    && client.employee_id !== authStore.user.id
  )
}

function handleMove(evt: { draggedContext: { element: Client } }): boolean {
  if (isSellerLockedForCurrentEmployee(evt.draggedContext.element)) {
    dragError.value = t('listingDetails.foreignListingNotice')
    return false
  }
  return true
}
```

- [ ] **Step 3: Wire it into the draggable component**

On the `<draggable ... @change="handleColumnChange(stage.id, $event)">` element, add the `:move` binding:

```html
<draggable
  :list="columns[stage.id]"
  group="clients-board"
  item-key="id"
  class="flex min-h-[4rem] flex-1 flex-col gap-2"
  ghost-class="opacity-40"
  :move="handleMove"
  @change="handleColumnChange(stage.id, $event)"
>
```

- [ ] **Step 4: Verify locale key reuse**

No new locale key needed — `listingDetails.foreignListingNotice` already exists from Task 8. Run the same JSON-validity check as Task 8 Step 6 if any edits were made to the locale files in this task (there shouldn't be any).

---

### Task 10: Frontend — surface bulk-delete skip messages on the Archive page

**Files:**
- Modify: `frontend/app/stores/listings.ts`
- Modify: `frontend/app/pages/crm/archive.vue`
- Modify: `frontend/locales/uk.json` (only if the section header text below needs a key — see Step 3)
- Modify: `frontend/locales/ru.json` (same)

**Interfaces:**
- Produces: `bulkDeleteListings(listingIds: number[]): Promise<{ deletedCount: number, skippedMessages: string[] }>` (return type changes from `Promise<number>`).

- [ ] **Step 1: Update the store**

In `frontend/app/stores/listings.ts`, replace `bulkDeleteListings`:

```ts
const bulkDeleteListings = async (listingIds: number[]): Promise<{ deletedCount: number, skippedMessages: string[] }> => {
    isLoading.value = true
    error.value = null
    try {
        const result = await apiPost<{ deleted_count: number, deleted_ids: number[], skipped: string[] }>('/listings/bulk-delete', { ids: listingIds })
        const deletedIds = new Set(result.deleted_ids)
        listings.value = listings.value.filter((listing) => !deletedIds.has(listing.id))
        return { deletedCount: result.deleted_count, skippedMessages: result.skipped }
    } catch (e) {
        error.value = (e as ApiError).message
        throw e
    } finally {
        isLoading.value = false
    }
}
```

- [ ] **Step 2: Update the Archive page**

In `frontend/app/pages/crm/archive.vue`, add a ref near the other bulk-delete refs (`isBulkDeleteConfirmOpen`, `isBulkDeleting`):

```ts
const bulkDeleteSkippedMessages = ref<string[]>([])
```

Replace `handleBulkDeleteConfirm`:

```ts
async function handleBulkDeleteConfirm(): Promise<void> {
  isBulkDeleting.value = true
  try {
    const { skippedMessages } = await listingStore.bulkDeleteListings(selectedIds.value)
    bulkDeleteSkippedMessages.value = skippedMessages
    selectedIds.value = []
  } finally {
    isBulkDeleting.value = false
    isBulkDeleteConfirmOpen.value = false
  }
}
```

- [ ] **Step 3: Add the skip-message banner**

In the template, right before the `<!-- BulkActionsBar -->` comment, add:

```html
<!-- BulkDeleteSkippedNotice -->
<div
  v-if="bulkDeleteSkippedMessages.length > 0"
  class="flex items-start justify-between gap-2 rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
  role="alert"
>
  <ul class="list-disc space-y-1 pl-4">
    <li v-for="message in bulkDeleteSkippedMessages" :key="message">{{ message }}</li>
  </ul>
  <button type="button" class="shrink-0 font-medium hover:underline" @click="bulkDeleteSkippedMessages = []">
    {{ t('common.buttons.close') }}
  </button>
</div>
```

No new locale keys are needed — the skip messages come pre-formatted (in Ukrainian) from the backend response, and `common.buttons.close` already exists (used elsewhere in this codebase, e.g. `[id].vue`'s photo-upload-failure banner).

- [ ] **Step 4: Verify JSON/type-check**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('ok')"` (only relevant if you touched the locale files; skip otherwise)
Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "archive.vue\|stores/listings.ts" || echo "no errors in touched files"`
Expected: `no errors in touched files` (pre-existing unrelated errors elsewhere in the project, if any, are not this task's concern)

---

### Task 11: Frontend — hide the Dashboard's total-net-profit card for employees

**Files:**
- Modify: `frontend/app/pages/crm/index.vue`

**Interfaces:** none beyond the existing `useAuthStore()` composable.

- [ ] **Step 1: Add the auth store and role computed**

Change:

```ts
const { t, n } = useI18n()

const listingStore = useListingStore()
```

to:

```ts
const { t, n } = useI18n()

const authStore = useAuthStore()
const listingStore = useListingStore()

const isOwner = computed<boolean>(() => authStore.user?.role === 'owner')
```

- [ ] **Step 2: Gate the card**

Change:

```html
    <!-- TotalNetProfitCard -->
    <div class="max-w-sm rounded-lg border border-border bg-surface p-5 shadow-card">
```

to:

```html
    <!-- TotalNetProfitCard -->
    <div v-if="isOwner" class="max-w-sm rounded-lg border border-border bg-surface p-5 shadow-card">
```

- [ ] **Step 3: Verify type-check**

Run: `cd frontend && npx vue-tsc --noEmit -p tsconfig.json 2>&1 | grep -i "pages/crm/index.vue" || echo "no errors in touched file"`
Expected: `no errors in touched file`

---

### Task 12: Full manual QA pass (the checkpoint the user asked for)

**Files:** none (verification only)

- [ ] **Step 1: Start both dev servers**

Backend: `cd backend && venv/bin/uvicorn app.main:app --reload`
Frontend: `cd frontend && npm run dev`

- [ ] **Step 2: Reuse the seed data from Task 7**

Owner + company, employee A, employee B, one listing assigned to A (`seller.employee_id == A.id`).

- [ ] **Step 3: As employee B, in the browser**

- Open `/crm/inventory`, confirm A's listing is still visible in the list (read access unchanged).
- Open its detail page `/crm/inventory/{id}`: confirm "Редагувати", "Позначити проданим", "Видалити" are all absent, and the notice "Цей лот закріплений за іншим співробітником (A's name)" is shown; confirm every other field/section on the page still renders normally (read-only, not hidden).
- Open `/crm/clients`, "Продавці" (seller) tab, Kanban view: attempt to drag A's card to another column — confirm it snaps back / does not move, and an error notice appears.
- Open `/crm/inventory/new` and create a brand-new listing (self-assigned by default per `create_listing`'s employee self-assign rule) — confirm all three action buttons ARE present on its own detail page.

- [ ] **Step 4: As the owner, in the browser**

- Confirm all three action buttons are present and functional on A's listing (edit, mark sold, delete all still work).
- Confirm the Kanban drag still works for any card regardless of assigned employee.
- Confirm the Dashboard's "Загальний чистий прибуток (продано)" card is still visible.

- [ ] **Step 5: As employee B again**

- Open `/crm` (Dashboard): confirm the "Загальний чистий прибуток (продано)" card is completely absent (not just filtered — gone).

- [ ] **Step 6: Report results**

Confirm every check above passed before considering this plan done. If anything fails, fix it and re-run only the failing check (no need to redo the whole pass).
