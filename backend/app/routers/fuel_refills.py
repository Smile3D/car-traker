from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_car
from app.models.car import Car
from app.models.fuel_refill import FuelRefill
from app.schemas.fuel_refill import FuelRefillCreate, FuelRefillOut, FuelRefillUpdate
from app.services.car_mileage import sync_car_mileage

router = APIRouter(prefix="/cars/{car_id}/fuel-refills", tags=["fuel-refills"])


def _get_owned_fuel_refill_or_404(
    refill_id: int, car: Car, database_session: Session
) -> FuelRefill:
    fuel_refill = (
        database_session.query(FuelRefill)
        .filter(FuelRefill.id == refill_id, FuelRefill.car_id == car.id)
        .first()
    )
    if fuel_refill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuel refill not found")

    return fuel_refill


@router.post("", response_model=FuelRefillOut, status_code=status.HTTP_201_CREATED)
def create_fuel_refill(
    fuel_refill_create: FuelRefillCreate,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> FuelRefill:
    new_fuel_refill = FuelRefill(**fuel_refill_create.model_dump(), car_id=car.id)
    database_session.add(new_fuel_refill)

    sync_car_mileage(car, fuel_refill_create.mileage)

    database_session.commit()
    database_session.refresh(new_fuel_refill)

    return new_fuel_refill


@router.get("", response_model=list[FuelRefillOut])
def list_fuel_refills(
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> list[FuelRefill]:
    return (
        database_session.query(FuelRefill)
        .filter(FuelRefill.car_id == car.id)
        .order_by(FuelRefill.refill_date.asc())
        .all()
    )


@router.get("/{refill_id}", response_model=FuelRefillOut)
def read_fuel_refill(
    refill_id: int,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> FuelRefill:
    return _get_owned_fuel_refill_or_404(refill_id, car, database_session)


@router.patch("/{refill_id}", response_model=FuelRefillOut)
def update_fuel_refill(
    refill_id: int,
    fuel_refill_update: FuelRefillUpdate,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> FuelRefill:
    fuel_refill = _get_owned_fuel_refill_or_404(refill_id, car, database_session)

    update_data = fuel_refill_update.model_dump(exclude_unset=True)
    for field_name, field_value in update_data.items():
        setattr(fuel_refill, field_name, field_value)

    sync_car_mileage(car, fuel_refill.mileage)

    database_session.commit()
    database_session.refresh(fuel_refill)

    return fuel_refill


@router.delete("/{refill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel_refill(
    refill_id: int,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> None:
    fuel_refill = _get_owned_fuel_refill_or_404(refill_id, car, database_session)

    database_session.delete(fuel_refill)
    database_session.commit()
