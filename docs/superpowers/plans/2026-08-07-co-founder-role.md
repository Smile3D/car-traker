# Co-Founder Role Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third user role, `co_founder`, with permissions identical to `owner` everywhere in the app EXCEPT one strict exception: only the real `owner` may promote an employee to co_founder, demote a co_founder back to employee, or deactivate a co_founder's account.

**Architecture:** `users.role` stays a plain `String(20)` (already unconstrained, no boolean/enum to migrate) — a new Alembic migration adds a `CHECK (role IN ('owner','co_founder','employee'))` constraint and the Pydantic/TypeScript `CompanyRole` literal grows a third value. Backend authorization currently funnels almost everything through one dependency, `require_company_owner`; this plan adds a second dependency, `require_company_admin` (owner OR co_founder), and swaps it in everywhere that isn't the two explicit exceptions. Roughly ten inline `current_user.role == "employee"` checks scattered across other routers need **no changes** — verified during design that all of them treat `"employee"` as the sole restricted branch, so `co_founder` (which is never `"employee"`) automatically lands in the unrestricted branch. On the frontend, a new `useUserRole()` composable replaces 16 independently-duplicated `isOwner`/`isCompanyOwner`/`isEmployee`/`canManageEmployees` definitions across 14 files with three shared computeds (`isOwner`, `isCoFounder`, `isEmployee`) plus one derived one (`isCompanyAdmin = isOwner || isCoFounder`).

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend, Postgres), Nuxt 3 / Vue 3 + Pinia (frontend), `@nuxtjs/i18n` (uk/ru locale files).

## Global Constraints

- The role-assignment endpoint (`PATCH /employees/{id}/role`) and the co-founder-account-deactivation guard inside `update_employee` are the ONLY two places that must stay strictly `owner`-only (`require_company_owner`, or `current_user.role == "owner"` inline) — everywhere else currently gated to owner-only becomes owner-or-co-founder (`require_company_admin`).
- On the frontend, the promote/demote-co-founder control is the ONLY place that uses `isOwner` where every other previously-owner-gated site uses `isCompanyAdmin` — see the per-file mapping in Task 10, it is not uniform.
- `users.role` column type does NOT change (stays `String(20)`, no Postgres ENUM type) — only a CHECK constraint is added. Do not introduce a SQLAlchemy `Enum`.
- No invite-directly-as-co-founder flow — `POST /auth/register` with `invite_token` always creates `role="employee"`, unchanged. Co-founder is reached only by promoting an existing employee via the new endpoint.
- `_get_owned_active_employee_or_error` in `listings.py` and `clients.py` (the "assignable responsible employee" lookups) stay filtered to `role == "employee"` only — co-founders are not made assignable sellers, out of scope.
- No new automated test infrastructure (confirmed with the user: this backend has zero existing tests, previous features shipped without them) — every task ends with a manual verification step (`curl`/browser) instead of a pytest run.
- Follow existing code style: full descriptive names, no abbreviations, comments only where they explain *why*.
- `npm run check:i18n` must pass (uk.json/ru.json key parity) before this is considered done — the script does not exist yet, Task 14 creates it.

---

### Task 1: Backend — allow `co_founder` as a valid `role` value

**Files:**
- Create: `backend/alembic/versions/<generated>_add_co_founder_role_check_constraint.py`
- Modify: `backend/app/schemas/user.py:8`

**Interfaces:**
- Produces: DB-level guarantee that `users.role` is one of `'owner'`, `'co_founder'`, `'employee'`, or `NULL`. `CompanyRole` Pydantic literal now accepts `"co_founder"`.

- [ ] **Step 1: Generate the migration file**

Run: `cd backend && source venv/bin/activate && alembic revision -m "add co_founder role check constraint"`

This creates a new file in `backend/alembic/versions/` with a fresh revision id and `down_revision = 'b7699ff44960'` (current head) auto-filled. Note the generated filename/revision id for the next step.

- [ ] **Step 2: Fill in upgrade/downgrade**

Edit the generated file's `upgrade()`/`downgrade()`:

```python
def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role_valid",
        "users",
        "role IN ('owner', 'co_founder', 'employee')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role_valid", "users", type_="check")
```

(NULL passes the CHECK automatically under standard SQL NULL-comparison semantics — individual accounts with `company_id IS NULL` and `role IS NULL` are unaffected.)

- [ ] **Step 3: Run the migration**

Run: `cd backend && source venv/bin/activate && alembic upgrade head`
Expected: no errors, migration applies cleanly against the existing data (no existing row violates the new constraint since it only adds `'co_founder'` as a new allowed value).

- [ ] **Step 4: Widen the Pydantic type**

In `backend/app/schemas/user.py:8`:

```python
CompanyRole = Literal["owner", "co_founder", "employee"]
```

- [ ] **Step 5: Verify the constraint is live**

