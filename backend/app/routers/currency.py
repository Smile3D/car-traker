from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_company_admin, require_company_member
from app.models.company import Company
from app.models.user import User
from app.schemas.currency import CompanyCurrencySettingsUpdate, CurrencyRateOut
from app.services.currency import get_auto_rate

router = APIRouter(tags=["currency"])


def _get_company(current_user: User, database_session: Session) -> Company:
    # require_company_member/require_company_admin already guarantee company_id is set.
    company = database_session.query(Company).filter(Company.id == current_user.company_id).first()
    assert company is not None
    return company


def _build_rate_response(company: Company, database_session: Session) -> CurrencyRateOut:
    auto_rate, auto_rate_updated_at = get_auto_rate(company, database_session)
    active_rate = company.manual_rate if company.rate_source == "manual" else auto_rate

    return CurrencyRateOut(
        auto_rate=auto_rate,
        auto_rate_updated_at=auto_rate_updated_at,
        manual_rate=company.manual_rate,
        active_source=company.rate_source,
        active_rate=active_rate,
    )


@router.get("/currency/rate", response_model=CurrencyRateOut)
def get_currency_rate(
    current_user: User = Depends(require_company_member),
    database_session: Session = Depends(get_db),
) -> CurrencyRateOut:
    return _build_rate_response(_get_company(current_user, database_session), database_session)


@router.patch("/company/currency-settings", response_model=CurrencyRateOut)
def update_currency_settings(
    settings_update: CompanyCurrencySettingsUpdate,
    current_user: User = Depends(require_company_admin),
    database_session: Session = Depends(get_db),
) -> CurrencyRateOut:
    company = _get_company(current_user, database_session)
    update_data = settings_update.model_dump(exclude_unset=True)

    company.rate_source = update_data["rate_source"]
    if "manual_rate" in update_data:
        company.manual_rate = update_data["manual_rate"]

    database_session.commit()
    database_session.refresh(company)

    return _build_rate_response(company, database_session)
