from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

from app.schemas.client import LeadSource

DealType = Literal["sold", "removed"]


class DealHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int | None
    deal_type: DealType

    brand: str
    model: str
    year: str
    vin: str | None

    seller_name: str
    seller_phone: str
    buyer_name: str | None
    buyer_phone: str | None
    seller_lead_source: LeadSource | None
    buyer_lead_source: LeadSource | None

    final_price: float | None
    purchase_price: float | None
    additional_expenses: float | None

    employee_name: str | None
    employee_id: int | None

    date_closed: date
    date_added: date | None
    created_at: datetime

    @computed_field
    @property
    def net_profit(self) -> float | None:
        if self.final_price is None or self.purchase_price is None or self.additional_expenses is None:
            return None
        return self.final_price - self.purchase_price - self.additional_expenses

    @computed_field
    @property
    def days_on_lot(self) -> int | None:
        if self.date_added is None:
            return None
        return (self.date_closed - self.date_added).days
