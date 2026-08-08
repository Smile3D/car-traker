from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject: str = Field(alias="sub")
    expires_at: int = Field(alias="exp")