Run: `cd backend && source venv/bin/activate && python -c "
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    db.execute(text(\"SELECT 1\"))
    try:
        db.execute(text(\"UPDATE users SET role = 'bogus_role' WHERE 1=0\"))
        db.execute(text(\"INSERT INTO users (email, hashed_password, role) VALUES ('constraint-test@example.com', 'x', 'bogus_role')\"))
        print('FAIL: constraint did not block bogus role')
    except Exception as e:
        print('OK: constraint blocked bogus role:', type(e).__name__)
    db.rollback()
finally:
    db.close()
"`
Expected: prints `OK: constraint blocked bogus role: IntegrityError`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/*add_co_founder_role_check_constraint.py backend/app/schemas/user.py
git commit -m "Add co_founder as a valid users.role value"
```

---

### Task 2: Backend — `require_company_admin` dependency + `get_owned_employee` fixes

**Files:**
- Modify: `backend/app/dependencies.py:76-150`

**Interfaces:**
- Consumes: `require_company_member` (existing, `dependencies.py:63`).
- Produces: `require_company_admin(current_user: User = Depends(require_company_member)) -> User` — new dependency, raises 403 unless `current_user.role in ("owner", "co_founder")`. Task 3+ routers import and use this by name.

- [ ] **Step 1: Add `require_company_admin` right after `require_company_owner`**

In `backend/app/dependencies.py`, after the existing `require_company_owner` function (ends at line 84):

```python
def require_company_admin(current_user: User = Depends(require_company_member)) -> User:
    """Gate for endpoints owner AND co-founder may use — everything that used
    to be owner-only except role assignment and deactivating a co-founder's
    account (those two stay on require_company_owner, strictly)."""
    if current_user.role not in ("owner", "co_founder"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available to the company owner or a co-founder",
        )

    return current_user
```

- [ ] **Step 2: Fix `get_owned_employee` — actor gate, target filter, self-exclusion**

Replace the existing `get_owned_employee` (currently `dependencies.py:133-150`):

```python
def get_owned_employee(
    employee_id: int,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> User:
    employee = (
        database_session.query(User)
        .filter(
            User.id == employee_id,
            User.company_id == current_user.company_id,
            User.role.in_(("employee", "co_founder")),
            User.id != current_user.id,
        )
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    return employee
```

Three changes from the original: (1) actor gate relaxed from `require_company_owner` to `require_company_admin`; (2) target filter expanded from `role == "employee"` to `role.in_(("employee", "co_founder"))` so a co-founder's own card is reachable by id; (3) added `User.id != current_user.id` — with co_founder now both a valid actor role and a valid target role, a co-founder could otherwise fetch/edit their own record through this endpoint (previously structurally impossible, since owner's own role was never `"employee"`).

- [ ] **Step 3: Verify the module still imports cleanly**

Run: `cd backend && source venv/bin/activate && python -c "import app.dependencies"`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "Add require_company_admin dependency, fix get_owned_employee for co_founder"
```

---

### Task 3: Backend — swap mechanical owner-only gates to owner-or-co-founder

**Files:**
- Modify: `backend/app/routers/positions.py:5,40,55,70`
- Modify: `backend/app/routers/currency.py:5,45`
- Modify: `backend/app/routers/sales_plans.py:7,35,140`
- Modify: `backend/app/routers/employees.py:8,46,87,103,225` (invites x3 + the explicit `current_user` param on `update_employee`, NOT the `employee` param — that comes from `get_owned_employee`, already fixed in Task 2)

**Interfaces:**
- Consumes: `require_company_admin` from Task 2 (`app.dependencies.require_company_admin`).

- [ ] **Step 1: `positions.py`**

Line 5, change the import:
```python
from app.dependencies import require_company_admin, require_company_member
```
Lines 40, 55, 70 (the `current_user: User = Depends(require_company_owner)` in `create_position`, `update_position`, `delete_position`) — replace `require_company_owner` with `require_company_admin` in all three.

- [ ] **Step 2: `currency.py`**

Line 5:
```python
from app.dependencies import require_company_admin, require_company_member
```
Line 45 (`update_currency_settings`'s `current_user` param) — replace `require_company_owner` with `require_company_admin`.

- [ ] **Step 3: `sales_plans.py`**

Line 7:
```python
from app.dependencies import require_company_admin, require_company_member
```
Lines 35 (`upsert_sales_plan`) and 140 (`delete_sales_plan`) — replace `require_company_owner` with `require_company_admin`.

- [ ] **Step 4: `employees.py`**

Line 8:
```python
from app.dependencies import get_owned_employee, require_company_admin, require_company_member
```
Lines 46 (`create_employee_invite`), 87 (`list_employee_invites`), 103 (`revoke_employee_invite`) — replace `require_company_owner` with `require_company_admin`.

Line 225, the `update_employee` function signature's explicit `current_user` param:
```python
@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_update: EmployeeUpdate,
    employee: User = Depends(get_owned_employee),
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> User:
```
(Only the `require_company_admin` on this line changes; `get_owned_employee` was already fixed in Task 2 and needs no further edit here.)

- [ ] **Step 5: Verify no leftover `require_company_owner` imports break anything**

Run: `cd backend && source venv/bin/activate && python -c "
import app.routers.positions, app.routers.currency, app.routers.sales_plans, app.routers.employees
print('OK')
"`
Expected: prints `OK`, no `ImportError`/`NameError`.

- [ ] **Step 6: Start the server and spot-check one relaxed endpoint**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload &` (background), then once it's up, confirm `require_company_owner` is still used only where intended:
Run: `grep -rn "require_company_owner" backend/app/routers/`
Expected output: only `employees.py` line ~225's route decorator context should show **no** hits for `require_company_owner` (it now uses `require_company_admin`) — the grep should return **zero** matches in `routers/`, since the only remaining strictly-owner-only endpoint (the role-assignment endpoint) doesn't exist yet (Task 5 adds it). Stop the background server after checking (`kill %1` or the job id printed).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/positions.py backend/app/routers/currency.py backend/app/routers/sales_plans.py backend/app/routers/employees.py
git commit -m "Relax owner-only gates to owner-or-co-founder across positions, currency, sales plans, employee management"
```

---

### Task 4: Backend — employee roster includes co-founders + co-founder deactivation guard

**Files:**
- Modify: `backend/app/routers/employees.py` (`list_employees`, currently lines 127-143; `update_employee`, currently lines 221-235)

**Interfaces:**
- Consumes: nothing new.
- Produces: `GET /employees` now returns both `role="employee"` and `role="co_founder"` rows. `PATCH /employees/{id}` now 403s if a non-owner tries to change `is_active` on a co-founder target.

- [ ] **Step 1: Widen `list_employees`' roster filter**

Current code:
```python
    employees_query = database_session.query(User).filter(
        User.company_id == current_user.company_id, User.role == "employee"
    )
```
Replace with:
```python
    employees_query = database_session.query(User).filter(
        User.company_id == current_user.company_id,
        User.role.in_(("employee", "co_founder")),
    )
```

- [ ] **Step 2: Add the co-founder-deactivation guard to `update_employee`**

Current body starts:
```python
def update_employee(
    employee_update: EmployeeUpdate,
    employee: User = Depends(get_owned_employee),
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> User:
    update_data = employee_update.model_dump(exclude_unset=True)

    if update_data.get("position_id") is not None:
```
Insert the guard right after `update_data = employee_update.model_dump(exclude_unset=True)`:
```python
    update_data = employee_update.model_dump(exclude_unset=True)

    if "is_active" in update_data and employee.role == "co_founder" and current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the company owner can deactivate or reactivate a co-founder's account",
        )

    if update_data.get("position_id") is not None:
```

- [ ] **Step 3: Verify module still imports**

Run: `cd backend && source venv/bin/activate && python -c "import app.routers.employees; print('OK')"`
Expected: `OK`.

- [ ] **Step 4: Manual verification via curl**

Requires two test accounts already existing in the same company: one `owner`, one promoted to `co_founder` (this can only be done for real after Task 5 ships the promotion endpoint — for now, manually set one test user's role via SQL to unblock this check):
```bash
cd backend && source venv/bin/activate && python -c "
from app.database import SessionLocal
from app.models.user import User
db = SessionLocal()
u = db.query(User).filter(User.role == 'employee').first()
assert u is not None, 'seed at least one employee first'
u.role = 'co_founder'
db.commit()
print('promoted', u.email, 'to co_founder for testing')
"
```
Then, logged in as that co_founder (obtain a token via `POST /auth/login`), attempt `PATCH /employees/{another_employee_id}` with `{"is_active": false}` — expect `200` (co-founder CAN deactivate a plain employee). Then attempt `PATCH /employees/{owner_id}`... this will 404 (self-exclusion / owner never matches target filter) — instead attempt deactivating a SECOND co_founder if one exists, or verify by reading the code path: the guard triggers only when `employee.role == "co_founder"`, so this manual check is: promote a second employee to co_founder via the same SQL snippet, then as the first co_founder, `PATCH /employees/{second_co_founder_id}` with `{"is_active": false}` — expect `403`. As the real `owner`, the same request should return `200`.

- [ ] **Step 5: Revert the manual SQL test promotions**

```bash
cd backend && source venv/bin/activate && python -c "
from app.database import SessionLocal
from app.models.user import User
db = SessionLocal()
for u in db.query(User).filter(User.role == 'co_founder').all():
    u.role = 'employee'
    print('reverted', u.email, 'back to employee')
db.commit()
"
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/employees.py
git commit -m "Include co-founders in employee roster, guard co-founder deactivation to owner-only"
```

---

### Task 5: Backend — `PATCH /employees/{id}/role` endpoint

**Files:**
- Modify: `backend/app/schemas/employee.py` (add `EmployeeRoleUpdate`)
- Modify: `backend/app/routers/employees.py` (add the new route)

**Interfaces:**
- Consumes: `require_company_owner` (existing, unchanged), `EmployeeOut` (existing response schema).
- Produces: `EmployeeRoleUpdate(BaseModel)` with field `role: Literal["co_founder", "employee"]`. `PATCH /employees/{employee_id}/role` route.

- [ ] **Step 1: Add the request schema**

In `backend/app/schemas/employee.py`, add the `Literal` import and the new class. Current top of file:
```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
```
Change to:
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
```
Then add, right after the existing `EmployeeUpdate` class:
```python
class EmployeeRoleUpdate(BaseModel):
    role: Literal["co_founder", "employee"]
```

- [ ] **Step 2: Add the route**

In `backend/app/routers/employees.py`, this file's `require_company_owner` import was removed in Task 3 Step 4 (every usage in this file was swapped to `require_company_admin` at that point) — this task reintroduces a usage, so re-add it to the import line:
```python
from app.dependencies import get_owned_employee, require_company_admin, require_company_member, require_company_owner
```
Also import the new schema (extend the existing schema import line):
```python
from app.schemas.employee import EmployeeCurrentMonthPlan, EmployeeOut, EmployeeRoleUpdate, EmployeeStatsOut, EmployeeUpdate
```
Add the route after `update_employee` (end of file):
```python
@router.patch("/{employee_id}/role", response_model=EmployeeOut)
def update_employee_role(
    employee_id: int,
    role_update: EmployeeRoleUpdate,
    current_user: User = Depends(require_company_owner),
    database_session: Session = Depends(get_db),
) -> User:
    if employee_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    employee = (
        database_session.query(User)
        .filter(
            User.id == employee_id,
            User.company_id == current_user.company_id,
            User.role.in_(("employee", "co_founder")),
        )
        .first()
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot change the role of a deactivated employee",
        )

    if role_update.role == "co_founder" and employee.role != "employee":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee is already a co-founder")
    if role_update.role == "employee" and employee.role != "co_founder":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee is not a co-founder")

    employee.role = role_update.role
    database_session.commit()
    database_session.refresh(employee)

    return employee
```

Note `require_company_owner` (not `require_company_admin`) — this is the strict exception. Also note the route must be registered where `GET/PATCH /{employee_id}` already are (after the `/invites` routes, per the existing comment in the file about FastAPI route-matching order) — appending at the end of the file is fine since `/invites` is already earlier in the file.

- [ ] **Step 3: Verify module imports and route registers**

Run: `cd backend && source venv/bin/activate && python -c "
from app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
assert '/employees/{employee_id}/role' in routes, routes
print('OK: route registered')
"`
Expected: `OK: route registered`.

- [ ] **Step 4: Manual verification via curl**

Start the server (`uvicorn app.main:app --reload`), log in as the real `owner`, and:
1. `PATCH /employees/{employee_id}/role` with `{"role": "co_founder"}` on an active employee → expect `200`, response `role` is `"co_founder"`.
2. Repeat the same call again → expect `409` ("already a co-founder").
3. `PATCH /employees/{same_id}/role` with `{"role": "employee"}` → expect `200`, back to `"employee"`.
4. `PATCH /employees/{owner_id}/role` (targeting the owner's own id) → expect `400` ("cannot change your own role").
5. Log in as a `co_founder` (promote one first via step 1) and attempt any `PATCH /employees/{id}/role` call → expect `403` (strictly owner-only, `require_company_admin` does NOT apply here).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/employee.py backend/app/routers/employees.py
git commit -m "Add PATCH /employees/{id}/role endpoint, strictly owner-only"
```

---

### Task 6: Frontend — widen `CompanyRole` type + role-update input type

**Files:**
- Modify: `frontend/app/types/user.ts:2`
- Modify: `frontend/app/types/employees.ts`

**Interfaces:**
- Produces: `CompanyRole = 'owner' | 'co_founder' | 'employee'`. `EmployeeRoleUpdateInput { role: 'co_founder' | 'employee' }`.

- [ ] **Step 1: Widen `CompanyRole`**

`frontend/app/types/user.ts:2`:
```ts
export type CompanyRole = 'owner' | 'co_founder' | 'employee'
```

- [ ] **Step 2: Add the role-update input type**

In `frontend/app/types/employees.ts`, add after the existing `EmployeeUpdateInput` interface:
```ts
export interface EmployeeRoleUpdateInput {
    role: 'co_founder' | 'employee'
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no new errors introduced by this change (pre-existing errors, if any, are not this task's concern — but there should be none related to `CompanyRole`/`EmployeeRoleUpdateInput`).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/types/user.ts frontend/app/types/employees.ts
git commit -m "Widen CompanyRole type to include co_founder"
```

---

### Task 7: Frontend — `useUserRole()` composable

**Files:**
- Create: `frontend/app/composables/useUserRole.ts`

**Interfaces:**
- Produces: `useUserRole(): { isOwner: ComputedRef<boolean>, isCoFounder: ComputedRef<boolean>, isEmployee: ComputedRef<boolean>, isCompanyAdmin: ComputedRef<boolean> }`. Tasks 9-12 consume this by name.

- [ ] **Step 1: Write the composable**

```ts
export function useUserRole() {
  const authStore = useAuthStore()
  const role = computed(() => authStore.user?.role ?? null)

  return {
    isOwner: computed<boolean>(() => role.value === 'owner'),
    isCoFounder: computed<boolean>(() => role.value === 'co_founder'),
    isEmployee: computed<boolean>(() => role.value === 'employee'),
    // Owner-equivalent access — every previously owner-only surface EXCEPT
    // co-founder role assignment and co-founder account deactivation, which
    // stay on isOwner strictly.
    isCompanyAdmin: computed<boolean>(() => role.value === 'owner' || role.value === 'co_founder'),
  }
}
```

- [ ] **Step 2: Verify it compiles and auto-imports**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no errors (Nuxt auto-imports `composables/*.ts` — no manual import needed elsewhere).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/composables/useUserRole.ts
git commit -m "Add useUserRole composable"
```

---

### Task 8: Frontend — employees store: `updateEmployeeRole` action

**Files:**
- Modify: `frontend/app/stores/employees.ts`

**Interfaces:**
- Consumes: `EmployeeRoleUpdateInput` (Task 6), `apiPatch` (existing `useApi()`).
- Produces: `updateEmployeeRole(employeeId: number, role: 'co_founder' | 'employee'): Promise<Employee>` — Task 13 (UI) calls this.

- [ ] **Step 1: Add the import**

Change:
```ts
import type { Employee, EmployeeStats, EmployeeUpdateInput } from '~/types/employees'
```
to:
```ts
import type { Employee, EmployeeRoleUpdateInput, EmployeeStats, EmployeeUpdateInput } from '~/types/employees'
```

- [ ] **Step 2: Add the action**

Right after the existing `updateEmployee` action:
```ts
    const updateEmployeeRole = async (employeeId: number, role: EmployeeRoleUpdateInput['role']): Promise<Employee> => {
        isLoading.value = true
        error.value = null
        try {
            const updatedEmployee = await apiPatch<Employee>(`/employees/${employeeId}/role`, { role })
            employees.value = employees.value.map((employee) => employee.id === employeeId ? updatedEmployee : employee)
            return updatedEmployee
        } catch (e) {
            error.value = (e as ApiError).message
            throw e
        } finally {
            isLoading.value = false
        }
    }
```

- [ ] **Step 3: Export it**

In the `return { ... }` block, add `updateEmployeeRole` alongside `updateEmployee`.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/stores/employees.ts
git commit -m "Add updateEmployeeRole action to employee store"
```

---

### Task 9: Frontend — refactor all 16 role-check sites to `useUserRole()`

**Files:**
- Modify: `frontend/app/pages/crm/index.vue:10,41`
- Modify: `frontend/app/pages/settings.vue:26,31,493`
- Modify: `frontend/app/components/listings/ListingForm.vue:25,279`
- Modify: `frontend/app/components/employees/EmployeeDetailsReadOnly.vue:31,111`
- Modify: `frontend/app/components/employees/EmployeeDetailModal.vue:18,59`
- Modify: `frontend/app/pages/crm/analytics.vue:15,25,84,92`
- Modify: `frontend/app/pages/crm/inventory/[id].vue:115,144`
- Modify: `frontend/app/layouts/business.vue:24,56`
- Modify: `frontend/app/pages/crm/employees.vue:16,34,72,159,203`
- Modify: `frontend/app/pages/crm/sales-plans.vue:14,135`
- Modify: `frontend/app/pages/crm/deal-history.vue:18,67`
- Modify: `frontend/app/pages/garage/index.vue:16`
- Modify: `frontend/app/pages/crm/inventory/new.vue:18`
- Modify: `frontend/app/pages/crm/composer.vue:28,199,201`
- Modify: `frontend/app/components/clients/ClientKanbanBoard.vue:91`

**Interfaces:**
- Consumes: `useUserRole()` from Task 7.

This is a mechanical replacement, but the mapping is NOT uniform — some sites that were literally `role === 'owner'` become `isCompanyAdmin` (relaxed), while others must stay `isOwner` (the two explicit exceptions, plus one narrow case explained below). Follow this exact table:

| File | Old local var | New composable prop | Why |
|---|---|---|---|
| `crm/index.vue:10` | `isOwner` | `isCompanyAdmin` | Company-wide net profit card — relax |
| `settings.vue:26` | `isCompanyOwner` | `isCompanyAdmin` | Currency settings — relax |
| `ListingForm.vue:25` | `isCompanyOwner` | `isCompanyAdmin` | Employee-assignment field — relax (backend already auto-includes co_founder here) |
| `EmployeeDetailsReadOnly.vue:31` | `isCompanyOwner` | `isCompanyAdmin` | Stats section — relax |
| `EmployeeDetailModal.vue:18` | `canManageEmployees` | `isCompanyAdmin` | Edit/deactivate footer — relax (Task 12 adds an extra owner-only sub-check for deactivating a co-founder target) |
| `crm/analytics.vue:15` | `isEmployee` | `isEmployee` | Personal-vs-company scope — unchanged meaning, just relocate |
| `crm/inventory/[id].vue:115` | `isEmployee` | `isEmployee` | Listing-lock mirror — unchanged meaning |
| `crm/inventory/[id].vue:144` | inline `role === 'owner'` | `isCompanyAdmin` | Fetch employee list for assignment dropdown — relax |
| `layouts/business.vue:24` | `isCompanyOwner` | `isCompanyAdmin` | Sidebar nav filter (currently a no-op, all items have `ownerOnly: false`) — relax for consistency |
| `crm/employees.vue:16` | `isCompanyOwner` | **split** — see Step 9 below | Different meanings at different use sites in this one file |
| `crm/sales-plans.vue:14` | `isCompanyOwner` | `isCompanyAdmin` | Sales plan management — relax (explicitly named in the brief) |
| `crm/deal-history.vue:18` | `isEmployee` | `isEmployee` | Personal scope subtitle — unchanged meaning |
| `garage/index.vue:16` | inline `role === 'owner'` | `isOwner` | Business-profile-setup nudge is specific to the literal owner who registered the company — NOT in the brief's relax list, stays strict |
| `crm/inventory/new.vue:18` | inline `role === 'owner'` | `isCompanyAdmin` | Fetch employee list for assignment dropdown — relax |
| `crm/composer.vue:28` | `isCompanyOwner` | `isCompanyAdmin` | Telegram settings — relax (explicitly named in the brief) |
| `ClientKanbanBoard.vue:91` | inline `role === 'employee'` | `isEmployee` | Seller-lock mirror — unchanged meaning |

- [ ] **Step 1: `crm/index.vue`**

Replace line 10:
```ts
const { isCompanyAdmin } = useUserRole()
```
Remove the old `const isOwner = computed<boolean>(() => authStore.user?.role === 'owner')` line entirely. Line 41: change `v-if="isOwner"` to `v-if="isCompanyAdmin"`.

- [ ] **Step 2: `settings.vue`**

Replace line 26 (`const isCompanyOwner = computed(() => authStore.user?.role === 'owner')`) with:
```ts
const { isCompanyAdmin } = useUserRole()
```
Line 31: `if (isCompanyOwner.value) {` → `if (isCompanyAdmin.value) {`. Line 493: `v-if="isCompanyOwner"` → `v-if="isCompanyAdmin"`.

- [ ] **Step 3: `ListingForm.vue`**

Replace line 25 with `const { isCompanyAdmin } = useUserRole()`. Line 279: `v-if="isCompanyOwner"` → `v-if="isCompanyAdmin"`.

- [ ] **Step 4: `EmployeeDetailsReadOnly.vue`**

Replace line 31 with `const { isCompanyAdmin } = useUserRole()`. Line 111: `v-if="isCompanyOwner"` → `v-if="isCompanyAdmin"`.

- [ ] **Step 5: `EmployeeDetailModal.vue`**

Replace line 18 (`const canManageEmployees = computed<boolean>(() => authStore.user?.role === 'owner')`) with:
```ts
const { isCompanyAdmin } = useUserRole()
```
Line 59: `v-if="canManageEmployees"` → `v-if="isCompanyAdmin"`. (Task 12 handles the additional promote/demote controls and the co-founder-deactivation sub-check inside this same file — don't add them here, this task is only the mechanical rename.)

- [ ] **Step 6: `crm/analytics.vue`**

Replace line 15 (`const isEmployee = computed<boolean>(() => authStore.user?.role === 'employee')`) with:
```ts
const { isEmployee } = useUserRole()
```
Lines 25, 84, 92 reference `isEmployee` already — no further change needed there, it's the same identifier.

- [ ] **Step 7: `crm/inventory/[id].vue`**

Replace line 115 (`const isEmployee = computed<boolean>(() => authStore.user?.role === 'employee')`) with:
```ts
const { isEmployee, isCompanyAdmin } = useUserRole()
```
Line 122 references `isEmployee` unchanged. Line 144: `if (authStore.user?.role === 'owner') {` → `if (isCompanyAdmin.value) {`.

- [ ] **Step 8: `layouts/business.vue`**

Replace line 24 with `const { isCompanyAdmin } = useUserRole()`. Line 56: `isCompanyOwner.value` → `isCompanyAdmin.value`.

- [ ] **Step 9: `crm/employees.vue` — split usage**

Replace line 16 (`const isCompanyOwner = computed<boolean>(() => authStore.user?.role === 'owner')`) with:
```ts
const { isOwner, isCompanyAdmin } = useUserRole()
```
- Line 34 (`if (isCompanyOwner.value) {` guarding the invites fetch): → `if (isCompanyAdmin.value) {`
- Line 72 (inside `visibleEmployees`, `isCompanyOwner.value ? employeeStore.employees : employeeStore.employees.filter(...)`): → `isOwner.value ? employeeStore.employees : employeeStore.employees.filter(...)`. **This one must stay `isOwner`, not `isCompanyAdmin`** — the roster (`GET /employees`) now includes co-founders (Task 4), so a co-founder viewing this page WILL find their own id in `employeeStore.employees`; only `isOwner` correctly triggers the self-exclusion filter for them. Using `isCompanyAdmin` here would make a co-founder see their own card in their own roster view.
- Line 159 (`v-if="isCompanyOwner"` on the manage-positions/invite buttons): → `v-if="isCompanyAdmin"`
- Line 203 (`v-if="isCompanyOwner"` on the invites section): → `v-if="isCompanyAdmin"`

- [ ] **Step 10: `crm/sales-plans.vue`**

Replace line 14 with `const { isCompanyAdmin } = useUserRole()`. Line 135: `v-if="isCompanyOwner"` → `v-if="isCompanyAdmin"`.

- [ ] **Step 11: `crm/deal-history.vue`**

Replace line 18 with `const { isEmployee } = useUserRole()`. Line 67 references `isEmployee` unchanged.

- [ ] **Step 12: `garage/index.vue`**

Line 16, replace:
```ts
const showBusinessProfileBanner = computed<boolean>(() =>
  authStore.user?.role === 'owner' && !authStore.user?.company?.name
)
```
with:
```ts
const { isOwner } = useUserRole()
const showBusinessProfileBanner = computed<boolean>(() =>
  isOwner.value && !authStore.user?.company?.name
)
```

- [ ] **Step 13: `crm/inventory/new.vue`**

Line 18, replace:
```ts
if (authStore.user?.role === 'owner') {
  await employeeStore.fetchEmployees()
}
```
with:
```ts
const { isCompanyAdmin } = useUserRole()
if (isCompanyAdmin.value) {
  await employeeStore.fetchEmployees()
}
```

- [ ] **Step 14: `crm/composer.vue`**

Replace line 28 with `const { isCompanyAdmin } = useUserRole()`. Lines 199, 201: `isCompanyOwner` → `isCompanyAdmin`.

- [ ] **Step 15: `ClientKanbanBoard.vue`**

Line 91, replace the inline `authStore.user?.role === 'employee'` with a composable-backed check: add `const { isEmployee } = useUserRole()` near the top of the `<script setup>` block, then replace the inline expression at line 91 with `isEmployee.value`.

- [ ] **Step 16: Verify TypeScript compiles and remove now-unused `authStore` imports where applicable**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no errors. If any file no longer uses `authStore` for anything else (check each file — several still use it for other fields like `authStore.user?.id`, `authStore.user?.company?.name`, so don't blindly remove the `useAuthStore()` call), remove the now-unused `useAuthStore()` call — but only where genuinely unused elsewhere in that file.

- [ ] **Step 17: Commit**

```bash
git add frontend/app/pages/crm/index.vue frontend/app/pages/settings.vue frontend/app/components/listings/ListingForm.vue frontend/app/components/employees/EmployeeDetailsReadOnly.vue frontend/app/components/employees/EmployeeDetailModal.vue frontend/app/pages/crm/analytics.vue "frontend/app/pages/crm/inventory/[id].vue" frontend/app/layouts/business.vue frontend/app/pages/crm/employees.vue frontend/app/pages/crm/sales-plans.vue frontend/app/pages/crm/deal-history.vue frontend/app/pages/garage/index.vue frontend/app/pages/crm/inventory/new.vue frontend/app/pages/crm/composer.vue frontend/app/components/clients/ClientKanbanBoard.vue
git commit -m "Refactor role checks to useUserRole composable across the app"
```

---

### Task 10: Frontend — co-founder badge on `EmployeeCard.vue`

**Files:**
- Modify: `frontend/app/components/employees/EmployeeCard.vue`

**Interfaces:**
- Consumes: `Employee.role` (already exists, typed `CompanyRole | null` from Task 6).

- [ ] **Step 1: Add the badge**

In the template, right after the existing inactive-status `<span>` block (currently ending around line 45), add a co-founder badge, and keep the existing position line separate below it:

```vue
      <span
        v-if="employee.role === 'co_founder'"
        class="shrink-0 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
      >
        {{ t('crm.employees.coFounderBadge') }}
      </span>
```
Place it inside the same flex row as the inactive-status span (the `<div class="flex items-start justify-between gap-2">` block), so both badges can coexist if a co-founder happens to also be inactive.

- [ ] **Step 2: Verify the i18n key resolves**

This key doesn't exist yet — Task 13 adds it. For now this step is a placeholder marker for Task 13's dependency; skip runtime verification until Task 13 lands, but confirm the template change itself doesn't break compilation:
Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no errors (missing i18n keys are a runtime warning in `@nuxtjs/i18n`, not a TypeScript error).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/employees/EmployeeCard.vue
git commit -m "Add co-founder badge to EmployeeCard"
```

---

### Task 11: Frontend — promote/demote co-founder UI (owner-only)

**Files:**
- Modify: `frontend/app/components/employees/EmployeeDetailModal.vue`

**Interfaces:**
- Consumes: `useUserRole()` (Task 7, already imported in this file per Task 9 Step 5), `employeeStore.updateEmployeeRole` (Task 8), `ConfirmDialog` (existing component, props `title`/`message`/`confirmLabel`, events `confirm`/`cancel`).

- [ ] **Step 1: Add `isOwner` alongside the existing `isCompanyAdmin`**

This file already has `const { isCompanyAdmin } = useUserRole()` from Task 9 Step 5. Change it to:
```ts
const { isOwner, isCompanyAdmin } = useUserRole()
```

- [ ] **Step 2: Add state for the promote/demote confirm dialogs**

Near the existing `const isDeactivateConfirmOpen = ref(false)`:
```ts
const isPromoteConfirmOpen = ref(false)
const isDemoteConfirmOpen = ref(false)
```

- [ ] **Step 3: Add a computed to gate the deactivate/reactivate button for co-founder targets**

Right after the `canManageEmployees`-turned-`isCompanyAdmin` area, add:
```ts
// Deactivating/reactivating a co-founder's account is strictly owner-only —
// a co-founder can manage a plain employee's account but not another
// co-founder's, mirroring the backend guard in update_employee.
const canToggleThisEmployeeActive = computed<boolean>(() =>
  isOwner.value || props.employee.role !== 'co_founder'
)
```

- [ ] **Step 4: Add the promote/demote handlers**

Alongside the existing `handleDeactivateConfirm`/`handleReactivate`:
```ts
async function handlePromoteConfirm(): Promise<void> {
  await employeeStore.updateEmployeeRole(props.employee.id, 'co_founder')
  isPromoteConfirmOpen.value = false
}

async function handleDemoteConfirm(): Promise<void> {
  await employeeStore.updateEmployeeRole(props.employee.id, 'employee')
  isDemoteConfirmOpen.value = false
}
```

- [ ] **Step 5: Wire the deactivate/reactivate buttons to the new gate**

The existing footer buttons for deactivate (`v-if="!isEditMode && employee.is_active"`) and reactivate (`v-else-if="!isEditMode"`) both need `canToggleThisEmployeeActive` added to their condition:
```vue
        <button
          v-if="!isEditMode && employee.is_active && canToggleThisEmployeeActive"
          ...
          @click="isDeactivateConfirmOpen = true"
        >
          {{ t('crm.employees.deactivateButton') }}
        </button>
        <button
          v-else-if="!isEditMode && canToggleThisEmployeeActive"
          ...
          @click="handleReactivate"
        >
          {{ t('crm.employees.reactivateButton') }}
        </button>
```

- [ ] **Step 6: Add the promote/demote buttons, owner-only, inside the existing `isCompanyAdmin` footer**

Right after the deactivate/reactivate buttons (still inside the `<div v-if="isCompanyAdmin" ...>` footer), add a second row visible only to `isOwner`:
```vue
      <div v-if="isOwner && !isEditMode" class="mt-2 flex justify-end">
        <button
          v-if="employee.role === 'employee'"
          type="button"
          class="rounded-md border border-primary/30 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/10"
          @click="isPromoteConfirmOpen = true"
        >
          {{ t('crm.employees.promoteToCoFounderButton') }}
        </button>
        <button
          v-else-if="employee.role === 'co_founder'"
          type="button"
          class="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
          @click="isDemoteConfirmOpen = true"
        >
          {{ t('crm.employees.demoteCoFounderButton') }}
        </button>
      </div>
```

- [ ] **Step 7: Add the two confirm dialogs**

Right after the existing `<ConfirmDialog v-if="isDeactivateConfirmOpen" ...>` block, before `</BaseModal>`:
```vue
    <ConfirmDialog
      v-if="isPromoteConfirmOpen"
      :title="t('crm.employees.promoteConfirmTitle')"
      :message="t('crm.employees.promoteConfirmMessage')"
      :confirm-label="t('crm.employees.promoteToCoFounderButton')"
      @confirm="handlePromoteConfirm"
      @cancel="isPromoteConfirmOpen = false"
    />
    <ConfirmDialog
      v-if="isDemoteConfirmOpen"
      :title="t('crm.employees.demoteConfirmTitle')"
      :message="t('crm.employees.demoteConfirmMessage')"
      :confirm-label="t('crm.employees.demoteCoFounderButton')"
      @confirm="handleDemoteConfirm"
      @cancel="isDemoteConfirmOpen = false"
    />
```

- [ ] **Step 8: Verify TypeScript compiles**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: no errors (the i18n keys referenced here don't exist yet — Task 13 adds them; this is a runtime concern, not a type error).

- [ ] **Step 9: Commit**

```bash
git add frontend/app/components/employees/EmployeeDetailModal.vue
git commit -m "Add owner-only promote/demote co-founder controls to employee detail modal"
```

---

### Task 12: i18n — uk/ru keys

**Files:**
- Modify: `frontend/locales/uk.json` (inside existing `crm.employees` object)
- Modify: `frontend/locales/ru.json` (inside existing `crm.employees` object)

**Interfaces:**
- Consumes: nothing.
- Produces: the six keys referenced in Tasks 10 and 11 (`coFounderBadge`, `promoteToCoFounderButton`, `demoteCoFounderButton`, `promoteConfirmTitle`, `promoteConfirmMessage`, `demoteConfirmTitle`, `demoteConfirmMessage` — seven total).

- [ ] **Step 1: Add keys to `uk.json`**

Inside the existing `crm.employees` object, right after `"deactivateConfirmMessage"` and before `"reactivateButton"`, insert:
```json
    "coFounderBadge": "Співзасновник",
    "promoteToCoFounderButton": "Призначити співзасновником",
    "promoteConfirmTitle": "Призначити співзасновником?",
    "promoteConfirmMessage": "Співробітник отримає всі права власника компанії, окрім можливості призначати інших співзасновників.",
    "demoteCoFounderButton": "Зняти роль співзасновника",
    "demoteConfirmTitle": "Зняти роль співзасновника?",
    "demoteConfirmMessage": "Користувач втратить права співзасновника і стане звичайним співробітником.",
```

- [ ] **Step 2: Add matching keys to `ru.json`**

At the same position inside `crm.employees` in `ru.json`:
```json
    "coFounderBadge": "Совладелец",
    "promoteToCoFounderButton": "Назначить совладельцем",
    "promoteConfirmTitle": "Назначить совладельцем?",
    "promoteConfirmMessage": "Сотрудник получит все права владельца компании, кроме возможности назначать других совладельцев.",
    "demoteCoFounderButton": "Снять роль совладельца",
    "demoteConfirmTitle": "Снять роль совладельца?",
    "demoteConfirmMessage": "Пользователь потеряет права совладельца и станет обычным сотрудником.",
```

- [ ] **Step 3: Verify both files are valid JSON**

Run: `cd frontend && node -e "JSON.parse(require('fs').readFileSync('locales/uk.json')); JSON.parse(require('fs').readFileSync('locales/ru.json')); console.log('OK: both valid JSON')"`
Expected: `OK: both valid JSON`.

- [ ] **Step 4: Commit**

```bash
git add frontend/locales/uk.json frontend/locales/ru.json
git commit -m "Add co-founder i18n keys (uk/ru) to crm.employees"
```

---

### Task 13: `check:i18n` script

**Files:**
- Create: `frontend/scripts/check-i18n.mjs`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `npm run check:i18n` — exits 1 and prints the diff if `uk.json`/`ru.json` key sets don't match, exits 0 otherwise.

- [ ] **Step 1: Write the script**

```js
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const currentDirectory = dirname(fileURLToPath(import.meta.url))
const localesDirectory = join(currentDirectory, '..', 'locales')

function collectKeyPaths(value, prefix = '') {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return [prefix]
  }
  return Object.entries(value).flatMap(([key, nestedValue]) =>
    collectKeyPaths(nestedValue, prefix ? `${prefix}.${key}` : key)
  )
}

const localeFiles = ['uk.json', 'ru.json']
const keyPathsByLocale = localeFiles.map((fileName) => ({
  fileName,
  keyPaths: new Set(collectKeyPaths(JSON.parse(readFileSync(join(localesDirectory, fileName), 'utf-8')))),
}))

const [first, second] = keyPathsByLocale
const onlyInFirst = [...first.keyPaths].filter((keyPath) => !second.keyPaths.has(keyPath))
const onlyInSecond = [...second.keyPaths].filter((keyPath) => !first.keyPaths.has(keyPath))

if (onlyInFirst.length === 0 && onlyInSecond.length === 0) {
  console.log(`OK: ${first.fileName} and ${second.fileName} have matching key sets (${first.keyPaths.size} keys)`)
  process.exit(0)
}

if (onlyInFirst.length > 0) {
  console.error(`Keys only in ${first.fileName}:`)
  onlyInFirst.forEach((keyPath) => console.error(`  - ${keyPath}`))
}
if (onlyInSecond.length > 0) {
  console.error(`Keys only in ${second.fileName}:`)
  onlyInSecond.forEach((keyPath) => console.error(`  - ${keyPath}`))
}
process.exit(1)
```

- [ ] **Step 2: Wire it into `package.json`**

In `frontend/package.json`, add to `"scripts"`:
```json
    "check:i18n": "node scripts/check-i18n.mjs",
```

- [ ] **Step 3: Run it**

Run: `cd frontend && npm run check:i18n`
Expected: `OK: uk.json and ru.json have matching key sets (<N> keys)`. If it fails, the output lists exactly which keys are missing from which file — fix `uk.json`/`ru.json` from Task 12 until it passes.

- [ ] **Step 4: Commit**

```bash
git add frontend/scripts/check-i18n.mjs frontend/package.json
git commit -m "Add check:i18n script for uk/ru locale key parity"
```

---

### Task 14: Full manual verification pass

**Files:** none (verification only).

- [ ] **Step 1: Backend up**

Run: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload` (background/separate terminal).

- [ ] **Step 2: Frontend up**

Use the `run` skill to launch the Nuxt dev server and drive it in a real browser (per this project's convention for verifying frontend changes before calling them done).

- [ ] **Step 3: Owner flow**

Log in as the real company owner. On `/crm/employees`: confirm an active employee's card shows a "Призначити співзасновником" action inside its detail modal; click it, confirm the dialog, verify the card now shows the "Співзасновник" badge and the modal's action flips to "Зняти роль співзасновника". Verify the owner still sees Telegram settings (`/crm/composer`), Sales Plans, full Analytics, Currency settings, Positions management — all unaffected by the refactor.

- [ ] **Step 4: Co-founder flow**

Log in as the newly-promoted co-founder. Verify: Telegram settings, Sales Plans, full company-wide Analytics, Currency settings, Positions management, and the Employees roster (including invites section) are all visible/usable exactly as they were for the owner. Verify the co-founder does NOT see any promote/demote-role control anywhere (including on their own — nonexistent, since they're excluded from their own roster view — and on other employees' cards). Verify the co-founder CAN deactivate a plain employee's account, but attempting to deactivate a second co-founder's account (promote a second test employee first) is either hidden in the UI or returns a clear error.

- [ ] **Step 5: Employee flow**

Log in as a regular employee. Verify nothing changed: personal-scope Analytics/Deal History, no access to Sales Plans management, Telegram settings, Currency settings, Positions management, or the invites section. Verify the roster now also lists the co-founder (with badge) alongside other employees.

- [ ] **Step 6: Positions settings unaffected**

On `/crm/employees`, open "Керувати посадами" (Positions modal) as owner: confirm "Співзасновник" is not listed and cannot be added — expected by construction, since `Position` is a fully separate model/table with no relation to `role` (nothing in this plan touches `positions.py`'s data model or `PositionsManageModal.vue`), but worth a quick visual confirmation.

- [ ] **Step 7: `check:i18n` final run**

Run: `cd frontend && npm run check:i18n`
Expected: `OK`.

- [ ] **Step 8: Revert any test-only role promotions left over from manual backend verification (Task 4/5)**

If any test accounts are still `co_founder` from earlier manual checks and shouldn't be, demote them back via the UI (owner → "Зняти роль співзасновника") or the SQL snippet from Task 4 Step 5.

No commit for this task — it's verification only. Report completion to the user once all six checks pass.
