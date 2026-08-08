# Підтвердження email при реєстрації owner-а компанії (Car Garage Tracker)

**Дата:** 2026-08-05
**Статус:** Approved

## Мета

Додати обов'язкове підтвердження email для власника (owner) компанії, який реєструється
через `POST /auth/register` з `account_type="business"` і без `invite_token`. Без
підтвердження такий користувач не може залогінитись.

Реєстрація співробітника через invite-посилання (`invite_token` присутній) і реєстрація
"individual"-акаунту (`account_type="individual"`, без компанії) — **без змін**, лист не
надсилається, `is_email_confirmed` виставляється одразу `true`.

## Scope

In scope:
- `User.is_email_confirmed` (Boolean) + модель `EmailConfirmationToken`
- Alembic-міграція з backfill `is_email_confirmed=true` для всіх існуючих користувачів
- `email_service.py` — відправка листа підтвердження через Resend API (`httpx`), з
  dev-fallback (лог в консоль), якщо `RESEND_API_KEY` не заданий
- Зміна `POST /auth/register` (тільки owner/business-гілка), `POST /auth/login`
- Нові ендпоінти `POST /auth/confirm-email`, `POST /auth/resend-confirmation`
- Фронтенд: екран "перевірте пошту" на сторінці реєстрації, нова сторінка
  `/auth/confirm-email`, блок на сторінці логіну для `email_not_confirmed`
- i18n-ключі (uk/ru) всередині існуючої секції `auth`

Out of scope (свідомо не робиться зараз):
- Реєстрація/логін employee та individual-акаунтів — без змін
- Refresh-токени, зміна формату Token за межами нових ендпоінтів
- Redis/зовнішня rate-limit інфраструктура — ліміт рахується прямим запитом до
  `EmailConfirmationToken`
- Автоматизовані тести (в проєкті немає існуючої тестової конвенції; не запитувалось)

## Дані, з'ясовані під час дослідження кодбази

- Один `User` (`backend/app/models/user.py`) на owner/employee/individual, роль тільки
  через `role` + `company_id`. Окремої моделі `Owner`/`Employee` немає.
- Один ендпоінт `POST /auth/register` (`backend/app/routers/auth.py`, `UserCreate` з
  опційним `invite_token`) обробляє всі три випадки. Не повертає токен — фронтенд
  (`stores/auth.ts::register`) сам викликає `login()` одразу після успішної реєстрації.
- JWT видається через `create_access_token(subject=user.email)`
  (`backend/app/services/security.py`), сьогодні викликається тільки з `login()`.
- Немає жодного існуючого структурованого формату помилки (`{"detail": "<string>"}`
  всюди) і немає жодного rate-limiting в проєкті — обидва рішення нижче є першим
  прецедентом.
- `EmployeeInvite` (`backend/app/models/employee_invite.py`) — прямий взірець для
  `EmailConfirmationToken`: `token String(64) unique+index`, `expires_at` tz-aware,
  `used_at` nullable.
- Токен авторизації на фронтенді зберігається через `useCookie('auth_token')`
  (`frontend/app/stores/auth.ts`), не localStorage.
- i18n: `frontend/locales/{uk,ru}.json`, секція `auth` вже має `login`/`register`
  під-об'єкти. Нові ключі — всередину `auth`, не новий top-level блок.

## Рішення, узгоджені з користувачем

1. Підтвердження email потрібне **тільки** для owner (`account_type="business"`, без
   invite). Individual-акаунти підтвердження не потребують.
2. `POST /auth/resend-confirmation` завжди повертає однакову generic-відповідь
   (`200 {"message": "..."}"`), незалежно від того, чи існує акаунт з таким email, чи він
   вже підтверджений, чи спрацював rate-limit — щоб не розкривати існування акаунту
   стороннім особам за email (user enumeration).
3. Структура помилки для нових/змінених ендпоінтів: `detail` може бути об'єктом
   `{"message": "...", "code": "..."}` замість рядка. Це вводиться лише для цих
   ендпоінтів; всі інші лишаються плоским рядком. Фронтендовий нормалізатор помилок
   (`useApi.ts`) підтримує обидва варіанти.
4. Rate-limit на resend — 60 секунд, рахується прямим запитом
   `created_at` останнього `EmailConfirmationToken` користувача, без нової інфраструктури.

## Модель даних і міграція

`backend/app/models/user.py`:
```python
is_email_confirmed: Mapped[bool] = mapped_column(server_default="false")
```

Нова `backend/app/models/email_confirmation_token.py`:
```python
class EmailConfirmationToken(Base):
    __tablename__ = "email_confirmation_tokens"
    id: Mapped[int]
    user_id: Mapped[int]          # FK users.id, CASCADE
    token: Mapped[str]            # String(64), unique, index; secrets.token_urlsafe(32)
    created_at: Mapped[datetime]  # server_default=func.now()
    expires_at: Mapped[datetime]  # tz-aware, created_at + 24h
    used_at: Mapped[datetime | None]
```

Одна Alembic-міграція:
- `create_table("email_confirmation_tokens")` + unique index на `token` (стиль —
  як в `1c02820b2c14_add_employee_invites_table.py`)
- `add_column("users", "is_email_confirmed", server_default="false")`
- Data-міграція в тій самій ревізії: `UPDATE users SET is_email_confirmed = true` для
  всіх існуючих рядків (усі поточні користувачі — тестові/довірені, реєструвались до
  фічі).

