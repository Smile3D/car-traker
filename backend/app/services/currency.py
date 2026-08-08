from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy.orm import Session

from app.models.company import Company

PRIVATBANK_RATE_URL = "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
CACHE_TTL = timedelta(hours=6)


def _fetch_privatbank_usd_sale_rate() -> Decimal | None:
    """Best-effort fetch — any failure (network, bad JSON, missing USD entry)
    just returns None so the caller falls back to whatever's cached. A
    currency reference value must never be the thing that breaks a page."""
    try:
        response = httpx.get(PRIVATBANK_RATE_URL, timeout=10.0)
        response.raise_for_status()
        rate_entries = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    # coursid=5 (cash rate at branches) responds with {ccy, base_ccy, buy,
    # sale} — not the {currency, saleRate} shape used by PrivatBank's other
    # (interbank/NBU) rate endpoints.
    for rate_entry in rate_entries:
        if rate_entry.get("ccy") == "USD":
            try:
                return Decimal(str(rate_entry["sale"]))
            except (KeyError, InvalidOperation):
                return None

    return None


def get_auto_rate(company: Company, database_session: Session) -> tuple[Decimal | None, datetime | None]:
    """Returns (rate, fetched_at) for the PrivatBank auto rate, refreshing
    the cache on company when it's older than CACHE_TTL. Leaves the existing
    cached value untouched if PrivatBank can't be reached right now."""
    is_stale = (
        company.cached_auto_rate_fetched_at is None
        or datetime.now(timezone.utc) - company.cached_auto_rate_fetched_at > CACHE_TTL
    )

    if is_stale:
        fresh_rate = _fetch_privatbank_usd_sale_rate()
        if fresh_rate is not None:
            company.cached_auto_rate = fresh_rate
            company.cached_auto_rate_fetched_at = datetime.now(timezone.utc)
            database_session.commit()

    return company.cached_auto_rate, company.cached_auto_rate_fetched_at
