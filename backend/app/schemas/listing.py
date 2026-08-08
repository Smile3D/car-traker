from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator, model_validator

from app.schemas.client import ClientEmployeeSummary, LeadSource, normalize_and_validate_phone

ConditionType = Literal["new", "used"]
ListingStatus = Literal["draft", "active", "reserved", "sold", "removed", "on_service"]
ListingFuelType = Literal[
    "petrol",
    "diesel",
    "electric",
    "gas",
    "gas_propane_petrol",
    "gas_methane_petrol",
    "hybrid_hev",
    "hybrid_phev",
    "hybrid_mhev",
    "hybrid_reev",
]


class ListingCreate(BaseModel):
    brand: str
    model: str
    year: str
    mileage: str
    vin: str | None = None

    body_type: str
    transmission: str
    engine: str
    fuel_type: ListingFuelType
    color: str

    condition: ConditionType
    condition_description: str | None = None
    trim_level: str | None = None

    purchase_price: float
    additional_expenses: float = 0
    sale_price: float
    discount_amount: float | None = None

    date_added: date | None = None
    deadline_date: date | None = None

    status: ListingStatus = "draft"

    seller_name: str = Field(min_length=2, max_length=100)
    seller_phone: str
    seller_email: EmailStr | None = None
    seller_social_media: str | None = None
    seller_lead_source: LeadSource | None = None
    employee_id: int | None = None

    @field_validator("seller_phone")
    @classmethod
    def validate_seller_phone(cls, value: str) -> str:
        return normalize_and_validate_phone(value)

    @model_validator(mode="after")
    def check_discount_does_not_exceed_sale_price(self) -> Self:
        if self.discount_amount is not None and self.discount_amount > self.sale_price:
            raise ValueError("Discount amount cannot exceed the sale price")
        return self


class ListingUpdate(BaseModel):
    brand: str | None = None
    model: str | None = None
    year: str | None = None
    mileage: str | None = None
    vin: str | None = None

    body_type: str | None = None
    transmission: str | None = None
    engine: str | None = None
    fuel_type: ListingFuelType | None = None
    color: str | None = None

    condition: ConditionType | None = None
    condition_description: str | None = None
    trim_level: str | None = None

    purchase_price: float | None = None
    additional_expenses: float | None = None
    sale_price: float | None = None
    discount_amount: float | None = None

    date_added: date | None = None
    deadline_date: date | None = None
    date_sold: date | None = None

    status: ListingStatus | None = None


class MarkListingSoldInput(BaseModel):
    final_sale_price: float | None = None


class MarkListingOnServiceInput(BaseModel):
    service_note: str | None = None
    service_start_date: date
    service_expected_end_date: date | None = None

    @model_validator(mode="after")
    def check_expected_end_date_not_before_start_date(self) -> Self:
        if self.service_expected_end_date is not None and self.service_expected_end_date < self.service_start_date:
            raise ValueError("Expected end date cannot be before the service start date")
        return self


class ListingDelete(BaseModel):
    """Optional context for why a listing was deleted — shown to the deleting
    user in the moment only. Not persisted anywhere (no deletion log/journal
    yet — same deliberate scope as ClientDelete, see its docstring). Only
    for the single-listing delete flow on the detail page — bulk delete
    (Archive) has no reason field."""

    reason: str | None = None


class ListingBulkDeleteInput(BaseModel):
    ids: list[int]


class ListingBulkDeleteResult(BaseModel):
    deleted_count: int
    deleted_ids: list[int] = []
    skipped: list[str] = []


class ListingSellerSummary(BaseModel):
    """Minimal seller-client info embedded in ListingOut — just enough for
    the frontend to filter "my own listings" (Analytics, for an employee)
    and show the responsible manager's name (Archive) without a separate
    per-listing round-trip."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int | None
    employee: ClientEmployeeSummary | None


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    seller: ListingSellerSummary | None

    brand: str
    model: str
    year: str
    mileage: str
    vin: str | None

    body_type: str
    transmission: str
    engine: str
    fuel_type: ListingFuelType
    color: str

    condition: ConditionType
    condition_description: str | None
    trim_level: str | None

    purchase_price: float
    additional_expenses: float
    sale_price: float
    discount_amount: float | None

    date_added: date
    deadline_date: date | None
    date_sold: date | None
    archived_at: datetime | None

    status: ListingStatus
    service_note: str | None
    service_start_date: date | None
    service_expected_end_date: date | None
    created_at: datetime

    @computed_field
    @property
    def total_cost(self) -> float:
        return self.purchase_price + self.additional_expenses

    @computed_field
    @property
    def final_price(self) -> float:
        return self.sale_price - (self.discount_amount or 0)

    @computed_field
    @property
    def net_profit(self) -> float:
        return self.final_price - self.total_cost

    @computed_field
    @property
    def days_on_lot(self) -> int:
        end_date = self.date_sold if self.date_sold is not None else date.today()
        return (end_date - self.date_added).days
