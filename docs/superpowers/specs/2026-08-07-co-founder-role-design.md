# Роль "Співзасновник" (co_founder) для Car Garage Tracker

**Дата:** 2026-08-07
**Статус:** Approved

## Мета

Додати третю системну роль користувача — `co_founder` ("Співзасновник") — з правами,
ідентичними `owner`, окрім ОДНОГО строгого винятку: призначати/знімати роль
"Співзасновник" і деактивувати акаунт співзасновника може ВИКЛЮЧНО реальний `owner`.
Це роль, а не запис у таблиці `Position` — повністю відокремлена від системи кастомних
посад, яку власник створює для employee.

## Scope

In scope:
- `users.role`: третє допустиме значення `"co_founder"` (поточна колонка — вже вільний
  `String(20)`, не enum/boolean — тому не потрібна складна data-міграція існуючих рядків,
  лише розширення допустимих значень + CHECK-обмеження)
- Новий бекенд-dependency `require_company_admin` (owner АБО co_founder) поряд з
  існуючим строго-owner `require_company_owner`
- Новий ендпоінт `PATCH /employees/{id}/role` (строго owner-only) — призначення/зняття
  co_founder
- Виправлення двох меж у `get_owned_employee`/`list_employees`, які сьогодні бачать лише
  `role == "employee"` (потрібне розширення, щоб співзасновники з'являлись у списку
  співробітників і були доступні для керування)
- Фронтенд: composable `useUserRole()`, що замінює 16 локальних копій
  `isOwner`/`isCompanyOwner`/`isEmployee`/`canManageEmployees` у 14 файлах
- Бейдж співзасновника + кнопка призначення/зняття ролі на картці employee
  (owner-only), i18n (uk/ru) всередині `crm.employees`
- Мінімальний `scripts/check-i18n.mjs` + `npm run check:i18n` (в проєкті ще не існує)

Out of scope (свідомо не робиться зараз):
- Запрошення нового користувача одразу як co_founder — запрошення завжди створюють
  `role="employee"` (`POST /auth/register` з `invite_token`); співзасновником можна
  стати лише через підвищення вже існуючого employee
- Розширення пулу "відповідальних співробітників" для лотів/клієнтів
  (`_get_owned_active_employee_or_error` у `listings.py`/`clients.py`) на co_founder —
  ці helper-и лишаються фільтром `role == "employee"`, бо задача не просить робити
  співзасновників призначуваними продавцями
- Автоматизовані frontend-тести (в проєкті немає існуючої тестової конвенції для
  frontend); backend отримує pytest-покриття нових/змінених owner-меж

## Дані, з'ясовані під час дослідження кодбази

- `backend/app/models/user.py`: `role: Mapped[str | None] = mapped_column(String(20))`.
  Немає `is_owner` boolean, немає SQLAlchemy/Postgres Enum — вільний рядок. БД — Postgres
  (підтверджено через `server_default=sa.text('now()')` в існуючих міграціях).
- Єдина owner-only межа сьогодні — `require_company_owner` (`backend/app/dependencies.py`),
  використовується у 14 місцях: `positions.py` (create/rename/delete), `currency.py`
  (update), `employees.py` (invites create/list/revoke, `update_employee`, і опосередковано
  через `get_owned_employee` — read/stats), `sales_plans.py` (upsert/delete).
- `get_owned_employee` (`dependencies.py:133`) фільтрує ціль на `role == "employee"` —
  сьогодні неможливо звернутись до owner-рядка (`role` ніколи не `"employee"`), тож
  self-match не траплявся. Після розширення фільтра до `("employee", "co_founder")`
  self-match стає можливим для актора-co_founder, який звертається до власного `id` —
  потрібен явний виняток.
- ~10 інлайн-перевірок `current_user.role == "employee"` (НЕ через dependency) у
  `listing_authorization.py`, `sales_plans.py` (self-scoping + company-total-рядок),
  `deal_history.py`, `listings.py` (self-assignment), `clients.py`/`listings.py`
  (`_get_owned_active_employee_or_error`). Усі вони трактують `"employee"` як обмежувальну
  гілку, а "все інше" — як owner-рівень доступу. Оскільки `"co_founder" != "employee"`,
  co_founder автоматично потрапляє у необмежену гілку без жодних змін коду в цих файлах.
  Виняток: `auth.py:208` (`role == "owner" and not is_email_confirmed`) — це про
  реєстрацію самого owner, коректно лишається owner-literal (co_founder не проходить
  окрему реєстрацію/підтвердження email).
