from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RateSource = Literal["auto", "manual"]


class CurrencyRateOut(BaseModel):
    # float here (not Decimal) so these serialize as plain JSON numbers,
    # matching how every other money field in the API (ListingOut, etc.) is
    # exposed — the underlying columns stay Decimal for storage precision.
    auto_rate: float | None
    auto_rate_updated_at: datetime | None
    manual_rate: float | None
    active_source: RateSource
    active_rate: float | None


class CompanyCurrencySettingsUpdate(BaseModel):
    rate_source: RateSource
    # Left unset when just switching back to "auto" without touching the
    # previously saved manual value — so it isn't lost if the owner flips
    # back to "manual" later.
    manual_rate: float | None = None