Нові employee-акаунти після цієї фічі отримують `is_email_confirmed=True` явно в коді
під час прийняття invite (не через backfill).

## Backend-сервіси

- `backend/app/config.py`: додати `resend_api_key: str | None = None` і, якщо ще не
  існує еквівалент, `frontend_url: str` (перевірити під час імплементації — можливо вже
  є щось на кшталт CORS-origin, яке можна перевикористати). Перший опційний зовнішній
  ключ в `Settings` — задокументувати коментарем чому опційний.
- `backend/app/services/email_service.py`:
  `send_confirmation_email(to_email: str, confirmation_link: str, locale: str) -> None`.
  Якщо `settings.resend_api_key is None` — залогувати попередження (один раз) і
  залогувати HTML листа в консоль замість реального виклику (dev-режим). Інакше —
  POST `https://api.resend.com/emails`, `Authorization: Bearer {resend_api_key}` через
  `httpx`. Будь-яка помилка (мережа, non-2xx) — залогувати і **не** прокидати exception
  далі; реєстрація не повинна падати через збій Resend.
- Rate-limit — інлайн в `resend-confirmation`: якщо найновіший
  `EmailConfirmationToken.created_at` користувача молодший за 60 секунд — не відправляти
  нічого, повернути той самий generic `200`.

## Backend-ендпоінти (`backend/app/routers/auth.py`)

**`POST /auth/register`** — гілки `invite_token` (employee) і `account_type="individual"`
без змін. Гілка `account_type="business"` без invite: після створення `User`+`Company` —
створити `EmailConfirmationToken`, викликати `send_confirmation_email(...)` з локаллю
запиту (перевірити під час імплементації, як реєстрація сьогодні дізнається locale —
query/header/поле в тілі; дефолт `uk`, якщо не знайдено). Response лишається `UserRead`
без токена.

**`POST /auth/login`** — після перевірки пароля: якщо
`user.role == "owner" and not user.is_email_confirmed` → `403`,
`detail={"message": "...", "code": "email_not_confirmed", "email": user.email}`. Employee
та individual — без змін (в них `is_email_confirmed` завжди `true`).

**`POST /auth/confirm-email`** (`{"token": "..."}"` в тілі):
- токен не знайдено → `404 {"code": "invalid"}`
- `used_at is not None` → `400 {"code": "already_used"}`
- `expires_at < now()` → `400 {"code": "expired"}`
- інакше: `used_at = now()`, `user.is_email_confirmed = True`,
  `create_access_token(user.email)`, повернути `Token` — той самий формат, що й `/login`.

**`POST /auth/resend-confirmation`** (`{"email": "..."}"`):
- користувача не знайдено, або вже підтверджений, або rate-limit — усі три випадки
  повертають однаковий `200 {"message": "..."}"` без відправки листа
- інакше: інвалідувати (`used_at = now()`) всі невикористані токени користувача,
  створити новий, відправити лист, повернути той самий `200`.

## Frontend

- `stores/auth.ts::register(...)` — для business/no-invite гілки **не** викликати
  `login()` після успішної реєстрації; повернути сигнал, який сторінка використає для
  показу стану "перевірте пошту". Нові actions: `resendConfirmation(email)`,
  `confirmEmail(token)` (останній зберігає токен так само, як `login()`:
  `useCookie('auth_token')` + `fetchCurrentUser()`).
- `pages/register.vue` — inline-стан "перевірте пошту" (без окремого редіректу) з
  кнопкою повторної відправки і клієнтським кулдауном 60с (узгоджено із серверним
  rate-limit).
- Нова `pages/auth/confirm-email.vue` — читає `token` з `route.query` при монтуванні,
  викликає `confirmEmail(token)`. Успіх → редірект на Дашборд (та сама логіка
  пост-логін редіректу, що вже використовується). Помилка → повідомлення за
  `error.data.detail.code` (`expired`/`already_used`/`invalid`) + форма повторної
  відправки (поле email, бо токен-помилка не завжди несе email).
- `pages/login.vue` — при `code === "email_not_confirmed"` показати блок підтвердження
  email (з `email` із тіла помилки) + кнопку повторної відправки з тим самим кулдауном.
- `composables/useApi.ts` — нормалізатор помилок підтримує
  `detail: string | {message, code, email?}`, `ApiError.code` опційний, поведінка для
  існуючих викликів (плоский рядок) не міняється.
- Спільний компонент/composable "кнопка повторної відправки з кулдауном" — один,
  перевикористовується на 3 сторінках (register/confirm-email/login).

## i18n

Нові ключі — всередину існуючого `auth` об'єкта в `frontend/locales/uk.json` і
`frontend/locales/ru.json` (новий під-об'єкт `auth.confirmEmail`: заголовок/текст
"перевірте пошту", текст і кулдаун кнопки повторної відправки, повідомлення про
помилки за кодом, блок підтвердження на сторінці логіну). Жодного нового top-level
блоку. Після редагування обох файлів — перевірити валідність JSON.

## Відкриті питання для перевірки під час імплементації

- Чи реєстрація сьогодні вже знає locale користувача (поле в тілі запиту, query-param,
  чи `Accept-Language`) — якщо так, перевикористати; якщо ні, дефолт `uk`.
- Чи в `Settings`/CORS вже є щось на кшталт frontend origin, яке можна перевикористати
  замість нового `frontend_url`.
