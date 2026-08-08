#!/usr/bin/env python3
"""Seed a full demo company (owner + employees + listings across every status +
buyers) for manual UI testing, so the app never needs to be re-populated by
hand after a DB reset.

WHY THROUGH THE REAL API, NOT DIRECT INSERTS: everything that has an
endpoint is created by calling it — POST /auth/register, POST /positions,
POST /employees/invites + POST /auth/register(invite_token=...), POST
/listings, POST /listings/{id}/mark-sold, PATCH /listings/{id} (removed),
POST /clients — so it goes through the exact same business logic the UI
does. This matters concretely: _record_deal_history() is what fills in
net_profit/purchase_price/additional_expenses/date_added on DealHistory, and
skipping it (e.g. a raw bulk INSERT) is exactly how this app ended up with
NULL net_profit/date_added on old rows in the first place (see the archive
auto-cleanup and Dashboard/Analytics DealHistory-source fixes earlier in
this project's history). A seed script that bypasses business logic just
recreates that same bug on day one.

THE ONE DELIBERATE EXCEPTION: mark_listing_sold() always sets
date_sold = today() — there's no API parameter to backdate a sale (nor
should there be one for a live UI action). To get realistic historical
spread for charts like AverageDaysToSellChart, this script calls the real
mark-sold endpoint first (so every computed/snapshot field is correct), and
only then patches date_sold/archived_at/DealHistory.date_closed directly via
SQLAlchemy for entries that request a backdate. This is a narrow, explicitly
logged exception — not a way to skip business logic, just to move its
already-correct output to a different date. Direct DB access is available
here because this script is meant to run *inside* the backend container
(see USAGE), where app.database's engine already points at the right
Postgres instance.

USAGE (from the repo root, backend container already running):
    docker compose exec backend python -m scripts.seed_demo_data
    docker compose exec backend python -m scripts.seed_demo_data --reset

Re-running with no flags when seed data already exists is a deliberate
hard failure (not a silent duplicate-adding no-op) — use --reset first.
--reset only deletes rows belonging to the seed company (matched by the
owner's fixed email below); it never touches any other company's data.
"""

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.client_stage import ClientStage  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.deal_history import DealHistory  # noqa: E402
from app.models.employee_invite import EmployeeInvite  # noqa: E402
from app.models.listing import Listing  # noqa: E402
from app.models.position import Position  # noqa: E402
from app.models.telegram_integration import TelegramIntegration  # noqa: E402
from app.models.user import User  # noqa: E402

BASE_URL = "http://localhost:8000"

OWNER_EMAIL = "demo.owner.demoseed@example.com"
OWNER_PASSWORD = "DemoSeed123!"
EMPLOYEE_PASSWORD = "DemoSeed123!"

TODAY = date.today()


def log(message: str) -> None:
    print(message, flush=True)


def shift_days(days: int) -> str:
    """ISO date `days` from today. Negative = past, positive = future."""
    return (TODAY + timedelta(days=days)).isoformat()


# ============================================================================
# --reset: delete only this seed company's data (never another company's)
# ============================================================================

