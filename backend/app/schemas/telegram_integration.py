from datetime import datetime

from pydantic import BaseModel, Field


class TelegramConnectInput(BaseModel):
    bot_token: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)


class TelegramStatusOut(BaseModel):
    is_connected: bool
    channel_id: str | None
    created_at: datetime | None


class TelegramPublishInput(BaseModel):
    text: str = Field(min_length=1)


class TelegramPublishOut(BaseModel):
    message_id: int
