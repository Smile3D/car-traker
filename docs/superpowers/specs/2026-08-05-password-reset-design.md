# Скидання пароля ("Забули пароль?") (Car Garage Tracker)

**Дата:** 2026-08-05
**Статус:** Approved

## Мета

Додати повний флоу відновлення забутого пароля: `POST /auth/forgot-password` (запит
листа), `POST /auth/reset-password` (встановлення нового пароля за токеном), брендований
email-шаблон (`email_password_reset_{uk,ru}.html`), підключений через уже наявну
Resend-інфраструктуру `email_service.py`.

На відміну від фічі підтвердження email (`docs/superpowers/specs/2026-08-05-email-confirmation-design.md`),
скидання пароля доступне для **всіх** типів акаунтів (individual, employee, owner) —
забутий пароль не пов'язаний з підтвердженням email власника компанії.

## Scope

In scope:
- Модель `PasswordResetToken` + Alembic-міграція
- `email_service.py` — новий `send_password_reset_email(...)`, спільні приватні хелпери
  (`_send_email_via_resend`, `_current_year`) винесені з існуючого
  `send_confirmation_email`, щоб обидва листи ділили один HTTP-виклик до Resend і одну
  підстановку року
- Два нові ендпоінти: `POST /auth/forgot-password`, `POST /auth/reset-password`
- Два нові HTML-шаблони листа (uk/ru) в `backend/app/templates/emails/`
- Фронтенд: `pages/auth/forgot-password.vue`, `pages/auth/reset-password.vue`, посилання
  "Забули пароль?" на `pages/login.vue`, нові actions в `stores/auth.ts`
- i18n-ключі (uk/ru) — нові під-об'єкти `auth.forgotPassword`, `auth.resetPassword`

Out of scope (свідомо не робиться зараз):
- Інвалідація/revocation вже виданих JWT після зміни пароля — у проєкті немає жодного
  механізму revocation взагалі (стейтлес JWT, без refresh-токенів чи session-store), тому
  додавати його тільки заради цієї фічі — over-engineering. Стара сесія просто живе до
  природного закінчення `access_token_expire_minutes` (60 хв), як і зараз для будь-якої
  іншої зміни (напр. деактивації employee).
- Auto-login одразу після `reset-password` — свідоме рішення користувача: показуємо
  success і редіректимо на `/login`, користувач логіниться новим паролем сам.
- Автоматизовані тести (так само, як і в email-confirmation — в проєкті немає існуючої
  тестової конвенції).

## Дані, з'ясовані під час дослідження кодбази

- `EmailConfirmationToken` (`backend/app/models/email_confirmation_token.py`) — прямий
  взірець для `PasswordResetToken`: `token String(64) unique+index`, `expires_at`
  tz-aware, `used_at` nullable, `user_id` FK CASCADE.
- `hash_password`/`verify_password` вже є в `backend/app/services/security.py`
  (bcrypt через passlib) — перевикористовуються без змін.
- `UserCreate.password` валідується `Field(min_length=8)` — та сама вимога
  застосовується до `new_password` у reset-ендпоінті.
- Anti-enumeration патерн (generic `200` відповідь незалежно від існування акаунта) вже
  застосований у `resend-confirmation` — той самий підхід переноситься на
  `forgot-password`.
- `email_service.py` наразі має `send_confirmation_email` з інлайновим HTTP-викликом до
  Resend і інлайновою підстановкою `{current_year}` — обидва виносяться в спільні
  приватні функції під час додавання другого листа, а не дублюються.
- Фронтендові сторінки `login.vue`/`confirm-email.vue`/`register.vue` — усталений патерн
  для auth-сторінок: `definePageMeta({ layout: 'auth' })`, vee-validate (`useForm`/
  `useField` + `createValidators(t)`), `ApiError` з `useApi.ts` для помилок,
  `onMounted` для читання токена з `route.query` (client-only, той самий SSR-нюанс, що
  описаний коментарем у `confirm-email.vue`).

## Рішення, узгоджені з користувачем