def reset_seed_data() -> None:
    session = SessionLocal()
    try:
        owner = session.query(User).filter(User.email == OWNER_EMAIL).first()
        if owner is None or owner.company_id is None:
            log(f"[SKIP] No seed company found for {OWNER_EMAIL} — nothing to reset")
            return

        company_id = owner.company_id
        log(f"--- Resetting seed company_id={company_id} (owner={OWNER_EMAIL}) ---")

        deleted_listings = session.query(Listing).filter(Listing.company_id == company_id).delete(
            synchronize_session=False
        )
        # Client/ListingPhoto rows cascade at the DB level (ON DELETE CASCADE
        # on their listing_id FK) — nothing further to do for them here.
        log(f"[OK] Deleted {deleted_listings} listing(s) (Client/ListingPhoto rows cascaded)")

        deleted_deal_history = session.query(DealHistory).filter(DealHistory.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_deal_history} deal_history row(s)")

        deleted_invites = session.query(EmployeeInvite).filter(EmployeeInvite.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_invites} employee invite(s)")

        deleted_client_stages = session.query(ClientStage).filter(ClientStage.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_client_stages} client stage(s)")

        deleted_telegram = session.query(TelegramIntegration).filter(
            TelegramIntegration.company_id == company_id
        ).delete(synchronize_session=False)
        log(f"[OK] Deleted {deleted_telegram} telegram integration row(s)")

        # Employees must be deleted before Positions — User.position_id has a
        # live FK into positions.id, so a Position row can't go while an
        # employee still references it.
        employee_ids = [
            row.id for row in session.query(User.id).filter(User.company_id == company_id, User.role == "employee")
        ]
        session.query(User).filter(User.company_id == company_id, User.role == "employee").delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {len(employee_ids)} employee account(s)")

        deleted_positions = session.query(Position).filter(Position.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_positions} position(s)")

        # Break the User<->Company circular FK (Company.owner_user_id -> User,
        # User.company_id -> Company) before either row can be deleted.
        owner.company_id = None
        owner.role = None
        session.flush()

        session.query(Company).filter(Company.id == company_id).delete(synchronize_session=False)
        log(f"[OK] Deleted company_id={company_id}")

        session.delete(owner)
        log(f"[OK] Deleted owner account {OWNER_EMAIL}")

        session.commit()
        log("[OK] Reset complete")
    finally:
        session.close()


# ============================================================================
# Owner + positions + employees, via the real API
# ============================================================================

def ensure_owner_does_not_already_exist(client: httpx.Client) -> None:
    login_response = client.post("/auth/login", data={"username": OWNER_EMAIL, "password": OWNER_PASSWORD})
    if login_response.status_code == 200:
        log(
            f"[FAIL] Seed data already exists for {OWNER_EMAIL} — refusing to add duplicates.\n"
            f"       Run with --reset first, then re-run this script with no flags."
        )
        sys.exit(1)


def register_owner(client: httpx.Client) -> str:
    log(f"--- Registering owner account: {OWNER_EMAIL} ---")
    response = client.post(
        "/auth/register",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD, "account_type": "business"},
    )
    if response.status_code != 201:
        log(f"[FAIL] Register owner: {response.status_code} {response.text}")
        sys.exit(1)

    login_response = client.post("/auth/login", data={"username": OWNER_EMAIL, "password": OWNER_PASSWORD})
    login_response.raise_for_status()
    token = login_response.json()["access_token"]
    log("[OK] Owner registered and logged in")
    return token


POSITIONS = ["Менеджер з продажу", "Консультант", "Керівник відділу"]


