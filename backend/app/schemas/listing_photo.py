from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ListingPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    order: int
    uploaded_at: datetime


class ListingPhotoReorderInput(BaseModel):
    photo_ids: list[int]


class ListingPhotoUploadResult(BaseModel):
    created: list[ListingPhotoOut]
    # Per-file messages for uploads that failed validation/conversion — a bad
    # file in a batch never aborts the ones that succeeded.
    errors: list[str]
