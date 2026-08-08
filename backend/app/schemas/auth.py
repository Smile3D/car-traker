from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import Locale


class ConfirmEmailInput(BaseModel):
    token: str


class ResendConfirmationInput(BaseModel):
    email: EmailStr


class MessageOut(BaseModel):
    message: str


class ForgotPasswordInput(BaseModel):
    email: EmailStr
    # Same locale mechanism as UserCreate.locale — the frontend passes its
    # current i18n locale; defaults to "uk" for any client that doesn't send one.
    locale: Locale = "uk"


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
