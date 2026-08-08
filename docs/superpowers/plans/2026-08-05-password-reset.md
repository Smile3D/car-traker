# Password Reset ("Забули пароль?") — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any user (individual, employee, or owner) reset a forgotten password via a Resend-sent email link, using a new `PasswordResetToken` table, two new endpoints (`POST /auth/forgot-password`, `POST /auth/reset-password`), and a branded bilingual email template wired through the existing email infrastructure.

**Architecture:** One new backend table (`password_reset_tokens`, modeled directly on the existing `email_confirmation_tokens` pattern). `email_service.py` is refactored to extract its Resend-sending and current-year logic into shared private helpers, then a second `send_password_reset_email` function reuses them alongside a second pair of HTML templates. Two new `auth.py` endpoints mirror the shape of `confirm_email`/`resend_confirmation`. The frontend gets two new pages (`/auth/forgot-password`, `/auth/reset-password`), two new Pinia actions, and one new link on `login.vue`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (backend); Nuxt 4 + Pinia + `@nuxtjs/i18n` + vee-validate (frontend); Resend REST API via `httpx`.

## Global Constraints

- Password reset works for **all** account types (individual, employee, owner) — unlike email confirmation, there is no `role`/`account_type` check anywhere in this flow.
- `POST /auth/forgot-password` always returns the same generic `200` body regardless of whether the email exists or the request is rate-limited (no user enumeration) — same pattern as `resend-confirmation`. Rate limit: 5 minutes since the last `password_reset_tokens` row for that user, checked via a plain query — no new infrastructure.
- A Resend API failure must never fail the request — log and swallow it (inherited from the existing `email_service.py` behavior).
- Error responses from `POST /auth/reset-password` use `detail={"message": str, "code": str}` (a dict) — same convention as `confirm-email`.
- `POST /auth/reset-password` does **not** log the user in — it returns a plain `MessageOut`, and the frontend redirects to `/login`.
- Every new user-facing string is a translation key added inside the existing `auth` object in both `frontend/locales/uk.json` and `frontend/locales/ru.json` — never a new top-level block, never hardcoded text. Validate both files as JSON after editing.
- No automated tests exist anywhere in this repo (confirmed: no `tests/` dir, no pytest in `backend/requirements.txt`, no test runner in `frontend/package.json`) and none are introduced by this plan — every task's "test" step is a manual verification command instead (`curl` against a running backend, or a browser check).
- **This project directory is not a git repository** (`git status` fails with "not a git repository"). Every task below ends with a "Commit" step per the standard plan template — since there is no repo, treat every such step as **skipped**. Do not run `git init` (explicit prior guidance from the project owner: don't initialize git here unless asked).

---

### Task 1: `PasswordResetToken` model

**Files:**
- Create: `backend/app/models/password_reset_token.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `PasswordResetToken` (fields: `id`, `user_id`, `token`, `created_at`, `expires_at`, `used_at`, relationship `user`) — consumed by Task 2 (migration) and Task 6/7 (endpoints).

- [ ] **Step 1: Create the model**

Create `backend/app/models/password_reset_token.py` — an exact structural copy of `backend/app/models/email_confirmation_token.py`:

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")
```

- [ ] **Step 2: Register the model in `models/__init__.py`**

In `backend/app/models/__init__.py`, the import lines are ordered alphabetically by module path. Add the new import right after `listing_photo` and before `position`:

```python
from app.models.listing_photo import ListingPhoto
from app.models.password_reset_token import PasswordResetToken
from app.models.position import Position
```

And add `"PasswordResetToken"` to the `__all__` list, keeping it alphabetically sorted:

```python
__all__ = [
    "Car",
    "Client",
    "ClientStage",
    "Company",
    "DealHistory",
    "EmailConfirmationToken",
    "EmployeeInvite",
    "FuelRefill",
    "Listing",
    "ListingPhoto",
    "PasswordResetToken",
    "Position",
    "Receipt",
    "SalesPlan",
    "ServiceRecord",
    "ServiceRecordItem",
    "TelegramIntegration",
    "User",
]
```

- [ ] **Step 3: Verify it imports cleanly**

```bash
cd backend && venv/bin/python -c "from app.models import PasswordResetToken; print(PasswordResetToken.__tablename__)"
```
Expected: prints `password_reset_tokens` with no import errors.

- [ ] **Step 4: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 2: Alembic migration

**Files:**
- Create: `backend/alembic/versions/<generated>_add_password_reset.py`

**Interfaces:**
- Consumes: `PasswordResetToken.__tablename__` (Task 1) — schema must match exactly.
- Produces: `password_reset_tokens` table, present in the DB after `alembic upgrade head`.

- [ ] **Step 1: Generate the migration file**

From `backend/`, with `.env` pointing at a running local Postgres:
```bash
venv/bin/alembic revision -m "add password reset"
```
This creates `backend/alembic/versions/<hash>_add_password_reset.py`. Verify `down_revision` was auto-set to `e3716b460ac9` (the current head, confirmed via `alembic heads`) — if it wasn't (e.g. another migration landed since this plan was written), fix `down_revision` to point at whatever `alembic heads` reports before continuing.

- [ ] **Step 2: Fill in `upgrade()`/`downgrade()`**

```python
def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='password_reset_tokens_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='password_reset_tokens_pkey'),
    )
    op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
```

- [ ] **Step 3: Apply and verify**

```bash
venv/bin/alembic upgrade head
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d password_reset_tokens"
```
(Adjust the `psql` invocation if Postgres isn't running in the `db` container in your setup — e.g. `psql "$DATABASE_URL"` if connecting directly.)
Expected: `password_reset_tokens` table exists with a unique index on `token` and a `user_id` FK with `ON DELETE CASCADE`.

- [ ] **Step 4: Verify the downgrade path**

```bash
venv/bin/alembic downgrade -1 && venv/bin/alembic upgrade head
```
Expected: both commands succeed with no errors.

- [ ] **Step 5: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 3: `email_service.py` — extract shared helpers (no behavior change)

**Files:**
- Modify: `backend/app/services/email_service.py`

**Interfaces:**
- Produces: `_send_email_via_resend(to_email: str, subject: str, html: str) -> None`; `_current_year() -> str` — consumed by Task 4.
- This task must not change `send_confirmation_email`'s observable behavior at all — it's a pure refactor.

- [ ] **Step 1: Rewrite the file with the extracted helpers**

Replace the full contents of `backend/app/services/email_service.py`:

```python
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "Car Garage Tracker <onboarding@resend.dev>"

_TEMPLATES_DIRECTORY = Path(__file__).resolve().parent.parent / "templates" / "emails"

_SUBJECT_BY_LOCALE = {
    "uk": "Підтвердіть email — Car Garage Tracker",
    "ru": "Подтвердите email — Car Garage Tracker",
}

_TEMPLATE_FILENAME_BY_LOCALE = {
    "uk": "email_confirmation_uk.html",
    "ru": "email_confirmation_ru.html",
}


def _current_year() -> str:
    return str(datetime.now(timezone.utc).year)


def _send_email_via_resend(to_email: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY is not set — logging the email instead of sending it")
        logger.info("Email for %s | Subject: %s | %s", to_email, subject, html)
        return

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": FROM_ADDRESS, "to": [to_email], "subject": subject, "html": html},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Registration/password-reset must never fail because Resend is down
        # or misconfigured — the caller can always retry.
        logger.exception("Failed to send email to %s via Resend", to_email)


def _render_confirmation_email_html(confirmation_link: str, locale: str) -> str:
    template_filename = _TEMPLATE_FILENAME_BY_LOCALE.get(locale, _TEMPLATE_FILENAME_BY_LOCALE["uk"])
    template_html = (_TEMPLATES_DIRECTORY / template_filename).read_text(encoding="utf-8")

    return template_html.replace("{confirmation_link}", confirmation_link).replace("{current_year}", _current_year())


def send_confirmation_email(to_email: str, confirmation_link: str, locale: str) -> None:
    subject = _SUBJECT_BY_LOCALE.get(locale, _SUBJECT_BY_LOCALE["uk"])
    html = _render_confirmation_email_html(confirmation_link, locale)
    _send_email_via_resend(to_email, subject, html)
```

- [ ] **Step 2: Verify the confirmation email still renders and sends identically**

```bash
cd backend && venv/bin/python -c "
from app.services.email_service import send_confirmation_email
send_confirmation_email('owner@example.com', 'http://localhost:3000/auth/confirm-email?token=abc', 'uk')
"
```
Expected: same behavior as before this refactor — a `WARNING` log about the missing key (if `RESEND_API_KEY` is unset) followed by an `INFO` log with the rendered HTML, no exception. If `RESEND_API_KEY` is set, confirm no exception is raised and (if you want to confirm the live path) check your test inbox for the confirmation email exactly as before.

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 4: Password-reset email templates (uk/ru) + `send_password_reset_email`

**Files:**
- Create: `backend/app/templates/emails/email_password_reset_uk.html`
- Create: `backend/app/templates/emails/email_password_reset_ru.html`
- Modify: `backend/app/services/email_service.py`

**Interfaces:**
- Consumes: `_send_email_via_resend`, `_current_year`, `_TEMPLATES_DIRECTORY` (Task 3).
- Produces: `send_password_reset_email(to_email: str, reset_link: str, locale: str) -> None` — consumed by Task 6.

- [ ] **Step 1: Place the uk template**

Copy the provided `/Users/sergey/Downloads/email_password_reset_uk.html` to
`backend/app/templates/emails/email_password_reset_uk.html` **unchanged** — it already uses
`{current_year}` and `{reset_link}` placeholders, no edits needed.

```bash
cp /Users/sergey/Downloads/email_password_reset_uk.html backend/app/templates/emails/email_password_reset_uk.html
```

- [ ] **Step 2: Create the ru template**

Create `backend/app/templates/emails/email_password_reset_ru.html` — same HTML structure/styles as the uk file, only text nodes translated:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <meta name="x-apple-disable-message-reformatting">
  <title>Сброс пароля</title>
  <style type="text/css">
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { width: 100% !important; min-width: 100%; }
    body, table, td, div, p, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { border: 0; outline: none; text-decoration: none; -ms-interpolation-mode: nearest-neighbor; display: block; }
    a { text-decoration: none; }

    /* Mobile */
    @media only screen and (max-width: 600px) {
      body { width: 100% !important; min-width: 100% !important; }
      .wrapper { width: 100% !important; max-width: 100% !important; }
      .content-cell { width: 100% !important; padding: 16px !important; }
      .card { width: 100% !important; }
      .button-cell { width: 100% !important; }
      .footer-text { font-size: 12px !important; }
    }
  </style>
</head>
<body style="background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.55; color: #1f2937;">
  <div style="display: none; font-size: 1px; color: #f9fafb; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
    Сброс пароля для Car Garage Tracker
  </div>

  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f9fafb; width: 100%; min-width: 100%;">
    <tr>
      <td align="center" style="padding: 0; background-color: #f9fafb;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px; width: 100%;" class="wrapper">

          <tr>
            <td style="padding: 20px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb;">

                <tr>
                  <td style="padding: 40px 32px;" class="content-cell">

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                      <tr>
                        <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 24px; font-weight: 500; color: #1f2937; text-align: left; line-height: 1.3; margin-bottom: 20px;">
                          Сброс пароля
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 32px;">
                      <tr>
                        <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 15px; color: #6b7280; text-align: left; line-height: 1.6;">
                          Мы получили запрос на сброс пароля для вашего аккаунта. Нажмите кнопку ниже, чтобы установить новый пароль.
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 32px;">
                      <tr>
                        <td align="center" style="padding: 0;">
                          <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="background-color: #1e40af; border-radius: 6px;">
                            <tr>
                              <td style="padding: 12px 28px; text-align: center;">
                                <a href="{reset_link}" style="display: inline-block; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 15px; font-weight: 600; color: #ffffff; text-decoration: none; line-height: 1.4; mso-padding-alt: 12px 28px;">
                                  Сбросить пароль
                                </a>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 24px;">
                      <tr>
                        <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #9ca3af; text-align: center; line-height: 1.5;">
                          Ссылка действительна в течение 1 часа
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 24px;">
                      <tr>
                        <td style="height: 1px; background-color: #e5e7eb; font-size: 0; line-height: 0;">
                          &nbsp;
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 8px;">
                      <tr>
                        <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #9ca3af; text-align: center; line-height: 1.5;">
                          Если кнопка не работает, скопируйте эту ссылку:
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 32px;">
                      <tr>
                        <td style="font-family: 'Courier New', monospace; font-size: 12px; color: #1e40af; text-align: center; line-height: 1.4; word-break: break-all;">
                          {reset_link}
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f3f4f6; border-left: 3px solid #1e40af; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
                      <tr>
                        <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 13px; color: #4b5563; text-align: left; line-height: 1.5;">
                          Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо. Ваш пароль останется без изменений, и эта ссылка автоматически перестанет работать через 1 час.
                        </td>
                      </tr>
                    </table>

                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding: 40px 20px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 12px; color: #9ca3af; text-align: center; line-height: 1.6; padding: 0;">
                    <p style="margin: 0 0 8px 0;">
                      © {current_year} Car Garage Tracker. Все права защищены.
                    </p>
                    <p style="margin: 0 0 8px 0;">
                      Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.
                    </p>
                    <p style="margin: 0;">
                      Служба поддержки
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```

- [ ] **Step 3: Add `send_password_reset_email` to `email_service.py`**

Append to the end of `backend/app/services/email_service.py`:

```python
_PASSWORD_RESET_SUBJECT_BY_LOCALE = {
    "uk": "Скидання пароля — Car Garage Tracker",
    "ru": "Сброс пароля — Car Garage Tracker",
}

_PASSWORD_RESET_TEMPLATE_FILENAME_BY_LOCALE = {
    "uk": "email_password_reset_uk.html",
    "ru": "email_password_reset_ru.html",
}


def _render_password_reset_email_html(reset_link: str, locale: str) -> str:
    template_filename = _PASSWORD_RESET_TEMPLATE_FILENAME_BY_LOCALE.get(locale, _PASSWORD_RESET_TEMPLATE_FILENAME_BY_LOCALE["uk"])
    template_html = (_TEMPLATES_DIRECTORY / template_filename).read_text(encoding="utf-8")

    return template_html.replace("{reset_link}", reset_link).replace("{current_year}", _current_year())


def send_password_reset_email(to_email: str, reset_link: str, locale: str) -> None:
    subject = _PASSWORD_RESET_SUBJECT_BY_LOCALE.get(locale, _PASSWORD_RESET_SUBJECT_BY_LOCALE["uk"])
    html = _render_password_reset_email_html(reset_link, locale)
    _send_email_via_resend(to_email, subject, html)
```

- [ ] **Step 4: Verify rendering for both locales**

```bash
cd backend && venv/bin/python -c "
from app.services.email_service import _render_password_reset_email_html
for locale in ('uk', 'ru', 'unknown'):
    html = _render_password_reset_email_html('http://localhost:3000/auth/reset-password?token=abc123', locale)
    assert '{reset_link}' not in html and '{current_year}' not in html, locale
    assert 'http://localhost:3000/auth/reset-password?token=abc123' in html
    print(locale, 'OK', len(html))
"
```
Expected: `uk OK <n>`, `ru OK <n>`, `unknown OK <n>` (falls back to uk template) — no assertion errors.

- [ ] **Step 5: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 5: `ForgotPasswordInput`/`ResetPasswordInput` schemas

**Files:**
- Modify: `backend/app/schemas/auth.py`

**Interfaces:**
- Consumes: `Locale` type alias (`backend/app/schemas/user.py`).
- Produces: `ForgotPasswordInput(email: EmailStr, locale: Locale = "uk")`; `ResetPasswordInput(token: str, new_password: str)` — consumed by Task 6/7.

- [ ] **Step 1: Add the two schemas**

In `backend/app/schemas/auth.py`, add the `Field` import and the `Locale` import, then the two new classes:

```python
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import Locale


class ConfirmEmailInput(BaseModel):
    token: str


class ResendConfirmationInput(BaseModel):
    email: EmailStr


class MessageOut(BaseModel):
    message: str


class ForgotPasswordInput(BaseModel):
    email: EmailStr
    # Same locale mechanism as UserCreate.locale — the frontend passes its
    # current i18n locale; defaults to "uk" for any client that doesn't send one.
    locale: Locale = "uk"


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
```

- [ ] **Step 2: Verify the schemas import and validate**

```bash
cd backend && venv/bin/python -c "
from app.schemas.auth import ForgotPasswordInput, ResetPasswordInput
print(ForgotPasswordInput(email='a@b.com'))
print(ResetPasswordInput(token='x', new_password='12345678'))
"
```
Expected: prints both model reprs (the first shows `locale='uk'` by default), no validation errors.

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 6: `POST /auth/forgot-password`

**Files:**
- Modify: `backend/app/routers/auth.py`

**Interfaces:**
- Consumes: `PasswordResetToken` (Task 1); `send_password_reset_email` (Task 4); `ForgotPasswordInput`, `MessageOut` (Task 5); `settings.frontend_url` (existing).
- Produces: `_create_password_reset_token(user, database_session) -> PasswordResetToken`; `_send_password_reset_email_for_token(user, password_reset_token, locale) -> None` — consumed by Task 7.

- [ ] **Step 1: Update imports and add the two new constants**

In `backend/app/routers/auth.py`, extend the existing import block:

```python
from app.models.email_confirmation_token import EmailConfirmationToken
from app.models.employee_invite import EmployeeInvite
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ConfirmEmailInput,
    ForgotPasswordInput,
    MessageOut,
    ResendConfirmationInput,
    ResetPasswordInput,
)
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.email_service import send_confirmation_email, send_password_reset_email
from app.services.security import create_access_token, hash_password, verify_password
```

Add two new constants right after the existing `RESEND_CONFIRMATION_COOLDOWN` line:

```python
EMAIL_CONFIRMATION_TOKEN_VALIDITY = timedelta(hours=24)
RESEND_CONFIRMATION_COOLDOWN = timedelta(seconds=60)
PASSWORD_RESET_TOKEN_VALIDITY = timedelta(hours=1)
FORGOT_PASSWORD_COOLDOWN = timedelta(minutes=5)
```

- [ ] **Step 2: Add the two helpers**

Add these right after `_send_confirmation_email_for_token`:

```python
def _create_password_reset_token(user: User, database_session: Session) -> PasswordResetToken:
    password_reset_token = PasswordResetToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + PASSWORD_RESET_TOKEN_VALIDITY,
    )
    database_session.add(password_reset_token)
    database_session.commit()
    database_session.refresh(password_reset_token)
    return password_reset_token