def create_positions(client: httpx.Client, token: str) -> dict[str, int]:
    headers = {"Authorization": f"Bearer {token}"}
    position_id_by_name: dict[str, int] = {}

    log(f"\n--- Creating {len(POSITIONS)} positions ---")
    for name in POSITIONS:
        response = client.post("/positions", json={"name": name}, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create position '{name}': {response.status_code} {response.text}")
            continue
        position = response.json()
        position_id_by_name[name] = position["id"]
        log(f"[OK] Created position '{name}' -> id={position['id']}")

    return position_id_by_name


EMPLOYEES = [
    {"email": "roman.demoseed@example.com", "first_name": "Роман", "last_name": "Консультант", "position": "Консультант"},
    {"email": "hanna.demoseed@example.com", "first_name": "Ганна", "last_name": "Менеджер", "position": "Менеджер з продажу"},
    {"email": "ivan.demoseed@example.com", "first_name": "Іван", "last_name": "Керівник", "position": "Керівник відділу"},
]


def create_employees(client: httpx.Client, token: str, position_id_by_name: dict[str, int]) -> dict[str, int]:
    owner_headers = {"Authorization": f"Bearer {token}"}
    employee_id_by_email: dict[str, int] = {}

    log(f"\n--- Inviting and registering {len(EMPLOYEES)} employees (real invite-link flow) ---")
    for employee in EMPLOYEES:
        label = f"{employee['first_name']} {employee['last_name']}"
        position_id = position_id_by_name.get(employee["position"])

        invite_response = client.post(
            "/employees/invites",
            json={"email": employee["email"], "position_id": position_id},
            headers=owner_headers,
        )
        if invite_response.status_code != 201:
            log(f"[FAIL] Create invite for {label}: {invite_response.status_code} {invite_response.text}")
            continue
        invite_token = invite_response.json()["token"]

        register_response = client.post(
            "/auth/register",
            json={"email": employee["email"], "password": EMPLOYEE_PASSWORD, "invite_token": invite_token},
        )
        if register_response.status_code != 201:
            log(f"[FAIL] Register {label} via invite: {register_response.status_code} {register_response.text}")
            continue

        employee_user = register_response.json()
        employee_id = employee_user["id"]
        employee_id_by_email[employee["email"]] = employee_id
        log(f"[OK] {label} <{employee['email']}> joined via invite -> employee_id={employee_id}")

        name_response = client.patch(
            f"/employees/{employee_id}",
            json={"first_name": employee["first_name"], "last_name": employee["last_name"]},
            headers=owner_headers,
        )
        if name_response.status_code != 200:
            log(f"[FAIL] Set name for {label}: {name_response.status_code} {name_response.text}")

    return employee_id_by_email


# ============================================================================
# Listings across every status, via POST /listings (+ mark-sold / removed)
# ============================================================================

# backdate_sold_days: None = leave the sale dated "today" (as mark-sold
# naturally sets it). A number = how many days in the past this sale should
# APPEAR to have closed — applied via the one deliberate direct-DB patch
# described in the module docstring, after the real mark-sold call.
LISTINGS: list[dict] = [
    # --- draft (3) ---
    {
        "create": dict(
            brand="Toyota", model="Corolla", year="2018", mileage="88000", vin="JTDBR32E730300001",
            seller_name="Богдан Гриценко", seller_phone="+380671330001",
            body_type="sedan", transmission="automatic", engine="1.8L", fuel_type="petrol", color="silver",
            condition="used", purchase_price=9500, additional_expenses=250, sale_price=11800,
            status="draft", date_added=shift_days(-6),
        ),
        "employee_email": None, "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    {
        "create": dict(
            brand="Volkswagen", model="Golf", year="2017", mileage="102000", vin="WVWZZZ1KZAW300002",
            seller_name="Марія Дяченко", seller_phone="+380671330002",
            body_type="hatchback", transmission="manual", engine="1.6 TDI", fuel_type="diesel", color="red",
            condition="used", condition_description="Потребує заміни зчеплення",
            purchase_price=7200, additional_expenses=600, sale_price=8900,
            status="draft", date_added=shift_days(-3),
        ),
        "employee_email": "roman.demoseed@example.com", "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    {
        "create": dict(
            brand="Peugeot", model="308", year="2019", mileage="55000", vin="VF3LCBHZ6JS300003",
            seller_name="Ігор Савчук", seller_phone="+380671330003",
            body_type="hatchback", transmission="automatic", engine="1.6L", fuel_type="petrol", color="white",
            condition="used", purchase_price=10800, additional_expenses=150, sale_price=12900,
            status="draft", date_added=shift_days(-1),
        ),
        "employee_email": None, "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    # --- active (3) ---
    {
        "create": dict(
            brand="Honda", model="Civic", year="2020", mileage="34000", vin="2HGFC2F59LH300004",
            seller_name="Олена Бабич", seller_phone="+380671330004", seller_email="olena.babych.demoseed@example.com",
            body_type="sedan", transmission="automatic", engine="1.5 Turbo", fuel_type="petrol", color="blue",
            condition="used", purchase_price=15200, additional_expenses=300, sale_price=18500,
            status="active", deadline_date=shift_days(-4), date_added=shift_days(-40),
        ),
        "employee_email": "hanna.demoseed@example.com", "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    {
        "create": dict(
            brand="Mazda", model="CX-5", year="2021", mileage="21000", vin="JM3KFBDM5M0300005",
            seller_name="Тарас Мороз", seller_phone="+380671330005",
            body_type="suv", transmission="automatic", engine="2.5L", fuel_type="petrol", color="gray",
            condition="used", purchase_price=21500, additional_expenses=400, sale_price=25800,
            status="active", deadline_date=shift_days(25), date_added=shift_days(-15),
        ),
        "employee_email": None, "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    {
        "create": dict(
            brand="Skoda", model="Superb", year="2018", mileage="91000", vin="TMBAJ7NP5J0300006",
            seller_name="Юрій Романенко", seller_phone="+380671330006",
            body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="black",
            condition="used", condition_description="Комплектація Style, шкіряний салон",
            purchase_price=16800, additional_expenses=550, sale_price=19900,
            status="active", date_added=shift_days(-9),
        ),
        "employee_email": "ivan.demoseed@example.com", "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    # --- reserved (2) ---
    {
        "create": dict(
            brand="Renault", model="Megane", year="2019", mileage="60000", vin="VF1RFB00X61300007",
            seller_name="Христина Панченко", seller_phone="+380671330007",
            body_type="hatchback", transmission="manual", engine="1.3 TCe", fuel_type="petrol", color="white",
            condition="used", purchase_price=10200, additional_expenses=200, sale_price=12100,
            status="reserved", deadline_date=shift_days(10), date_added=shift_days(-18),
        ),
        "employee_email": "roman.demoseed@example.com", "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    {
        "create": dict(
            brand="Kia", model="Ceed", year="2020", mileage="41000", vin="U5YH1814ALL300008",
            seller_name="Денис Кучер", seller_phone="+380671330008", seller_email="denys.kucher.demoseed@example.com",
            body_type="hatchback", transmission="automatic", engine="1.6L", fuel_type="petrol", color="green",
            condition="used", purchase_price=12500, additional_expenses=300, sale_price=14700, discount_amount=400,
            status="reserved", deadline_date=shift_days(7), date_added=shift_days(-11),
        ),
        "employee_email": None, "mark_sold_final_price": None, "remove": False, "backdate_sold_days": None,
    },
    # --- sold (4), spread across different closing dates ---
    {
        "create": dict(
            brand="Toyota", model="RAV4", year="2019", mileage="58000", vin="JTMRFREV50D300009",
            seller_name="Володимир Гончар", seller_phone="+380671330009",
            body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="silver",
            condition="used", purchase_price=19500, additional_expenses=450, sale_price=23200,
            status="active", date_added=shift_days(-2),
        ),
        "employee_email": "hanna.demoseed@example.com", "mark_sold_final_price": 23000, "remove": False,
        "backdate_sold_days": None,  # sold "today"
    },
    {
        "create": dict(
            brand="BMW", model="520d", year="2017", mileage="120000", vin="WBAJA71050G300010",
            seller_name="Анна Ткач", seller_phone="+380671330010",
            body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="black",
            condition="used", condition_description="Повний пакет обслуговування",
            purchase_price=17800, additional_expenses=700, sale_price=21500,
            status="active", date_added=shift_days(-12),
        ),
        "employee_email": "ivan.demoseed@example.com", "mark_sold_final_price": 21000, "remove": False,
        "backdate_sold_days": 5,
    },
    {
        "create": dict(
            brand="Hyundai", model="i30", year="2018", mileage="70000", vin="TMAD381CAJJ300011",
            seller_name="Павло Демченко", seller_phone="+380671330011",
            body_type="hatchback", transmission="manual", engine="1.4L", fuel_type="petrol", color="orange",
            condition="used", purchase_price=8600, additional_expenses=250, sale_price=10400, discount_amount=300,
            status="active", date_added=shift_days(-28),
        ),
        "employee_email": None, "mark_sold_final_price": 10100, "remove": False,
        "backdate_sold_days": 20,
    },
    {
        "create": dict(
            brand="Audi", model="A4", year="2016", mileage="135000", vin="WAUZZZ8K5GA300012",
            seller_name="Софія Кравченко", seller_phone="+380671330012", seller_email="sofia.kravchenko.demoseed@example.com",
            body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="gray",
            condition="used", condition_description="Потребує косметичного ремонту салону",
            purchase_price=13200, additional_expenses=900, sale_price=16500, discount_amount=600,
            status="active", date_added=shift_days(-60),
        ),
        "employee_email": "roman.demoseed@example.com", "mark_sold_final_price": 15900, "remove": False,
        "backdate_sold_days": 45,
    },
    # --- removed (1) ---
    {
        "create": dict(
            brand="Chevrolet", model="Aveo", year="2015", mileage="140000", vin="XUFTF486J6L300013",
            seller_name="Роман Кузьменко", seller_phone="+380671330013",
            body_type="sedan", transmission="manual", engine="1.4L", fuel_type="petrol", color="white",
            condition="used", condition_description="Продавець зняв авто з продажу",
            purchase_price=4200, additional_expenses=150, sale_price=5400,
            status="active", date_added=shift_days(-22),
        ),
        "employee_email": None, "mark_sold_final_price": None, "remove": True, "backdate_sold_days": None,
    },
]


def create_listings(client: httpx.Client, token: str, employee_id_by_email: dict[str, int]) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    created: list[dict] = []

    log(f"\n--- Creating {len(LISTINGS)} listings ---")
    for entry in LISTINGS:
        payload = dict(entry["create"])
        label = f"{payload['brand']} {payload['model']} {payload['year']}"

        employee_email = entry["employee_email"]
        if employee_email is not None:
            employee_id = employee_id_by_email.get(employee_email)
            if employee_id is None:
                log(f"[FAIL] '{label}': unknown employee email {employee_email!r}, skipping employee_id")
            else:
                payload["employee_id"] = employee_id

        response = client.post("/listings", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create '{label}': {response.status_code} {response.text}")
            continue

        listing = response.json()
        log(f"[OK] Created '{label}' -> id={listing['id']} status={listing['status']}")
        created.append({
            "id": listing["id"],
            "label": label,
            "mark_sold_final_price": entry["mark_sold_final_price"],
            "remove": entry["remove"],
            "backdate_sold_days": entry["backdate_sold_days"],
        })

    return created


def mark_listings_sold(client: httpx.Client, token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    sold_count = 0

    log("\n--- Marking listings sold via POST /listings/{id}/mark-sold ---")
    for item in created:
        if item["mark_sold_final_price"] is None:
            continue

        response = client.post(
            f"/listings/{item['id']}/mark-sold",
            json={"final_sale_price": item["mark_sold_final_price"]},
            headers=headers,
        )
        if response.status_code != 200:
            log(f"[FAIL] mark-sold '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        listing = response.json()
        log(
            f"[OK] Sold '{item['label']}' (id={item['id']}) -> "
            f"date_sold={listing['date_sold']} net_profit={listing['net_profit']}"
        )
        sold_count += 1

    return sold_count


def remove_listings(client: httpx.Client, token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    removed_count = 0

    log("\n--- Marking listings removed via PATCH /listings/{id} ---")
    for item in created:
        if not item["remove"]:
            continue

        response = client.patch(f"/listings/{item['id']}", json={"status": "removed"}, headers=headers)
        if response.status_code != 200:
            log(f"[FAIL] remove '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        log(f"[OK] Removed '{item['label']}' (id={item['id']})")
        removed_count += 1

    return removed_count


def backdate_sold_dates(created: list[dict]) -> int:
    """The one deliberate exception described in the module docstring: patch
    date_sold/archived_at/DealHistory.date_closed AFTER the real mark-sold
    call already ran _record_deal_history() correctly. Every computed/
    snapshot field (net_profit, purchase_price, additional_expenses,
    date_added) is already correct at this point — only the date moves."""
    to_backdate = [item for item in created if item["mark_sold_final_price"] is not None and item["backdate_sold_days"]]
    if not to_backdate:
        return 0

    log(f"\n--- Backdating sale date for {len(to_backdate)} listing(s) (direct DB patch, see docstring) ---")
    session = SessionLocal()
    backdated_count = 0
    try:
        for item in to_backdate:
            backdated_date = TODAY - timedelta(days=item["backdate_sold_days"])
            backdated_datetime = datetime.combine(backdated_date, datetime.min.time(), tzinfo=timezone.utc)

            listing = session.query(Listing).filter(Listing.id == item["id"]).first()
            if listing is None:
                log(f"[FAIL] Backdate '{item['label']}': listing {item['id']} not found")
                continue
            listing.date_sold = backdated_date
            listing.archived_at = backdated_datetime

            deal_history_entry = (
                session.query(DealHistory)
                .filter(DealHistory.listing_id == item["id"], DealHistory.deal_type == "sold")
                .first()
            )
            if deal_history_entry is not None:
                deal_history_entry.date_closed = backdated_date

            session.commit()
            log(f"[OK] Backdated '{item['label']}' (id={item['id']}) -> date_sold={backdated_date.isoformat()}")
            backdated_count += 1
        return backdated_count
    finally:
        session.close()


# ============================================================================
# Buyers, via POST /clients — attached to some of the sold/reserved listings
# ============================================================================

BUYERS: list[dict] = [
    {"listing_index": 5, "name": "Максим Іллєнко", "phone": "+380671330101", "employee_email": "roman.demoseed@example.com"},
    {"listing_index": 6, "name": "Катерина Левченко", "phone": "+380671330102", "employee_email": None},
    {"listing_index": 8, "name": "Артем Гайдук", "phone": "+380671330103", "email": "artem.haiduk.demoseed@example.com", "employee_email": "hanna.demoseed@example.com"},
    {"listing_index": 9, "name": "Ольга Стельмах", "phone": "+380671330104", "employee_email": "ivan.demoseed@example.com"},
]


def create_buyers(client: httpx.Client, token: str, created_listings: list[dict], employee_id_by_email: dict[str, int]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    created_count = 0

    log(f"\n--- Creating {len(BUYERS)} buyer clients ---")
    for buyer in BUYERS:
        if buyer["listing_index"] >= len(created_listings):
            log(f"[FAIL] Buyer '{buyer['name']}': listing index {buyer['listing_index']} was not created, skipping")
            continue

        listing = created_listings[buyer["listing_index"]]
        payload = {
            "listing_id": listing["id"],
            "client_type": "buyer",
            "name": buyer["name"],
            "phone": buyer["phone"],
        }
        if "email" in buyer:
            payload["email"] = buyer["email"]

        response = client.post("/clients", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create buyer '{buyer['name']}': {response.status_code} {response.text}")
            continue

        buyer_client = response.json()
        log(f"[OK] Created buyer '{buyer['name']}' -> id={buyer_client['id']} listing='{listing['label']}'")
        created_count += 1

        employee_email = buyer["employee_email"]
        if employee_email is not None:
            employee_id = employee_id_by_email.get(employee_email)
            if employee_id is not None:
                client.patch(f"/clients/{buyer_client['id']}", json={"employee_id": employee_id}, headers=headers)

    return created_count


# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="Delete the seed company's data and exit (does not reseed)")
    args = parser.parse_args()

    if args.reset:
        reset_seed_data()
        return

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        ensure_owner_does_not_already_exist(client)

        token = register_owner(client)
        position_id_by_name = create_positions(client, token)
        employee_id_by_email = create_employees(client, token, position_id_by_name)

        created_listings = create_listings(client, token, employee_id_by_email)
        sold_count = mark_listings_sold(client, token, created_listings)
        removed_count = remove_listings(client, token, created_listings)
        backdated_count = backdate_sold_dates(created_listings)
        buyer_count = create_buyers(client, token, created_listings, employee_id_by_email)

        log("\n=== SUMMARY ===")
        log(f"Owner login:        {OWNER_EMAIL} / {OWNER_PASSWORD}")
        log(f"Employees created:  {len(employee_id_by_email)} / {len(EMPLOYEES)} (all password: {EMPLOYEE_PASSWORD})")
        log(f"Positions created:  {len(position_id_by_name)} / {len(POSITIONS)}")
        log(f"Listings created:   {len(created_listings)} / {len(LISTINGS)}")
        log(f"Marked sold:        {sold_count}")
        log(f"Marked removed:     {removed_count}")
        log(f"Sale dates backdated: {backdated_count}")
        log(f"Buyer clients created: {buyer_count} / {len(BUYERS)}")


if __name__ == "__main__":
    main()