- JWT несе лише `sub`(email)+`exp` — жодної ролі. `role` завжди читається свіжо з БД у
  `get_current_user`, тож зміна ролі діє одразу на наступному запиті, без переавторизації.
- Фронтенд: жодного спільного composable — `authStore.user?.role === 'owner'` (чи
  `!== 'employee'`) копіюється локально у 14 файлах під різними іменами (`isOwner`,
  `isCompanyOwner`, `isEmployee`, `canManageEmployees`) — 16 визначень.
- Позиції (`Налаштування посад`) — окрема модель `Position`/таблиця `positions`, немає
  окремої сторінки `/settings/positions`, керування відбувається через модалку
  `PositionsManageModal.vue`, відкриту з `crm/employees.vue`. Немає жодного перетину з
  роллю — нічого змінювати, щоб "Співзасновник" туди не потрапив.
- `npm run check:i18n` не існує в `frontend/package.json` (лише
  build/dev/generate/preview/postinstall) — буде додано новим.
- i18n: `frontend/locales/{uk,ru}.json`, секція `crm.employees` вже містить
  `deactivateButton`/`deactivateConfirmTitle`/`deactivateConfirmMessage` —
  прямий взірець стилю для нових ключів підтвердження призначення/зняття ролі.

## Рішення, узгоджені з користувачем

1. `users.role` лишається `String(20)` (не Postgres ENUM-тип — уникає болючого
   `ALTER TYPE ADD VALUE` для майбутніх ролей), але отримує
   `CHECK (role IN ('owner','co_founder','employee'))` через Alembic-міграцію.
   `CompanyRole` (Pydantic `Literal`, `backend/app/schemas/user.py`) і `CompanyRole`
   (TypeScript, `frontend/app/types/user.ts`) розширюються тим самим третім значенням.
2. Вводиться `useUserRole()` composable, і всі 14 файлів рефакторяться на нього замість
   збереження копіювання логіки ще й для третьої ролі.
3. Співзасновники відображаються в ТОМУ Ж списку/сторінці "Співробітники", що й звичайні
   employee, з окремим бейджем (не звичайний position-текст).
4. `check:i18n` — оскільки скрипта не існує, він буде створений (мінімальний, рекурсивне
   порівняння ключів `uk.json`/`ru.json`) і запущений перед здачею задачі.

## Модель даних і міграція

Без зміни типу колонки `users.role` (лишається `String(20)`, nullable). Одна
Alembic-міграція:
```python
op.create_check_constraint(
    "ck_users_role_valid",
    "users",
    "role IN ('owner', 'co_founder', 'employee')",
)
```
NULL (individual-акаунти без компанії) проходить CHECK автоматично (SQL: порівняння з
NULL → UNKNOWN → constraint не порушено). Existing owner/employee рядки — без змін
значень, downgrade просто дропає constraint.

`backend/app/schemas/user.py`: `CompanyRole = Literal["owner", "co_founder", "employee"]`.
`frontend/app/types/user.ts`: `export type CompanyRole = 'owner' | 'co_founder' | 'employee'`.

## Backend — авторизаційний шар

`backend/app/dependencies.py` — новий dependency поряд з існуючим:
```python
def require_company_admin(current_user: User = Depends(require_company_member)) -> User:
    """Gate for endpoints owner and co_founder both may use — everything
    previously owner-only EXCEPT role assignment and co-founder deactivation."""
    if current_user.role not in ("owner", "co_founder"):
        raise HTTPException(status_code=403, detail="...")
    return current_user
```
`require_company_owner` лишається без змін (строго `role != "owner"` → 403) і
використовується ТІЛЬКИ для: нового ендпоінту зміни ролі (нижче) і всередині
`update_employee` для co-founder-деактивації (нижче).

**Заміна dependency з `require_company_owner` на `require_company_admin`:**
- `positions.py`: `POST /positions`, `PATCH /positions/{id}`, `DELETE /positions/{id}`
- `currency.py`: `PATCH /company/currency-settings`
- `employees.py`: `POST /employees/invites`, `GET /employees/invites`,
  `PATCH /employees/invites/{id}/revoke`, `update_employee`
