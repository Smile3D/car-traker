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
