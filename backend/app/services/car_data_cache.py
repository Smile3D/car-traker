import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path("cache/car_data")
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


def _cache_file_path(cache_key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_key = "".join(character if character.isalnum() else "_" for character in cache_key.lower())
    return CACHE_DIR / f"{safe_key}.json"


def read_cached(cache_key: str) -> Any | None:
    cache_path = _cache_file_path(cache_key)
    if not cache_path.is_file():
        return None

    if time.time() - cache_path.stat().st_mtime > CACHE_TTL_SECONDS:
        return None

    with cache_path.open("r", encoding="utf-8") as cache_file:
        return json.load(cache_file)


def write_cache(cache_key: str, data: Any) -> None:
    cache_path = _cache_file_path(cache_key)
    with cache_path.open("w", encoding="utf-8") as cache_file:
        json.dump(data, cache_file)
