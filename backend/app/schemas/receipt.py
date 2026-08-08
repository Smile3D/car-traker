from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class LinkedServiceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_type: str
    service_date: date
    mileage: int


class LinkedFuelRefillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    refill_date: date
    fuel_amount: float
    cost: float


class ReceiptLinkInput(BaseModel):
    service_record_id: int | None = None
    fuel_refill_id: int | None = None

    @model_validator(mode="after")
    def check_links_are_mutually_exclusive(self) -> Self:
        if self.service_record_id is not None and self.fuel_refill_id is not None:
            raise ValueError("A receipt can be linked to at most one of service_record_id or fuel_refill_id")
        return self


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    car_id: int
    description: str | None
    uploaded_at: datetime
    service_record_id: int | None
    fuel_refill_id: int | None
    service_record: LinkedServiceRecordOut | None
    fuel_refill: LinkedFuelRefillOut | None
