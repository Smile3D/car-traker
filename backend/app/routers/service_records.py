from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_owned_car
from app.models.car import Car
from app.models.service_record import ServiceRecord
from app.models.service_record_item import ServiceRecordItem
from app.schemas.service_record import ServiceRecordCreate, ServiceRecordOut, ServiceRecordUpdate
from app.services.car_mileage import sync_car_mileage

router = APIRouter(prefix="/cars/{car_id}/service-records", tags=["service-records"])


def _get_owned_service_record_or_404(
    record_id: int, car: Car, database_session: Session
) -> ServiceRecord:
    service_record = (
        database_session.query(ServiceRecord)
        .filter(ServiceRecord.id == record_id, ServiceRecord.car_id == car.id)
        .first()
    )
    if service_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service record not found")

    return service_record


@router.post("", response_model=ServiceRecordOut, status_code=status.HTTP_201_CREATED)
def create_service_record(
    service_record_create: ServiceRecordCreate,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> ServiceRecord:
    new_service_record = ServiceRecord(
        record_type=service_record_create.record_type,
        service_date=service_record_create.service_date,
        mileage=service_record_create.mileage,
        car_id=car.id,
        items=[
            ServiceRecordItem(name=item.name, price=item.price)
            for item in service_record_create.items
        ],
    )
    database_session.add(new_service_record)

    sync_car_mileage(car, service_record_create.mileage)

    database_session.commit()
    database_session.refresh(new_service_record)

    return new_service_record


@router.get("", response_model=list[ServiceRecordOut])
def list_service_records(
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> list[ServiceRecord]:
    return (
        database_session.query(ServiceRecord)
        .filter(ServiceRecord.car_id == car.id)
        .order_by(ServiceRecord.mileage.asc())
        .all()
    )


@router.patch("/{record_id}", response_model=ServiceRecordOut)
def update_service_record(
    record_id: int,
    service_record_update: ServiceRecordUpdate,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> ServiceRecord:
    service_record = _get_owned_service_record_or_404(record_id, car, database_session)

    update_data = service_record_update.model_dump(exclude_unset=True, exclude={"items"})
    for field_name, field_value in update_data.items():
        setattr(service_record, field_name, field_value)

    if service_record_update.items is not None:
        service_record.items = [
            ServiceRecordItem(name=item.name, price=item.price)
            for item in service_record_update.items
        ]

    sync_car_mileage(car, service_record.mileage)

    database_session.commit()
    database_session.refresh(service_record)

    return service_record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_record(
    record_id: int,
    car: Car = Depends(get_owned_car),
    database_session: Session = Depends(get_db),
) -> None:
    service_record = _get_owned_service_record_or_404(record_id, car, database_session)

    database_session.delete(service_record)
    database_session.commit()
