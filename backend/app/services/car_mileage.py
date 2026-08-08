from app.models.car import Car


def sync_car_mileage(car: Car, mileage: int | None) -> None:
    if mileage is not None and mileage > int(car.mileage):
        car.mileage = str(mileage)
