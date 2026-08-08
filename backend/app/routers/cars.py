from pathlib import Path

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_owned_car
from app.models.car import Car
from app.models.user import User
from app.schemas.car import CarCreate, CarOut, CarUpdate

router = APIRouter(prefix="/cars", tags=["cars"])


@router.post("", response_model=CarOut, status_code=status.HTTP_201_CREATED)
def create_car(
    car_create: CarCreate,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> Car:
    new_car = Car(**car_create.model_dump(), user_id=current_user.id)
    database_session.add(new_car)
    database_session.commit()
    database_session.refresh(new_car)

    return new_car


@router.get("", response_model=list[CarOut])
def list_cars(
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> list[Car]:
    return database_session.query(Car).filter(Car.user_id == current_user.id).all()


@router.get("/{car_id}", response_model=CarOut)
def read_car(car: Car = Depends(get_owned_car)) -> Car:
    return car


@router.patch("/{car_id}", response_model=CarOut)
def update_car(
    car_update: CarUpdate,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> Car:
    for field_name, field_value in car_update.model_dump(exclude_unset=True).items():
        setattr(car, field_name, field_value)

    database_session.commit()
    database_session.refresh(car)

    return car


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_car(
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> None:
    for receipt in car.receipts:
        (Path(settings.upload_dir) / receipt.file_path).unlink(missing_ok=True)

    database_session.delete(car)
    database_session.commit()
