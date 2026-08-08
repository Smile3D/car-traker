from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class FuelRefillCreate(BaseModel):
    refill_date: date
    fuel_amount: float
    cost: float
    mileage: int | None = None
    station_name: str | None = None


class FuelRefillUpdate(BaseModel):
    refill_date: date | None = None
    fuel_amount: float | None = None
    cost: float | None = None
    mileage: int | None = None
    station_name: str | None = None


class FuelRefillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    car_id: int
    refill_date: date
    fuel_amount: float
    cost: float
    mileage: int | None
    station_name: str | None
    created_at: datetime
