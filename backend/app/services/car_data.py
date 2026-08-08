import httpx

from app.services.car_data_cache import read_cached, write_cache

NHTSA_BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"
REQUEST_TIMEOUT_SECONDS = 10.0


class CarDataUnavailableError(Exception):
    pass


def get_makes() -> list[str]:
    cache_key = "makes"
    cached_makes = read_cached(cache_key)
    if cached_makes is not None:
        return cached_makes

    try:
        response = httpx.get(f"{NHTSA_BASE_URL}/getallmakes?format=json", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        results = response.json()["Results"]
    except (httpx.HTTPError, KeyError, ValueError) as request_error:
        raise CarDataUnavailableError("Could not reach the vehicle data provider") from request_error

    makes = sorted({result["Make_Name"].strip() for result in results if result.get("Make_Name")})
    write_cache(cache_key, makes)
    return makes


def get_models_for_make(make: str) -> list[str]:
    cache_key = f"models_{make}"
    cached_models = read_cached(cache_key)
    if cached_models is not None:
        return cached_models

    try:
        response = httpx.get(f"{NHTSA_BASE_URL}/GetModelsForMake/{make}?format=json", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        results = response.json()["Results"]
    except (httpx.HTTPError, KeyError, ValueError) as request_error:
        raise CarDataUnavailableError("Could not reach the vehicle data provider") from request_error

    models = sorted({result["Model_Name"].strip() for result in results if result.get("Model_Name")})
    write_cache(cache_key, models)
    return models
