import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_member
from app.models.telegram_integration import TelegramIntegration
from app.models.user import User
from app.schemas.telegram_integration import (
    TelegramConnectInput,
    TelegramPublishInput,
    TelegramPublishOut,
    TelegramStatusOut,
)

router = APIRouter(prefix="/integrations/social/telegram", tags=["telegram-integration"])

TELEGRAM_API_BASE_URL = "https://api.telegram.org"


def _get_integration(company_id: int, database_session: Session) -> TelegramIntegration | None:
    return (
        database_session.query(TelegramIntegration)
        .filter(TelegramIntegration.company_id == company_id)
        .first()
    )


def _status_from_integration(integration: TelegramIntegration | None) -> TelegramStatusOut:
    # Built field-by-field (never `from_attributes=True` off the ORM object)
    # so bot_token can never leak into a response, even by accident.
    if integration is None:
        return TelegramStatusOut(is_connected=False, channel_id=None, created_at=None)
    return TelegramStatusOut(is_connected=True, channel_id=integration.channel_id, created_at=integration.created_at)


@router.get("/status", response_model=TelegramStatusOut)
def get_telegram_status(
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> TelegramStatusOut:
    return _status_from_integration(_get_integration(current_user.company_id, database_session))


@router.post("/connect", response_model=TelegramStatusOut, status_code=status.HTTP_201_CREATED)
def connect_telegram(
    connect_input: TelegramConnectInput,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> TelegramStatusOut:
    try:
        verify_response = httpx.get(f"{TELEGRAM_API_BASE_URL}/bot{connect_input.bot_token}/getMe", timeout=10.0)
        verify_data = verify_response.json()
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the Telegram API to verify the bot token",
        )

    if not verify_data.get("ok"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid bot token")

    integration = _get_integration(current_user.company_id, database_session)
    if integration is None:
        integration = TelegramIntegration(
            company_id=current_user.company_id,
            bot_token=connect_input.bot_token,
            channel_id=connect_input.channel_id,
        )
        database_session.add(integration)
    else:
        integration.bot_token = connect_input.bot_token
        integration.channel_id = connect_input.channel_id

    database_session.commit()
    database_session.refresh(integration)

    return _status_from_integration(integration)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_telegram(
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> None:
    integration = _get_integration(current_user.company_id, database_session)
    if integration is not None:
        database_session.delete(integration)
        database_session.commit()


@router.post("/publish", response_model=TelegramPublishOut)
def publish_to_telegram(
    publish_input: TelegramPublishInput,
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> TelegramPublishOut:
    integration = _get_integration(current_user.company_id, database_session)
    if integration is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Telegram is not connected")

    try:
        send_response = httpx.post(
            f"{TELEGRAM_API_BASE_URL}/bot{integration.bot_token}/sendMessage",
            json={"chat_id": integration.channel_id, "text": publish_input.text},
            timeout=10.0,
        )
        send_data = send_response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not reach the Telegram API")

    if not send_data.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=send_data.get("description", "Telegram API rejected the request"),
        )

    return TelegramPublishOut(message_id=send_data["result"]["message_id"])