def _send_password_reset_email_for_token(user: User, password_reset_token: PasswordResetToken, locale: str) -> None:
    reset_link = f"{settings.frontend_url}/auth/reset-password?token={password_reset_token.token}"
    send_password_reset_email(user.email, reset_link, locale)
```

- [ ] **Step 3: Add the `forgot_password` endpoint**

Add this after `resend_confirmation()` and before `read_current_user()`:

```python
@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(forgot_password_input: ForgotPasswordInput, database_session: Session = Depends(get_db)) -> MessageOut:
    # Always the same response, regardless of what actually happened below —
    # otherwise the response itself would reveal whether an account with
    # this email exists (user enumeration).
    generic_response = MessageOut(message="If this account exists, a password reset email has been sent")

    user = database_session.query(User).filter(User.email == forgot_password_input.email).first()
    if user is None:
        return generic_response

    latest_token = (
        database_session.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    is_rate_limited = (
        latest_token is not None
        and latest_token.created_at > datetime.now(timezone.utc) - FORGOT_PASSWORD_COOLDOWN
    )
    if is_rate_limited:
        return generic_response

    if latest_token is not None and latest_token.used_at is None:
        latest_token.used_at = datetime.now(timezone.utc)
        database_session.commit()

    password_reset_token = _create_password_reset_token(user, database_session)
    _send_password_reset_email_for_token(user, password_reset_token, forgot_password_input.locale)

    return generic_response
```

- [ ] **Step 4: Verify manually**

With the backend running and `RESEND_API_KEY` unset (dev-fallback logging), using any existing test account's email (individual, employee, or owner — all should work):
```bash
curl -s -X POST http://localhost:8000/auth/forgot-password -H "Content-Type: application/json" \
  -d '{"email":"<existing-test-account-email>","locale":"uk"}' | python -m json.tool
curl -s -X POST http://localhost:8000/auth/forgot-password -H "Content-Type: application/json" \
  -d '{"email":"<existing-test-account-email>","locale":"uk"}' | python -m json.tool
curl -s -X POST http://localhost:8000/auth/forgot-password -H "Content-Type: application/json" \
  -d '{"email":"does-not-exist@example.com"}' | python -m json.tool
```
Expected: all three return the identical generic `200` message. The backend log shows a dev-fallback email log (or a real Resend send) for the first call only — the immediate second call is rate-limited (no new log line), and the nonexistent email never logs anything.

- [ ] **Step 5: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 7: `POST /auth/reset-password`

**Files:**
- Modify: `backend/app/routers/auth.py`

**Interfaces:**
- Consumes: `ResetPasswordInput` (Task 5); `PasswordResetToken` (Task 1); `hash_password` (existing, `app/services/security.py`).
- Produces: the endpoint — consumed by frontend Task 11.

- [ ] **Step 1: Add the endpoint**

Add this right after `forgot_password()`:

```python
@router.post("/reset-password", response_model=MessageOut)
def reset_password(reset_password_input: ResetPasswordInput, database_session: Session = Depends(get_db)) -> MessageOut:
    password_reset_token = (
        database_session.query(PasswordResetToken)
        .filter(PasswordResetToken.token == reset_password_input.token)
        .first()
    )
    if password_reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Invalid password reset link", "code": "invalid"},
        )

    if password_reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This password reset link was already used", "code": "already_used"},
        )

    if password_reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "This password reset link has expired", "code": "expired"},
        )

    user = database_session.query(User).filter(User.id == password_reset_token.user_id).first()
    password_reset_token.used_at = datetime.now(timezone.utc)
    user.hashed_password = hash_password(reset_password_input.new_password)
    database_session.commit()

    return MessageOut(message="Password has been reset successfully")
