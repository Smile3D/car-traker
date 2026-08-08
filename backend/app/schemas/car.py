from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

FuelType = Literal["petrol", "diesel", "gas", "gas_petrol"]


class CarCreate(BaseModel):
    brand: str
    model: str
    year: str
    mileage: str
    vin: str
    fuel_type: FuelType


class CarUpdate(BaseModel):
    brand: str | None = None
    model: str | None = None
    year: str | None = None
    mileage: str | None = None
    vin: str | None = None
    fuel_type: FuelType | None = None


class CarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    brand: str
    model: str
    year: str
    mileage: str
    vin: str
    fuel_type: FuelType
    created_at: datetime