1. Скидання пароля доступне для **всіх** типів акаунтів (individual, employee, owner) —
   не обмежується, як email-confirmation, тільки owner.
2. Токен зберігається в окремій таблиці `PasswordResetToken` (той самий патерн, що й
   `EmailConfirmationToken`/`EmployeeInvite`), а не як stateless JWT і не як спільна
   таблиця з `EmailConfirmationToken` через поле `purpose` — окрема таблиця найкраще
   узгоджена з тим, як у проєкті вже двічі розведені концептуально схожі, але семантично
   різні "токен на дію" сутності.
3. `POST /auth/reset-password` **не** логінить користувача автоматично — повертає
   `MessageOut`, фронтенд показує success і редіректить на `/login`.
4. Rate-limit на `POST /auth/forgot-password` — **5 хвилин** (довший, ніж 60с у
   `resend-confirmation`, — скидання пароля чутливіша дія), той самий інлайн-механізм
   (перевірка `created_at` останнього токена користувача).

## Модель даних і міграція

Нова `backend/app/models/password_reset_token.py`:
```python
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int]
    user_id: Mapped[int]          # FK users.id, CASCADE
    token: Mapped[str]            # String(64), unique, index; secrets.token_urlsafe(32)
    created_at: Mapped[datetime]  # server_default=func.now()
    expires_at: Mapped[datetime]  # tz-aware, created_at + 1 година
    used_at: Mapped[datetime | None]
```

Одна Alembic-міграція: `create_table("password_reset_tokens")` + unique index на
`token` (стиль — як в `1c02820b2c14_add_employee_invites_table.py` /
міграції `email_confirmation_tokens`). Жодних змін до таблиці `users`.

## Backend-сервіси

- `backend/app/services/email_service.py`:
  - Рефактор: винести з `send_confirmation_email` спільний HTTP-виклик у приватну
    `_send_email_via_resend(to_email: str, subject: str, html: str) -> None` (містить
    поточну логіку fallback-логування, коли `resend_api_key is None`, і `try/except
    httpx.HTTPError` з `logger.exception`, що не прокидається далі).
  - Винести підстановку року у приватну `_current_year() -> str`, яку викликають обидва
    рендери (`_render_confirmation_email_html` і новий
    `_render_password_reset_email_html`).
  - Новий `_TEMPLATE_FILENAME_BY_LOCALE_RESET` (`email_password_reset_uk.html`/
    `email_password_reset_ru.html`), новий `_SUBJECT_BY_LOCALE_RESET`.
  - Новий `send_password_reset_email(to_email: str, reset_link: str, locale: str) -> None`
    — рендерить шаблон (`.replace("{reset_link}", ...)`, `.replace("{current_year}", ...)`),
    викликає `_send_email_via_resend(...)`.
- Rate-limit — інлайн в `forgot_password`, той самий підхід, що й `resend_confirmation`:
  якщо найновіший `PasswordResetToken.created_at` користувача молодший за 5 хвилин — не
  відправляти нічого, повернути generic `200`.

## Backend-ендпоінти (`backend/app/routers/auth.py`)

**`POST /auth/forgot-password`** (схема `ForgotPasswordInput`: `{"email": "...", "locale":
"uk"}`, `locale` опційний з дефолтом `"uk"`, той самий `Locale` тип, що й у `UserCreate`):
- Завжди повертає однаковий `200 {"message": "..."}"` — незалежно від того, чи існує
  акаунт з таким email, чи спрацював rate-limit (anti-enumeration, як у
  `resend-confirmation`).
- Користувача не знайдено → одразу generic-відповідь.
- Rate-limited (останній `PasswordResetToken` користувача молодший за 5 хв) → generic-
  відповідь, без нового токена/листа.
- Інакше: інвалідувати (`used_at = now()`) всі невикористані `PasswordResetToken`
  користувача, створити новий (`secrets.token_urlsafe(32)`, `expires_at = now() + 1h`),
  надіслати `send_password_reset_email(user.email, reset_link, locale)`, де
  `reset_link = f"{settings.frontend_url}/auth/reset-password?token={token}"`.