```

- [ ] **Step 2: Verify manually**

Grab the token from Task 6's dev-fallback log (or the real email), then:
```bash
curl -s -X POST http://localhost:8000/auth/reset-password -H "Content-Type: application/json" \
  -d '{"token":"<paste-token-here>","new_password":"newpassword123"}' | python -m json.tool
```
Expected: `200` with the success message.
```bash
curl -s -X POST http://localhost:8000/auth/reset-password -H "Content-Type: application/json" \
  -d '{"token":"<same-token-again>","new_password":"anotherpassword123"}' | python -m json.tool
```
Expected: `400` with `code: "already_used"`.
```bash
curl -s -X POST http://localhost:8000/auth/reset-password -H "Content-Type: application/json" \
  -d '{"token":"not-a-real-token","new_password":"newpassword123"}' | python -m json.tool
```
Expected: `404` with `code: "invalid"`.

Then verify the account can log in with the **new** password (`POST /auth/login`) and **not** with the old one — confirms the full chain works end to end.

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 8: Frontend — auth store actions

**Files:**
- Modify: `frontend/app/stores/auth.ts`

**Interfaces:**
- Produces: `forgotPassword(email: string, locale?: string): Promise<void>`; `resetPassword(token: string, newPassword: string): Promise<void>` — consumed by Tasks 10, 11.

- [ ] **Step 1: Add the two actions**

Add these right after `resendConfirmation`:

```typescript
  async function forgotPassword(email: string, locale?: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/forgot-password', { email, locale })
  }

  async function resetPassword(token: string, newPassword: string): Promise<void> {
    const { apiPost } = useApi()
    await apiPost<{ message: string }>('/auth/reset-password', { token, new_password: newPassword })
  }
