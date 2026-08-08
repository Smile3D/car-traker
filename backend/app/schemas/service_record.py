from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecordType = Literal["maintenance", "repair"]


class ServiceRecordItemInput(BaseModel):
    name: str
    price: float


class ServiceRecordItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float


class ServiceRecordCreate(BaseModel):
    record_type: RecordType
    service_date: date
    mileage: int
    items: list[ServiceRecordItemInput] = Field(min_length=1)


class ServiceRecordUpdate(BaseModel):
    record_type: RecordType | None = None
    service_date: date | None = None
    mileage: int | None = None
    items: list[ServiceRecordItemInput] | None = Field(default=None, min_length=1)


class ServiceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    car_id: int
    record_type: RecordType
    service_date: date
    mileage: int
    items: list[ServiceRecordItemOut]
    total_cost: float
    created_at: datetime
