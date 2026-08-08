#!/usr/bin/env python3
"""Re-seed test data on the Company/User CRM architecture, via the real API.

Everything that has an endpoint is created through the API (registration,
login, POST /listings with an atomic seller Client, POST /clients for buyers,
POST /listings/{id}/mark-sold) so it goes through the same validation and
business logic as the UI does. The ONE exception is attaching an employee
account to the owner's company: there is no invite-by-link endpoint yet
(that's a separate, future prompt), so this script does a single, narrow
SQL UPDATE for that step only — never a raw INSERT of business data. See the
"[NOTE]" printed at that step.

Usage:
    python3 backend/scripts/seed_company_data.py

Requires the `requests` package and a running docker-compose stack (backend
on localhost:8000, postgres reachable via `docker compose exec db psql`).
Re-running is safe for the owner/employee accounts (registration is skipped
if they already exist) but NOT idempotent for listings/clients — each run
adds another batch of 10 listings + 6 buyers.
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
OWNER_EMAIL = "aleksandrov+1@gmail.com"
OWNER_PASSWORD = "Test1234!"
EMPLOYEE_PASSWORD = "Test1234!"

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


def ensure_owner() -> tuple[str, dict]:
    log(f"--- Ensuring owner account exists: {OWNER_EMAIL} ---")

    register_response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD, "account_type": "business"},
    )
    if register_response.status_code == 201:
        log(f"[OK] Registered new business account {OWNER_EMAIL}")
    elif register_response.status_code == 400:
        log(f"[SKIP] Account already exists ({register_response.json().get('detail')})")
    else:
        log(f"[WARN] Unexpected /auth/register response {register_response.status_code}: {register_response.text}")

    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": OWNER_EMAIL, "password": OWNER_PASSWORD},
    )
    if login_response.status_code != 200:
        log(f"[FAIL] Could not log in as {OWNER_EMAIL}: {login_response.status_code} {login_response.text}")
        sys.exit(1)

    token = login_response.json()["access_token"]
    log("[OK] Logged in, JWT token acquired")

    me_response = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    me_response.raise_for_status()
    me = me_response.json()

    if me.get("role") != "owner" or me.get("company_id") is None:
        log(
            f"[FAIL] {OWNER_EMAIL} is not a company owner after ensure — "
            f"got role={me.get('role')!r} company_id={me.get('company_id')!r}"
        )
        sys.exit(1)

    log(f"[OK] Owner confirmed: company_id={me['company_id']} role={me['role']}")
    return token, me


EMPLOYEES = [
    {"email": "roman.konsultant.seed@example.com", "first_name": "Роман", "last_name": "Консультант"},
    {"email": "hanna.menedzher.seed@example.com", "first_name": "Ганна", "last_name": "Менеджер"},
    {"email": "ivan.prodavets.seed@example.com", "first_name": "Іван", "last_name": "Продавець"},
]


def ensure_employees(company_id: int) -> None:
    log(f"\n--- Ensuring {len(EMPLOYEES)} employee accounts exist ---")

    registered_emails: list[str] = []
    for employee in EMPLOYEES:
        label = f"{employee['first_name']} {employee['last_name']}"
        register_response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": employee["email"], "password": EMPLOYEE_PASSWORD, "account_type": "individual"},
        )
        if register_response.status_code == 201:
            log(f"[OK] Registered {label} <{employee['email']}>")
        elif register_response.status_code == 400:
            log(f"[SKIP] {label} <{employee['email']}> already exists")
        else:
            log(f"[FAIL] Register {employee['email']}: {register_response.status_code} {register_response.text}")
            continue
        registered_emails.append(employee["email"])

    log(
        "\n[NOTE] There is no invite-by-link endpoint yet to attach an existing user to a company "
        "as an employee (that flow is planned for a separate, future prompt). As a STOPGAP, this "
        "script runs a single targeted SQL UPDATE — not an INSERT of business data, just wiring "
        "company_id/role onto the accounts registered above through the real /auth/register call. "
        "Replace this step once the invite flow ships."
    )

    if not registered_emails:
        log("[FAIL] No employee accounts available to attach — aborting employee wiring")
        sys.exit(1)

    emails_sql_list = ", ".join(f"'{email}'" for email in registered_emails)
    sql = f"UPDATE users SET company_id = {company_id}, role = 'employee' WHERE email IN ({emails_sql_list});"
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", DB_SERVICE, "psql", "-U", DB_USER, "-d", DB_NAME, "-c", sql],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log(f"[FAIL] Attach employees to company: {result.stderr.strip()}")
        sys.exit(1)

    log(f"[OK] Attached {len(registered_emails)} accounts to company_id={company_id} as role=employee")


def fetch_employee_ids(token: str) -> dict[str, int]:
    response = requests.get(f"{BASE_URL}/employees", headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        log(f"[FAIL] GET /employees: {response.status_code} {response.text}")
        sys.exit(1)

    employees = response.json()
    by_email = {employee["email"]: employee["id"] for employee in employees}
    log(f"[OK] GET /employees -> {len(employees)} employees on record")
    return by_email


def set_employee_profile_names(token: str, employee_by_email: dict[str, int]) -> None:
    headers = {"Authorization": f"Bearer {token}"}

    log(f"\n--- Setting first_name/last_name for {len(EMPLOYEES)} employees via PATCH /employees/{{id}} ---")
    for employee in EMPLOYEES:
        employee_id = employee_by_email.get(employee["email"])
        if employee_id is None:
            log(f"[FAIL] {employee['email']}: not found in GET /employees, skipping name update")
            continue

        response = requests.patch(
            f"{BASE_URL}/employees/{employee_id}",
            json={"first_name": employee["first_name"], "last_name": employee["last_name"]},
            headers=headers,
        )
        if response.status_code != 200:
            log(f"[FAIL] PATCH /employees/{employee_id} (name): {response.status_code} {response.text}")
            continue

        updated = response.json()
        log(f"[OK] Set name for {employee['email']} -> {updated['first_name']} {updated['last_name']}")


def fetch_buyer_stage_ids(token: str) -> dict[str, int]:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/client-stages", params={"client_type": "buyer"}, headers=headers)
    if response.status_code != 200:
        log(f"[FAIL] GET /client-stages?client_type=buyer: {response.status_code} {response.text}")
        sys.exit(1)

    stages = response.json()
    by_name = {stage["name"]: stage["id"] for stage in stages}
    log(f"[OK] GET /client-stages?client_type=buyer -> {len(stages)} default stages ready")
    return by_name


# Each entry is the atomic POST /listings payload (listing + seller Client in
# one request, per the business-account create-listing flow) plus which
# already-registered employee (by email) should be the responsible one, and
# whether/how it should be marked sold afterwards via POST /mark-sold.
LISTINGS: list[dict] = [
    {
        "create": dict(
            brand="Toyota", model="Camry", year="2019", mileage="62000", vin="JT2BF22K1W0200001",
            seller_name="Олег Ковальчук", seller_phone="+380671234601", seller_email="oleg.kovalchuk.seed@example.com",
            body_type="sedan", transmission="automatic", engine="2.5L", fuel_type="petrol", color="silver",
            condition="used", condition_description="Один власник, повна сервісна історія",
            purchase_price=14000, additional_expenses=300, sale_price=17000,
            status="draft", date_added=shift_days(-85),
        ),
        "employee_email": None,
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Volkswagen", model="Passat", year="2020", mileage="45000", vin="WVWZZZ3CZLE200002",
            seller_name="Ірина Мельник", seller_phone="+380671234602",
            body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="white",
            condition="used",
            purchase_price=16000, additional_expenses=400, sale_price=18500,
            status="active", deadline_date=shift_days(30), date_added=shift_days(-70),
        ),
        "employee_email": "roman.konsultant.seed@example.com",
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="BMW", model="320i", year="2018", mileage="78000", vin="WBA8E9C50JK200003",
            seller_name="Андрій Бондаренко", seller_phone="+380671234603", seller_email="andriy.b.seed@example.com",
            body_type="sedan", transmission="automatic", engine="2.0L Turbo", fuel_type="petrol", color="black",
            condition="used", condition_description="Невелика подряпина на бампері",
            purchase_price=18000, additional_expenses=800, sale_price=21000,
            status="reserved", deadline_date=shift_days(15), date_added=shift_days(-60),
        ),
        "employee_email": None,
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Skoda", model="Octavia", year="2021", mileage="30000", vin="TMBJF7NE0M0200004",
            seller_name="Наталія Шевченко", seller_phone="+380671234604",
            body_type="liftback", transmission="manual", engine="1.6L", fuel_type="petrol", color="blue",
            condition="used",
            purchase_price=17500, additional_expenses=200, sale_price=19000,
            status="active", date_added=shift_days(-50),
        ),
        "employee_email": "hanna.menedzher.seed@example.com",
        "mark_sold_final_price": 18800,
    },
    {
        "create": dict(
            brand="Renault", model="Duster", year="2017", mileage="95000", vin="VF1HJD40H58200005",
            seller_name="Віктор Ткаченко", seller_phone="+380671234605",
            body_type="suv", transmission="manual", engine="1.6L", fuel_type="petrol", color="gray",
            condition="used", condition_description="Потребує заміни гальмівних колодок",
            purchase_price=9000, additional_expenses=250, sale_price=10200,
            status="active", date_added=shift_days(-42),
        ),
        "employee_email": None,
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Hyundai", model="Tucson", year="2022", mileage="15000", vin="KM8J3CA46NU200006",
            seller_name="Оксана Поліщук", seller_phone="+380671234606", seller_email="oksana.polishchuk.seed@example.com",
            body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="red",
            condition="used",
            purchase_price=22000, additional_expenses=500, sale_price=25500,
            status="active", date_added=shift_days(-35),
        ),
        "employee_email": "ivan.prodavets.seed@example.com",
        "mark_sold_final_price": 25200,
    },
    {
        "create": dict(
            brand="Ford", model="Focus", year="2016", mileage="110000", vin="WF0DXXWPMDGZ200007",
            seller_name="Максим Кравець", seller_phone="+380671234607",
            body_type="hatchback", transmission="manual", engine="1.6L", fuel_type="petrol", color="white",
            condition="used", condition_description="Пробіг підтверджений сервісною книжкою",
            purchase_price=7000, additional_expenses=300, sale_price=8200,
            status="draft", date_added=shift_days(-28),
        ),
        "employee_email": None,
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Kia", model="Sportage", year="2020", mileage="52000", vin="U5YFF4519LL200008",
            seller_name="Тетяна Гончаренко", seller_phone="+380671234608",
            body_type="suv", transmission="automatic", engine="2.0 CRDI", fuel_type="diesel", color="silver",
            condition="used",
            purchase_price=19000, additional_expenses=600, sale_price=22500, discount_amount=1500,
            status="active", date_added=shift_days(-20),
        ),
        "employee_email": "roman.konsultant.seed@example.com",
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Nissan", model="Qashqai", year="2019", mileage="68000", vin="SJNFAAJ11U0200009",
            seller_name="Сергій Литвин", seller_phone="+380671234609", seller_email="serhiy.lytvyn.seed@example.com",
            body_type="suv", transmission="automatic", engine="1.6 dCi", fuel_type="diesel", color="brown",
            condition="used", condition_description="Літня/зимова гума в комплекті",
            purchase_price=13500, additional_expenses=350, sale_price=15800, discount_amount=700,
            status="reserved", deadline_date=shift_days(20), date_added=shift_days(-12),
        ),
        "employee_email": "hanna.menedzher.seed@example.com",
        "mark_sold_final_price": None,
    },
    {
        "create": dict(
            brand="Mazda", model="6", year="2018", mileage="85000", vin="JM1GJ1V50J1200010",
            seller_name="Юлія Марченко", seller_phone="+380671234610",
            body_type="sedan", transmission="automatic", engine="2.5L", fuel_type="petrol", color="dark blue",
            condition="used", condition_description="Потребує косметичного ремонту салону",
            purchase_price=11000, additional_expenses=1200, sale_price=12500,
            status="active", date_added=shift_days(-5),
        ),
        "employee_email": "ivan.prodavets.seed@example.com",
        "mark_sold_final_price": 12300,
    },
]


def create_listings(token: str, employee_by_email: dict[str, int]) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    created: list[dict] = []

    log(f"\n--- Creating {len(LISTINGS)} listings (each atomic with its seller Client) ---")
    for entry in LISTINGS:
        payload = dict(entry["create"])
        label = f"{payload['brand']} {payload['model']} {payload['year']}"

        employee_email = entry["employee_email"]
        if employee_email is not None:
            employee_id = employee_by_email.get(employee_email)
            if employee_id is None:
                log(f"[FAIL] '{label}': unknown employee email {employee_email!r}, skipping employee_id")
            else:
                payload["employee_id"] = employee_id

        response = requests.post(f"{BASE_URL}/listings", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create '{label}': {response.status_code} {response.text}")
            continue

        listing = response.json()
        # ListingOut never carries employee_id (it lives on the seller
        # Client, not the Listing) — report what we actually sent instead.
        employee_note = f" seller_employee_id={payload['employee_id']}" if "employee_id" in payload else ""
        log(f"[OK] Created '{label}' -> id={listing['id']} status={listing['status']} company_id={listing['company_id']}{employee_note}")
        created.append({
            "id": listing["id"],
            "label": label,
            "company_id": listing["company_id"],
            "mark_sold_final_price": entry["mark_sold_final_price"],
        })

    return created


def mark_listings_sold(token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    sold_count = 0

    log("\n--- Marking listings as sold via POST /listings/{id}/mark-sold ---")
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


# Each buyer targets one of the 10 listings above by its 1-based index in
# LISTINGS, lands in a distinct default buyer stage (exercising all 6 of
# them), and some get a responsible employee assigned via a follow-up PATCH
# (ClientCreate has no employee_id field — only ClientUpdate does).
BUYERS: list[dict] = [
    {
        "listing_index": 0,
        "name": "Дмитро Савчук", "phone": "+380671234701",
        "stage_name": "Лід",
        "employee_email": None,
    },
    {
        "listing_index": 1,
        "name": "Олена Кравчук", "phone": "+380671234702", "email": "olena.kravchuk.seed@example.com",
        "stage_name": "Перегляд авто",
        "employee_email": "roman.konsultant.seed@example.com",
    },
    {
        "listing_index": 2,
        "name": "Павло Іванов", "phone": "+380671234703",
        "stage_name": "Переговори",
        "employee_email": None,
    },
    {
        "listing_index": 4,
        "name": "Марина Бойко", "phone": "+380671234704",
        "stage_name": "Резерв",
        "employee_email": "hanna.menedzher.seed@example.com",
    },
    {
        "listing_index": 6,
        "name": "Артем Сидоренко", "phone": "+380671234705",
        "stage_name": "Угода закрита",
        "employee_email": None,
    },
    {
        "listing_index": 7,
        "name": "Христина Лисенко", "phone": "+380671234706", "email": "khrystyna.lysenko.seed@example.com",
        "stage_name": "Відмова",
        "employee_email": "ivan.prodavets.seed@example.com",
    },
]


def create_buyers(
    token: str,
    created_listings: list[dict],
    stage_by_name: dict[str, int],
    employee_by_email: dict[str, int],
) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    created: list[dict] = []

    log(f"\n--- Creating {len(BUYERS)} buyer clients ---")
    for buyer in BUYERS:
        if buyer["listing_index"] >= len(created_listings):
            log(f"[FAIL] Buyer '{buyer['name']}': listing index {buyer['listing_index']} was not created, skipping")
            continue

        listing = created_listings[buyer["listing_index"]]
        stage_id = stage_by_name.get(buyer["stage_name"])
        if stage_id is None:
            log(f"[FAIL] Buyer '{buyer['name']}': unknown buyer stage {buyer['stage_name']!r}, skipping")
            continue

        payload = {
            "listing_id": listing["id"],
            "client_type": "buyer",
            "name": buyer["name"],
            "phone": buyer["phone"],
            "stage_id": stage_id,
        }
        if "email" in buyer:
            payload["email"] = buyer["email"]

        response = requests.post(f"{BASE_URL}/clients", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create buyer '{buyer['name']}': {response.status_code} {response.text}")
            continue

        client = response.json()
        log(
            f"[OK] Created buyer '{buyer['name']}' -> id={client['id']} listing='{listing['label']}' "
            f"stage='{buyer['stage_name']}' company_id={client['company_id']}"
        )
        created.append({"id": client["id"], "name": buyer["name"], "employee_email": buyer["employee_email"]})

        if buyer["employee_email"] is not None:
            employee_id = employee_by_email.get(buyer["employee_email"])
            if employee_id is None:
                log(f"[FAIL] Buyer '{buyer['name']}': unknown employee email {buyer['employee_email']!r}")
                continue

            patch_response = requests.patch(
                f"{BASE_URL}/clients/{client['id']}",
                json={"employee_id": employee_id},
                headers=headers,
            )
            if patch_response.status_code != 200:
                log(f"[FAIL] Assign employee to buyer '{buyer['name']}': {patch_response.status_code} {patch_response.text}")
                continue

            log(f"[OK] Assigned employee_id={employee_id} to buyer '{buyer['name']}' (id={client['id']})")

    return created


def verify_summary(token: str, company_id: int, expected_listings: int, expected_buyers: int, expected_employees: int) -> None:
    headers = {"Authorization": f"Bearer {token}"}

    log("\n--- Verifying via GET /listings, /clients, /employees ---")

    listings_response = requests.get(f"{BASE_URL}/listings", headers=headers)
    listings_response.raise_for_status()
    listings = listings_response.json()
    listings_wrong_company = [item for item in listings if item["company_id"] != company_id]

    clients_response = requests.get(f"{BASE_URL}/clients", headers=headers)
    clients_response.raise_for_status()
    clients = clients_response.json()
    sellers = [item for item in clients if item["client_type"] == "seller"]
    buyers = [item for item in clients if item["client_type"] == "buyer"]
    clients_wrong_company = [item for item in clients if item["company_id"] != company_id]

    employees_response = requests.get(f"{BASE_URL}/employees", headers=headers)
    employees_response.raise_for_status()
    employees = employees_response.json()

    log(f"[OK] GET /listings -> {len(listings)} total, {len(listings_wrong_company)} with wrong company_id")
    log(f"[OK] GET /clients  -> {len(sellers)} sellers, {len(buyers)} buyers, {len(clients_wrong_company)} with wrong company_id")
    log(f"[OK] GET /employees -> {len(employees)} total (expected at least {expected_employees})")

    log("\n=== SUMMARY ===")
    log(f"Owner company_id:            {company_id}")
    log(f"Employees on record:         {len(employees)} (this run attached {expected_employees})")
    log(f"Listings created this run:   {expected_listings} / {len(LISTINGS)}")
    log(f"Seller clients (total):      {len(sellers)} (one per listing, atomic with creation)")
    log(f"Buyer clients created:       {expected_buyers} / {len(BUYERS)}")
    log(f"Total listings in company:   {len(listings)}")
    log(f"Total clients in company:    {len(clients)}")
    log(f"Listings with wrong company: {len(listings_wrong_company)}")
    log(f"Clients with wrong company:  {len(clients_wrong_company)}")

    if listings_wrong_company or clients_wrong_company:
        log("[FAIL] Some records do not belong to the owner's company_id — investigate before trusting the UI view")
    else:
        log("[OK] Every listing and client fetched belongs to the owner's company_id")


def main() -> None:
    token, me = ensure_owner()
    company_id = me["company_id"]

    ensure_employees(company_id)
    employee_by_email = fetch_employee_ids(token)
    set_employee_profile_names(token, employee_by_email)
    stage_by_name = fetch_buyer_stage_ids(token)

    created_listings = create_listings(token, employee_by_email)
    sold_count = mark_listings_sold(token, created_listings)
    created_buyers = create_buyers(token, created_listings, stage_by_name, employee_by_email)

    verify_summary(
        token,
        company_id,
        expected_listings=len(created_listings),
        expected_buyers=len(created_buyers),
        expected_employees=len(employee_by_email),
    )

    log(f"\nMarked as sold: {sold_count}")
    log(f"Created listing ids: {[item['id'] for item in created_listings]}")
    log(f"Created buyer ids:   {[item['id'] for item in created_buyers]}")


if __name__ == "__main__":
    main()