```

Add both to the store's returned object:

```typescript
  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    confirmEmail,
    resendConfirmation,
    forgotPassword,
    resetPassword,
    fetchCurrentUser,
    updateBusinessProfile,
    updateOwnProfile,
    uploadAvatar,
    deleteAvatar,
    fetchAvatarImageUrl,
    logout
  }
```

- [ ] **Step 2: Verify the store compiles**

```bash
cd frontend && npx nuxi typecheck 2>&1 | grep -i "stores/auth" || echo "no auth.ts errors"
```
Expected: `no auth.ts errors`.

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 9: Frontend — i18n keys

**Files:**
- Modify: `frontend/locales/uk.json`
- Modify: `frontend/locales/ru.json`

**Interfaces:**
- Produces: the `auth.forgotPassword.*` and `auth.resetPassword.*` key namespaces — consumed by Tasks 10, 11, 12.

- [ ] **Step 1: Add both new blocks to `uk.json`**

Inside the existing `"auth": { ... }` object, add two new sibling keys after `"confirmEmail"`:

```json
    "forgotPassword": {
      "title": "Забули пароль?",
      "body": "Введіть email, і ми надішлемо посилання для скидання пароля.",
      "emailLabel": "Email",
      "submit": "Надіслати посилання",
      "submitting": "Надсилаємо…",
      "checkEmailTitle": "Перевірте пошту",
      "checkEmailBody": "Якщо акаунт з таким email існує, ми надіслали на нього лист із посиланням для скидання пароля.",
      "backToLoginLink": "Повернутися до входу",
      "loginLinkText": "Забули пароль?"
    },
    "resetPassword": {
      "title": "Новий пароль",
      "newPasswordLabel": "Новий пароль",
      "confirmPasswordLabel": "Підтвердіть пароль",
      "passwordMismatch": "Паролі не збігаються",
      "submit": "Зберегти новий пароль",
      "submitting": "Зберігаємо…",
      "successMessage": "Пароль успішно змінено.",
      "goToLoginLink": "Перейти до входу",
      "errorInvalid": "Посилання для скидання пароля недійсне.",
      "errorExpired": "Посилання протерміноване. Запросіть скидання пароля ще раз.",
      "errorAlreadyUsed": "Це посилання вже використано."
    }