- `sales_plans.py`: `upsert_sales_plan`, `delete_sales_plan`
- `dependencies.py::get_owned_employee` — актор-перевірка (звідси працюють
  `GET /employees/{id}`, `GET /employees/{id}/stats`, `PATCH /employees/{id}`)

**`get_owned_employee` (dependencies.py:133) — дві зміни:**
1. Фільтр цілі: `User.role == "employee"` → `User.role.in_(("employee", "co_founder"))`
   (щоб owner/co_founder-актор міг знайти і відредагувати/деактивувати картку
   співзасновника).
2. Додати `User.id != current_user.id` у фільтр — блокує self-match, який стає можливим,
   коли актор-co_founder звертається до власного `id` (раніше структурно неможливо, бо
   owner ніколи не мав `role == "employee"`).

**`list_employees` (employees.py:128):** фільтр `User.role == "employee"` →
`User.role.in_(("employee", "co_founder"))` — щоб співзасновники з'являлись у списку
"Співробітники" для будь-якого учасника компанії (сама точка входу лишається
`require_company_member`, без змін — перегляд списку й сьогодні доступний усім).

**`update_employee` (employees.py:221) — новий inline-guard:**
```python
if "is_active" in update_data and employee.role == "co_founder" and current_user.role != "owner":
    raise HTTPException(status_code=403, detail="Only the company owner can deactivate a co-founder's account")
```
Розміщується одразу після `get_owned_employee`/`require_company_admin` resolve, до
запису змін. Це і є явний виняток із задачі: звільнити/деактивувати співзасновника може
лише реальний owner, навіть якщо інший co_founder технічно пройшов
`require_company_admin`.

**Інлайн-перевірки, які НЕ потребують змін** (перевірено кожну — `role == "employee"` як
обмежувальна гілка, co_founder автоматично отримує owner-рівень):
`listing_authorization.py::is_listing_locked_for_employee`, `sales_plans.py`
(self-scoping рядків + owner-only company-total рядок), `deal_history.py::list_deal_history`,
`listings.py::create_listing` (self-assignment). `auth.py:208` лишається owner-literal
(коректно — стосується лише реєстрації самого owner).

**Свідомо без змін:** `_get_owned_active_employee_or_error` (`listings.py`, `clients.py`)
— фільтр цілі для "відповідального співробітника" лишається `role == "employee"`;
co_founder не стає призначуваним продавцем (поза scope, див. вище).

## Новий ендпоінт: `PATCH /employees/{id}/role`

`backend/app/routers/employees.py`, строго `require_company_owner`.

Схема запиту (новий клас у `backend/app/schemas/employee.py`):
```python
class EmployeeRoleUpdate(BaseModel):
    role: Literal["co_founder", "employee"]
```
Логіка:
1. Знайти ціль: `User.id == employee_id AND company_id == current_user.company_id
   AND role.in_(("employee", "co_founder"))`, інакше 404. (Owner ніколи не потрапляє в
   цей фільтр — структурно неможливо понизити/націлитись на самого owner через цей
   ендпоінт.)
2. `if employee.id == current_user.id: raise HTTPException(400, "...")` — явна помилка
   замість мовчазного 404, хоч self-target і так недосяжний через п.1 (owner не має
   `role in (employee, co_founder)`), явна перевірка лишається як defense-in-depth і
   чіткіше повідомлення про помилку.
3. Валідація переходу: `role == "co_founder"` дозволено лише якщо
   `employee.role == "employee"`; `role == "employee"` (пониження) — лише якщо
   `employee.role == "co_founder"`. Інакше 409 "already this role"/некоректний перехід.
4. Ціль має бути `is_active == True` (не можна міняти роль звільненому).
5. `employee.role = payload.role`, commit, повернути `EmployeeOut`.

Компанія без жодного owner структурно неможлива через цей ендпоінт — він ніколи не
торкається рядка з `role == "owner"`.

## Frontend

