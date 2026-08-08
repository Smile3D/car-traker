from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.client import ClientType


class ClientStageCreate(BaseModel):
    client_type: ClientType
    name: str = Field(min_length=1, max_length=100)


class ClientStageUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ClientStageReorderInput(BaseModel):
    stage_ids: list[int]


class ClientStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    client_type: ClientType
    name: str
    order: int
    created_at: datetime