```

- [ ] **Step 2: Add the matching blocks to `ru.json`**

```json
    "forgotPassword": {
      "title": "Забыли пароль?",
      "body": "Введите email, и мы отправим ссылку для сброса пароля.",
      "emailLabel": "Email",
      "submit": "Отправить ссылку",
      "submitting": "Отправляем…",
      "checkEmailTitle": "Проверьте почту",
      "checkEmailBody": "Если аккаунт с таким email существует, мы отправили на него письмо со ссылкой для сброса пароля.",
      "backToLoginLink": "Вернуться ко входу",
      "loginLinkText": "Забыли пароль?"
    },
    "resetPassword": {
      "title": "Новый пароль",
      "newPasswordLabel": "Новый пароль",
      "confirmPasswordLabel": "Подтвердите пароль",
      "passwordMismatch": "Пароли не совпадают",
      "submit": "Сохранить новый пароль",
      "submitting": "Сохраняем…",
      "successMessage": "Пароль успешно изменён.",
      "goToLoginLink": "Перейти ко входу",
      "errorInvalid": "Ссылка для сброса пароля недействительна.",
      "errorExpired": "Ссылка просрочена. Запросите сброс пароля ещё раз.",
      "errorAlreadyUsed": "Эта ссылка уже использована."
    }
