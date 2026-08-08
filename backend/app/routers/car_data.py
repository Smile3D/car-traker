from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user
from app.models.user import User
from app.services.car_data import CarDataUnavailableError, get_makes, get_models_for_make

router = APIRouter(prefix="/car-data", tags=["car-data"])


@router.get("/makes", response_model=list[str])
def list_makes(current_user: User = Depends(get_current_user)) -> list[str]:
    try:
        return get_makes()
    except CarDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get("/models", response_model=list[str])
def list_models(
    make: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    try:
        return get_models_for_make(make)
    except CarDataUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