**`frontend/app/composables/useUserRole.ts`** (новий):
```ts
export function useUserRole() {
  const authStore = useAuthStore()
  const role = computed(() => authStore.user?.role ?? null)
  return {
    isOwner: computed(() => role.value === 'owner'),
    isCoFounder: computed(() => role.value === 'co_founder'),
    isEmployee: computed(() => role.value === 'employee'),
    isCompanyAdmin: computed(() => role.value === 'owner' || role.value === 'co_founder'),
  }
}
```
Рефакторяться всі 14 файлів з локальними визначеннями (`crm/index.vue`, `settings.vue`,
`ListingForm.vue`, `EmployeeDetailsReadOnly.vue`, `EmployeeDetailModal.vue`,
`crm/analytics.vue`, `crm/inventory/[id].vue`, `layouts/business.vue`,
`crm/employees.vue`, `crm/sales-plans.vue`, `crm/deal-history.vue`, `garage/index.vue`,
`crm/inventory/new.vue`, `crm/composer.vue`, `ClientKanbanBoard.vue`) — кожне поточне
`isOwner`/`isCompanyOwner`/`canManageEmployees` замінюється на `isCompanyAdmin` з
composable, кожне `isEmployee` — на `isEmployee` з composable.

**Виняток (owner-only, НЕ `isCompanyAdmin`):** кнопка/дія призначення чи зняття ролі
співзасновника на картці employee — видима лише коли `isOwner === true`. Це єдине місце
в UI, де використовується строгий `isOwner`, а не `isCompanyAdmin`.

**`EmployeeCard.vue`** (і паралельний `EmployeeDetailsReadOnly.vue`):
- Бейдж "Співзасновник" — кольоровий pill (аналогічно існуючому inactive-status pill,
  інший колір), показується коли `employee.role === 'co_founder'`, окремо від
  position-тексту (який лишається для відображення посади, якщо призначена — див. мету:
  співзасновник може одночасно мати Position для підпису).
- Кнопка "Призначити співзасновником" / "Зняти роль співзасновника" — тільки під
  `useUserRole().isOwner`, викликає новий `PATCH /employees/{id}/role`.

**Employees store** (`stores/employees.ts` чи еквівалент) — новий action
`updateEmployeeRole(id, role)`, оновлює employee в локальному списку після успіху.

**Позиції/Налаштування посад** — без змін, "Співзасновник" органічно не може туди
потрапити (окрема модель).

## i18n

Нові ключі всередину існуючого `crm.employees` (uk.json + ru.json), поряд з
`deactivateButton`/`deactivateConfirmTitle`/`deactivateConfirmMessage`:
- `coFounderBadge` ("Співзасновник")
- `promoteToCoFounderButton` ("Призначити співзасновником")
- `demoteCoFounderButton` ("Зняти роль співзасновника")
- `promoteConfirmTitle`/`promoteConfirmMessage`,
  `demoteConfirmTitle`/`demoteConfirmMessage` (за взірцем існуючого deactivate-confirm)

Новий `frontend/scripts/check-i18n.mjs` — рекурсивно порівнює набори ключів
`uk.json`/`ru.json`, виводить розбіжності, exit code 1 при розбіжності. Додається
`"check:i18n": "node scripts/check-i18n.mjs"` в `package.json`. Запускається перед
здачею задачі.

## Тестування

В проєкті немає жодних існуючих автоматизованих тестів (ні на бекенді — немає pytest у
`requirements.txt`, немає `tests/`, ні на фронтенді) — попередні фічі (підтвердження
email, password reset) свідомо йшли без них. Узгоджено з користувачем: без нової тестової
інфраструктури і для цієї фічі — лише ручна перевірка через `run`-скіл (реальний браузер +
реальні API-виклики) перед здачею:
- Backend: межі `require_company_admin` vs `require_company_owner` на зміненому наборі
  ендпоінтів; `PATCH /employees/{id}/role` — self-target, некоректний перехід,
  non-owner-спроба, неактивна ціль; inline-guard деактивації co_founder в
  `update_employee` (owner може деактивувати co_founder, інший co_founder — ні).
- Frontend: вхід як owner (бачить бейдж+кнопку призначення), вхід як co_founder (має
  owner-рівень доступу всюди в UI, НЕ бачить кнопку призначення/зняття ролі), вхід як
  employee (без змін, як і раніше).

## Відкриті питання для перевірки під час імплементації

- Точна назва Pinia store для співробітників (`employees.ts` чи інша) — перевірити під
  час імплементації, куди додати `updateEmployeeRole`.
- Перевірити, чи в проєкті вже є конвенція для pytest (файли/фікстури), щоб нові тести
  відповідали стилю, а не вводили нову структуру.