```

- [ ] **Step 3: Validate both files as JSON**

```bash
python3 -m json.tool frontend/locales/uk.json > /dev/null && echo OK
python3 -m json.tool frontend/locales/ru.json > /dev/null && echo OK
```
Expected: `OK` printed twice.

- [ ] **Step 4: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 10: Frontend — `/auth/forgot-password` page

**Files:**
- Create: `frontend/app/pages/auth/forgot-password.vue`

**Interfaces:**
- Consumes: `authStore.forgotPassword` (Task 8); `auth.forgotPassword.*` i18n keys (Task 9); `createValidators` (`frontend/app/utils/validators.ts`, unchanged).

- [ ] **Step 1: Write the page**

```vue
<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t, locale } = useI18n()
const validators = createValidators(t)

const errorMessage = ref('')
const isSubmitting = ref(false)
const showCheckEmailScreen = ref(false)

const authStore = useAuthStore()

const { meta, handleSubmit } = useForm()
const { value: email, errorMessage: emailError } = useField<string>('email', validators.email, { initialValue: '' })

const onSubmit = handleSubmit(async (values) => {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    await authStore.forgotPassword(values.email, locale.value)
    showCheckEmailScreen.value = true
  } catch (error) {
    errorMessage.value = (error as ApiError).message
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <div>
    <template v-if="!showCheckEmailScreen">
      <h2 class="mb-4 text-center text-lg font-semibold text-foreground">{{ t('auth.forgotPassword.title') }}</h2>
      <p class="mb-4 text-center text-sm text-muted-foreground">{{ t('auth.forgotPassword.body') }}</p>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div>
          <label class="block text-sm font-medium text-foreground" for="email">{{ t('auth.forgotPassword.emailLabel') }} <RequiredMark /></label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            aria-required="true"
            :aria-invalid="!!emailError"
            class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          >
          <p v-if="emailError" class="mt-1 text-xs text-destructive">{{ emailError }}</p>
        </div>

        <div
          v-if="errorMessage"
          class="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {{ errorMessage }}
        </div>

        <button
          type="submit"
          :disabled="isSubmitting || !meta.valid"
          class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          {{ isSubmitting ? t('auth.forgotPassword.submitting') : t('auth.forgotPassword.submit') }}
        </button>

        <p class="text-center text-sm text-muted-foreground">
          <NuxtLink to="/login" class="font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
        </p>
      </form>
    </template>

    <div v-else class="space-y-4 text-center">
      <h2 class="text-lg font-semibold text-foreground">{{ t('auth.forgotPassword.checkEmailTitle') }}</h2>
      <p class="text-sm text-muted-foreground">{{ t('auth.forgotPassword.checkEmailBody') }}</p>
      <NuxtLink to="/login" class="text-sm font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Verify manually in the browser**

With `npm run dev` and the backend both running: go to `/auth/forgot-password`, submit an existing account's email. Expected: form is replaced by the "check email" screen; the backend logs (or sends) a password-reset email. Submit a nonexistent email — expected: identical "check email" screen shown (no way to tell from the UI whether the account exists).

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 11: Frontend — `/auth/reset-password` page

**Files:**
- Create: `frontend/app/pages/auth/reset-password.vue`

**Interfaces:**
- Consumes: `authStore.resetPassword` (Task 8); `ApiError.code` (`frontend/app/composables/useApi.ts`, unchanged); `auth.resetPassword.*`/`auth.forgotPassword.backToLoginLink` i18n keys (Task 9).

- [ ] **Step 1: Write the page**

```vue
<script setup lang="ts">
import { useForm, useField } from 'vee-validate'
import type { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'auth' })

const { t } = useI18n()
const validators = createValidators(t)
const route = useRoute()
const authStore = useAuthStore()

const tokenFromQuery = computed<string | undefined>(() => typeof route.query.token === 'string' ? route.query.token : undefined)

const status = ref<'form' | 'success' | 'error'>(tokenFromQuery.value ? 'form' : 'error')
const errorCode = ref(tokenFromQuery.value ? '' : 'invalid')
const isSubmitting = ref(false)

const { meta, handleSubmit } = useForm()
const { value: newPassword, errorMessage: newPasswordError } = useField<string>('newPassword', validators.minLength(8), { initialValue: '' })
const { value: confirmPassword, errorMessage: confirmPasswordError } = useField<string>('confirmPassword', validators.minLength(8), { initialValue: '' })

const passwordMismatch = computed<boolean>(() => Boolean(confirmPassword.value) && newPassword.value !== confirmPassword.value)

const errorMessageKey = computed<string>(() => {
  if (errorCode.value === 'expired') return 'auth.resetPassword.errorExpired'
  if (errorCode.value === 'already_used') return 'auth.resetPassword.errorAlreadyUsed'
  return 'auth.resetPassword.errorInvalid'
})

const onSubmit = handleSubmit(async (values) => {
  if (passwordMismatch.value || !tokenFromQuery.value) {
    return
  }

  isSubmitting.value = true
  try {
    await authStore.resetPassword(tokenFromQuery.value, values.newPassword)
    status.value = 'success'
  } catch (error) {
    status.value = 'error'
    errorCode.value = (error as ApiError).code ?? 'invalid'
  } finally {
    isSubmitting.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div v-if="status === 'success'" class="space-y-3 text-center">
      <p class="text-sm text-foreground">{{ t('auth.resetPassword.successMessage') }}</p>
      <NuxtLink to="/login" class="text-sm font-medium text-primary hover:underline">{{ t('auth.resetPassword.goToLoginLink') }}</NuxtLink>
    </div>

    <div v-else-if="status === 'error'" class="space-y-3 text-center">
      <p class="text-sm text-destructive">{{ t(errorMessageKey) }}</p>
      <NuxtLink to="/auth/forgot-password" class="text-sm font-medium text-primary hover:underline">{{ t('auth.forgotPassword.backToLoginLink') }}</NuxtLink>
    </div>

    <form v-else class="space-y-4" @submit.prevent="onSubmit">
      <h2 class="text-center text-lg font-semibold text-foreground">{{ t('auth.resetPassword.title') }}</h2>

      <div>
        <label class="block text-sm font-medium text-foreground" for="new-password">{{ t('auth.resetPassword.newPasswordLabel') }} <RequiredMark /></label>
        <input
          id="new-password"
          v-model="newPassword"
          type="password"
          autocomplete="new-password"
          aria-required="true"
          :aria-invalid="!!newPasswordError"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="newPasswordError" class="mt-1 text-xs text-destructive">{{ newPasswordError }}</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-foreground" for="confirm-password">{{ t('auth.resetPassword.confirmPasswordLabel') }} <RequiredMark /></label>
        <input
          id="confirm-password"
          v-model="confirmPassword"
          type="password"
          autocomplete="new-password"
          aria-required="true"
          :aria-invalid="!!confirmPasswordError || passwordMismatch"
          class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
        <p v-if="passwordMismatch" class="mt-1 text-xs text-destructive">{{ t('auth.resetPassword.passwordMismatch') }}</p>
      </div>

      <button
        type="submit"
        :disabled="isSubmitting || !meta.valid || passwordMismatch"
        class="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span v-if="isSubmitting" class="size-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
        {{ isSubmitting ? t('auth.resetPassword.submitting') : t('auth.resetPassword.submit') }}
      </button>
    </form>
  </div>
</template>
```

- [ ] **Step 2: Verify the success path**

Request a password reset via `/auth/forgot-password` (Task 10), copy the reset link from the backend log (or real email), open it. Expected: the form renders (new password + confirm password fields), typing mismatched passwords shows the mismatch message and disables submit, submitting matching valid passwords shows the success message with a link to `/login`, and logging in with the new password works.

- [ ] **Step 3: Verify the error paths**

Visit `/auth/reset-password` with no `token` query param — expected: `errorInvalid` message with a link back to `/auth/forgot-password`. Visit it again with the same (now used) token from Step 2 — expected: `errorAlreadyUsed`. Visit it with a made-up token — expected: `errorInvalid`.

- [ ] **Step 4: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

### Task 12: Frontend — "Забули пароль?" link on `login.vue`

**Files:**
- Modify: `frontend/app/pages/login.vue`

**Interfaces:**
- Consumes: `auth.forgotPassword.loginLinkText` i18n key (Task 9).

- [ ] **Step 1: Add the link**

In `frontend/app/pages/login.vue`'s template, add a right-aligned link right after the password field's closing `</div>` and before the `<!-- UnconfirmedEmailBlock -->` comment:

```html
    <div>
      <label class="block text-sm font-medium text-foreground" for="password">{{ t('auth.login.passwordLabel') }} <RequiredMark /></label>
      <input
        id="password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        aria-required="true"
        :aria-invalid="!!passwordError"
        class="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
      >
      <p v-if="passwordError" class="mt-1 text-xs text-destructive">{{ passwordError }}</p>
      <p class="mt-1.5 text-right">
        <NuxtLink to="/auth/forgot-password" class="text-xs font-medium text-primary hover:underline">{{ t('auth.forgotPassword.loginLinkText') }}</NuxtLink>
      </p>
    </div>
```

(everything else in the file is unchanged)

- [ ] **Step 2: Verify manually**

Open `/login` in the browser. Expected: a "Забули пароль?" link appears right below the password field, right-aligned; clicking it navigates to `/auth/forgot-password`.

- [ ] **Step 3: Commit**

Skipped — no git repository in this project (see Global Constraints).

---

## Final end-to-end verification (maps to the task's "Крок 4")

After all 12 tasks are done:

1. Call `POST /auth/forgot-password` for a real test account with `RESEND_API_KEY` set — confirm the email arrives via Resend with the new layout (card, button, security-notice block), visually consistent with the confirmation email (same header/footer/colors).
2. Click the button in the email, confirm it lands on `{FRONTEND_URL}/auth/reset-password?token=...`, submit a new password, confirm the token is invalidated (reusing it returns `already_used`), and confirm login with the new password works.
3. Repeat with a `ru`-locale account (or pass `"locale":"ru"` directly) and confirm the Russian template renders correctly (preheader, heading, button, security notice, footer).
