from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    upload_dir: str = "uploads"

    # Used to build the confirm-email link sent to a new company owner
    # ("{frontend_url}/auth/confirm-email?token=..."). Defaults to the same
    # origin already hardcoded as the CORS allow-origin in main.py.
    frontend_url: str = "http://localhost:3000"

    # Optional: without it, email_service.py logs the confirmation email to
    # the console instead of calling Resend — lets the app run locally
    # before a developer has created a Resend account.
    resend_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