**`POST /auth/reset-password`** (схема `ResetPasswordInput`: `{"token": "...",
"new_password": "..."}"`, `new_password: str = Field(min_length=8)`):
- токен не знайдено → `404 {"code": "invalid"}`
- `used_at is not None` → `400 {"code": "already_used"}`
- `expires_at < now()` → `400 {"code": "expired"}`
- інакше: `used_at = now()`, `user.hashed_password = hash_password(new_password)`,
  commit, повернути `MessageOut` (той самий формат, що й `resend-confirmation`).

Обидва ендпоінти використовують хелпери-дзеркала до вже наявних:
`_create_password_reset_token(user, database_session) -> PasswordResetToken` (дзеркало
`_create_confirmation_token`), `_send_password_reset_email_for_token(user,
password_reset_token, locale) -> None` (дзеркало
`_send_confirmation_email_for_token`).

## Frontend

- `stores/auth.ts` — нові actions:
  - `forgotPassword(email: string, locale?: string): Promise<void>` →
    `apiPost('/auth/forgot-password', { email, locale })`
  - `resetPassword(token: string, newPassword: string): Promise<void>` →
    `apiPost('/auth/reset-password', { token, new_password: newPassword })`, без запису в
    `token`/виклику `fetchCurrentUser()` (без auto-login).
- Нова `pages/auth/forgot-password.vue` — форма з email (той самий стиль/патерн валідації,
  що й `login.vue`: `useForm`/`useField`, `createValidators(t).email`). Успіх → inline-стан
  "перевірте пошту" (без розкриття, чи існує акаунт — той самий текст незалежно від
  результату).
- Нова `pages/auth/reset-password.vue` — читає `token` з `route.query` (той самий
  client-only `onMounted`-нюанс, що в `confirm-email.vue`). Форма: новий пароль +
  підтвердження пароля, клієнтська валідація збігу і мін. 8 символів. Успіх →
  повідомлення "пароль змінено" + `router.push('/login')`. Помилка → повідомлення за
  `(error as ApiError).code` (`expired`/`already_used`/`invalid`), той самий патерн, що
  в `confirm-email.vue`.
- `pages/login.vue` — додати `NuxtLink` "Забули пароль?" на `/auth/forgot-password` під
  полем пароля (той самий текстовий стиль, що посилання "Зареєструватись" внизу форми).
- Жодного нового спільного "resend"-компонента не потрібно — на відміну від
  email-confirmation, тут немає повторної кнопки в декількох місцях; сама сторінка
  `forgot-password.vue` і є єдиною точкою повторного запиту (користувач просто ще раз
  надсилає форму).

## i18n

Нові під-об'єкти всередину існуючого `auth` в `frontend/locales/{uk,ru}.json`:
- `auth.forgotPassword`: заголовок форми, submit-текст, "перевірте пошту" повідомлення,
  посилання "Забули пароль?" (використовується на `login.vue`).
- `auth.resetPassword`: заголовок, лейбли "новий пароль"/"підтвердіть пароль", помилка
  розбіжності паролів (клієнтська), success-повідомлення, помилки за кодом
  (`expired`/`already_used`/`invalid` — можна перевикористати формулювання з
  `auth.confirmEmail`, якщо підходить за змістом, або дати окремий текст, специфічний для
  скидання пароля).

Жодного нового top-level блоку. Після редагування обох файлів — перевірити валідність
JSON.

## Тестування (Крок 4 з задачі)

1. Викликати `POST /auth/forgot-password` для тестового акаунту (будь-якого типу —
   individual/employee/owner), переконатись, що реальний лист приходить через Resend з
   новою версткою (картка, кнопка, security-notice блок), візуально консистентний з
   листом підтвердження email.
2. Перевірити повний ланцюжок: кнопка веде на `{FRONTEND_URL}/auth/reset-password?token=...`,
   нова форма зберігає пароль, токен інвалідується (повторне використання того самого
   токена → `already_used`), логін новим паролем працює.
3. Перевірити uk і ru версії листа (preheader, заголовок, кнопка, security-notice, footer).
