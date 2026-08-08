#!/usr/bin/env python3
"""Seed a business account with 10 diverse Listing records for manual UI/dashboard testing.

Usage:
    python3 backend/scripts/seed_business_listings.py

Requires the `requests` package and a running docker-compose stack (backend on
localhost:8000, postgres reachable via `docker compose exec db psql`).
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
EMAIL = "aleksandrov+1@gmail.com"
PASSWORD = "Test1234!"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_SERVICE = "db"
DB_USER = "postgres"
DB_NAME = "car_garage_tracker"

TODAY = date.today()


def log(message: str) -> None:
    print(message, flush=True)


def shift_days(days: int) -> str:
    """ISO date `days` from today. Negative = past, positive = future."""
    return (TODAY + timedelta(days=days)).isoformat()


def get_auth_token() -> str:
    log(f"--- Ensuring business account exists: {EMAIL} ---")

    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "account_type": "business"},
    )
    if register_response.status_code == 201:
        log(f"[OK] Registered new business account {EMAIL}")
    elif register_response.status_code == 400:
        log(f"[SKIP] Account already exists ({register_response.json().get('detail')})")
    else:
        log(f"[WARN] Unexpected /auth/register response {register_response.status_code}: {register_response.text}")

    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    if login_response.status_code != 200:
        log(f"[FAIL] Could not log in as {EMAIL}: {login_response.status_code} {login_response.text}")
        sys.exit(1)

    token = login_response.json()["access_token"]
    log("[OK] Logged in, JWT token acquired")
    return token


# Each entry: the /listings creation payload, an optional mark-sold final price
# (None = leave the status set in the payload as-is), and an optional backdated
# date_added (None = keep today's date, applied automatically by the API).
LISTINGS: list[dict] = [
    {
        "create": dict(
            brand="Toyota", model="Camry", year="2019", mileage="62000", vin="JT2BF22K1W0100001",
            seller_name="Олег Ковальчук", seller_phone="+380671234501", seller_email="oleg.kovalchuk@example.com",
            body_type="sedan", transmission="automatic", engine="2.5L", fuel_type="petrol", color="silver",
            condition="used", condition_description="Один власник, повна сервісна історія",
            purchase_price=14000, additional_expenses=300, sale_price=17000,
            status="active",
        ),
        "mark_sold_final_price": 16800,
        "backdate": shift_days(-78),
    },
    {
        "create": dict(
            brand="Volkswagen", model="Passat", year="2020", mileage="45000", vin="WVWZZZ3CZLE100002",
            seller_name="Ірина Мельник", seller_phone="+380671234502",
            body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="white",
            condition="used",
            purchase_price=16000, additional_expenses=400, sale_price=18500,
            status="active", deadline_date=shift_days(30),
        ),
        "mark_sold_final_price": None,
        "backdate": shift_days(-55),
    },
    {
        "create": dict(
            brand="BMW", model="320i", year="2018", mileage="78000", vin="WBA8E9C50JK100003",
            seller_name="Андрій Бондаренко", seller_phone="+380671234503", seller_email="andriy.b@example.com",
            body_type="sedan", transmission="automatic", engine="2.0L Turbo", fuel_type="petrol", color="black",
            condition="used", condition_description="Невелика подряпина на бампері",
            purchase_price=18000, additional_expenses=800, sale_price=21000,
            status="active",
        ),
        "mark_sold_final_price": 21000,
        "backdate": shift_days(-68),
    },
    {
        "create": dict(
            brand="Skoda", model="Octavia", year="2021", mileage="30000", vin="TMBJF7NE0M0100004",
            seller_name="Наталія Шевченко", seller_phone="+380671234504",
            body_type="liftback", transmission="manual", engine="1.6L", fuel_type="petrol", color="blue",
            condition="used",
            purchase_price=17500, additional_expenses=200, sale_price=19000,
            status="draft", deadline_date=shift_days(10),
        ),
        "mark_sold_final_price": None,
        "backdate": None,
    },
    {
        "create": dict(
            brand="Renault", model="Duster", year="2017", mileage="95000", vin="VF1HJD40H58100005",
            seller_name="Віктор Ткаченко", seller_phone="+380671234505",
            body_type="suv", transmission="manual", engine="1.6L", fuel_type="petrol", color="gray",
            condition="used", condition_description="Потребує заміни гальмівних колодок",
            purchase_price=9000, additional_expenses=250, sale_price=10200,
            status="active",
        ),
        "mark_sold_final_price": 10000,
        "backdate": shift_days(-42),
    },
    {
        "create": dict(
            brand="Hyundai", model="Tucson", year="2022", mileage="15000", vin="KM8J3CA46NU100006",
            seller_name="Оксана Поліщук", seller_phone="+380671234506", seller_email="oksana.polishchuk@example.com",
            body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="red",
            condition="used",
            purchase_price=22000, additional_expenses=500, sale_price=25500,
            status="active", deadline_date=shift_days(-15),
        ),
        "mark_sold_final_price": None,
        "backdate": shift_days(-32),
    },
    {
        "create": dict(
            brand="Ford", model="Focus", year="2016", mileage="110000", vin="WF0DXXWPMDGZ100007",
            seller_name="Максим Кравець", seller_phone="+380671234507",
            body_type="hatchback", transmission="manual", engine="1.6L", fuel_type="petrol", color="white",
            condition="used", condition_description="Пробіг підтверджений сервісною книжкою",
            purchase_price=7000, additional_expenses=300, sale_price=8200,
            status="reserved", deadline_date=shift_days(-5),
        ),
        "mark_sold_final_price": None,
        "backdate": None,
    },
    {
        "create": dict(
            brand="Kia", model="Sportage", year="2020", mileage="52000", vin="U5YFF4519LL100008",
            seller_name="Тетяна Гончаренко", seller_phone="+380671234508",
            body_type="suv", transmission="automatic", engine="2.0 CRDI", fuel_type="diesel", color="silver",
            condition="used",
            purchase_price=19000, additional_expenses=600, sale_price=22500,
            discount_amount=1500, original_price=24000,
            status="active",
        ),
        "mark_sold_final_price": 23000,
        "backdate": shift_days(-83),
    },
    {
        "create": dict(
            brand="Nissan", model="Qashqai", year="2019", mileage="68000", vin="SJNFAAJ11U0100009",
            seller_name="Сергій Литвин", seller_phone="+380671234509", seller_email="serhiy.lytvyn@example.com",
            body_type="suv", transmission="automatic", engine="1.6 dCi", fuel_type="diesel", color="brown",
            condition="used", condition_description="Літня/зимова гума в комплекті",
            purchase_price=13500, additional_expenses=350, sale_price=15800,
            discount_amount=700, original_price=16500,
            status="reserved", deadline_date=shift_days(20),
        ),
        "mark_sold_final_price": None,
        "backdate": shift_days(-26),
    },
    {
        "create": dict(
            brand="Mazda", model="6", year="2018", mileage="85000", vin="JM1GJ1V50J1100010",
            seller_name="Юлія Марченко", seller_phone="+380671234510",
            body_type="sedan", transmission="automatic", engine="2.5L", fuel_type="petrol", color="dark blue",
            condition="used", condition_description="Потребує косметичного ремонту салону",
            purchase_price=11000, additional_expenses=1200, sale_price=12500,
            status="draft", deadline_date=shift_days(-30),
        ),
        "mark_sold_final_price": None,
        "backdate": None,
    },
]


def create_listings(token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    created: list[dict] = []

    log(f"\n--- Creating {len(LISTINGS)} listings ---")
    for entry in LISTINGS:
        payload = entry["create"]
        label = f"{payload['brand']} {payload['model']} {payload['year']}"

        response = requests.post(f"{BASE_URL}/listings", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create '{label}': {response.status_code} {response.text}")
            continue

        listing = response.json()
        log(f"[OK] Created '{label}' -> id={listing['id']} status={listing['status']}")
        created.append({
            "id": listing["id"],
            "label": label,
            "mark_sold_final_price": entry["mark_sold_final_price"],
            "backdate": entry["backdate"],
        })

    return created


def mark_listings_sold(token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    sold_count = 0

    log("\n--- Marking listings as sold ---")
    for item in created:
        if item["mark_sold_final_price"] is None:
            continue

        response = requests.post(
            f"{BASE_URL}/listings/{item['id']}/mark-sold",
            json={"final_sale_price": item["mark_sold_final_price"]},
            headers=headers,
        )
        if response.status_code != 200:
            log(f"[FAIL] mark-sold '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        listing = response.json()
        log(
            f"[OK] Sold '{item['label']}' (id={item['id']}) -> "
            f"sale_price={listing['sale_price']} date_sold={listing['date_sold']} "
            f"net_profit={listing['net_profit']}"
        )
        sold_count += 1

    return sold_count


def backdate_date_added(created: list[dict]) -> int:
    to_backdate = [item for item in created if item["backdate"] is not None]

    log(f"\n--- Backdating date_added for {len(to_backdate)} listings via psql ---")
    backdated_count = 0

    for item in to_backdate:
        sql = f"UPDATE listings SET date_added = '{item['backdate']}' WHERE id = {item['id']};"
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", DB_SERVICE, "psql", "-U", DB_USER, "-d", DB_NAME, "-c", sql],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            log(f"[FAIL] Backdate '{item['label']}' (id={item['id']}): {result.stderr.strip()}")
            continue

        log(f"[OK] Backdated '{item['label']}' (id={item['id']}) -> date_added={item['backdate']}")
        backdated_count += 1

    return backdated_count


def main() -> None:
    token = get_auth_token()
    created = create_listings(token)
    sold_count = mark_listings_sold(token, created)
    backdated_count = backdate_date_added(created)

    log("\n=== SUMMARY ===")
    log(f"Listings created:   {len(created)} / {len(LISTINGS)}")
    log(f"Marked as sold:     {sold_count}")
    log(f"date_added updated: {backdated_count}")
    log(f"Created listing ids: {[item['id'] for item in created]}")


if __name__ == "__main__":
    main()
