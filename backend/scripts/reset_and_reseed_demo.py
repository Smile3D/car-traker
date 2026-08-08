#!/usr/bin/env python3
"""Reset and reseed the demo/test data for ONE specific, already-existing
company — the one owned by OWNER_EMAIL below. Unlike scripts/seed_demo_data.py
(which creates a brand new owner+company from scratch), this script targets a
company that already exists and must keep existing: the owner's User row,
their Company row, and their login password are never touched or recreated.
Only the company's CHILDREN (employees, listings+photos, clients, deal
history, sales plans, positions, client stages, invites) are wiped and
regenerated.

WHY THROUGH THE REAL API, NOT DIRECT INSERTS: same reasoning as
seed_demo_data.py's docstring — POST /listings, POST /listings/{id}/mark-sold,
POST /listings/{id}/mark-on-service, PATCH /listings/{id} (removed), POST
/clients, POST /employees/invites + POST /auth/register, POST /sales-plans.
This is what fills in every derived/snapshot field correctly (net_profit,
date_added, archived_at, the DealHistory lead_source snapshot, etc) — a raw
bulk INSERT bypassing this logic is exactly how this app ended up with NULL
snapshot fields on old rows before, more than once.

HOW WE AUTHENTICATE AS THE EXISTING OWNER WITHOUT THEIR PASSWORD: we never
need it. create_access_token() (the same function POST /auth/login calls
internally once it has verified a password) mints a valid bearer token
directly from the owner's email. The owner's hashed_password column is never
read or written anywhere in this script.

THE ONE DELIBERATE EXCEPTION TO "real API only": same as seed_demo_data.py —
mark_listing_sold() always sets date_sold = today() with no API parameter to
backdate it. To spread sales across the last few months (so historical sales-
plan completion stats have something to show), this script calls the real
mark-sold endpoint first (so every computed/snapshot field is correct), then
patches only Listing.date_sold/archived_at and DealHistory.date_closed
directly via SQLAlchemy. Nothing else is ever touched by direct DB write.

USAGE (from the repo root, backend container already running):
    docker compose exec backend python -m scripts.reset_and_reseed_demo

There is no --reset-only / no-reseed flag here (unlike seed_demo_data.py) —
this script's whole point is reset-then-reseed as one step, since the target
company must never be left in a "wiped, no data at all" state for long.
"""

import calendar
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.client_stage import ClientStage  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.deal_history import DealHistory  # noqa: E402
from app.models.employee_invite import EmployeeInvite  # noqa: E402
from app.models.listing import Listing  # noqa: E402
from app.models.position import Position  # noqa: E402
from app.models.sales_plan import SalesPlan  # noqa: E402
from app.models.user import User  # noqa: E402
from app.config import settings  # noqa: E402
from app.services.security import create_access_token  # noqa: E402

BASE_URL = "http://localhost:8000"

OWNER_EMAIL = "aleksandrov+1@gmail.com"
EMPLOYEE_PASSWORD = "Test1234!"

TODAY = date.today()


def log(message: str) -> None:
    print(message, flush=True)


def shift_days(days: int) -> str:
    """ISO date `days` from today. Negative = past, positive = future."""
    return (TODAY + timedelta(days=days)).isoformat()


def month_start(months_ago: int) -> date:
    """The 1st of the month that is `months_ago` months before today's month."""
    year = TODAY.year
    month = TODAY.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def day_in_month(months_ago: int, day: int) -> date:
    ms = month_start(months_ago)
    last_day = calendar.monthrange(ms.year, ms.month)[1]
    return ms.replace(day=min(day, last_day))


def days_ago_for(months_ago: int, day: int) -> int:
    """How many days before today `day_in_month(months_ago, day)` is —
    what the backdating helper (mirrors seed_demo_data.py's) takes."""
    return (TODAY - day_in_month(months_ago, day)).days


# ============================================================================
# STEP 1 — reset: wipe this company's children, keep owner + company intact
# ============================================================================

def reset_company_data() -> int:
    session = SessionLocal()
    try:
        owner = session.query(User).filter(User.email == OWNER_EMAIL).first()
        if owner is None or owner.company_id is None:
            log(f"[FAIL] No company found for owner {OWNER_EMAIL} — nothing to reset against")
            sys.exit(1)

        company_id = owner.company_id
        company = session.query(Company).filter(Company.id == company_id).first()

        listing_count = session.query(Listing).filter(Listing.company_id == company_id).count()
        client_count = session.query(Client).filter(Client.company_id == company_id).count()
        deal_history_count = session.query(DealHistory).filter(DealHistory.company_id == company_id).count()
        sales_plan_count = session.query(SalesPlan).filter(SalesPlan.company_id == company_id).count()
        employee_count = session.query(User).filter(User.company_id == company_id, User.role == "employee").count()

        log("=" * 78)
        log(f"ABOUT TO DELETE for company_id={company_id} ({company.name if company else '?'}):")
        log(f"  - {employee_count} employee account(s) (owner {OWNER_EMAIL} is KEPT, untouched)")
        log(f"  - {listing_count} listing(s) + their photo files on disk")
        log(f"  - {client_count} client(s) (cascade from listings)")
        log(f"  - {deal_history_count} deal_history row(s)")
        log(f"  - {sales_plan_count} sales_plan row(s)")
        log("  - all positions, client stages, and employee invites for this company")
        log("=" * 78)

        # Photo files live on disk, not in the DB — ListingPhoto rows cascade
        # at the DB level (ON DELETE CASCADE) once their Listing is deleted,
        # but that never touches the filesystem. Delete the files first,
        # while we still have the listing ids.
        listing_ids = [
            row.id for row in session.query(Listing.id).filter(Listing.company_id == company_id).all()
        ]
        deleted_photo_dirs = 0
        for listing_id in listing_ids:
            listing_photo_dir = Path(settings.upload_dir) / "listing-photos" / str(listing_id)
            if listing_photo_dir.exists():
                shutil.rmtree(listing_photo_dir, ignore_errors=True)
                deleted_photo_dirs += 1
        log(f"[OK] Removed photo files for {deleted_photo_dirs} listing(s)")

        deleted_sales_plans = session.query(SalesPlan).filter(SalesPlan.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_sales_plans} sales_plan row(s)")

        deleted_deal_history = session.query(DealHistory).filter(DealHistory.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_deal_history} deal_history row(s)")

        # Client rows cascade at the DB level (ON DELETE CASCADE on
        # Client.listing_id), same as ListingPhoto — nothing further needed
        # for them once Listing rows go.
        deleted_listings = session.query(Listing).filter(Listing.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_listings} listing(s) (Client/ListingPhoto rows cascaded)")

        deleted_invites = session.query(EmployeeInvite).filter(EmployeeInvite.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_invites} employee invite(s)")

        deleted_client_stages = session.query(ClientStage).filter(ClientStage.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_client_stages} client stage(s)")

        # Employees before Positions — User.position_id has a live FK into
        # positions.id, so a Position row can't go while an employee still
        # references it. The owner (role='owner', not 'employee') is
        # deliberately excluded from this filter.
        deleted_employees = session.query(User).filter(User.company_id == company_id, User.role == "employee").delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_employees} employee account(s) — owner {OWNER_EMAIL} kept")

        deleted_positions = session.query(Position).filter(Position.company_id == company_id).delete(
            synchronize_session=False
        )
        log(f"[OK] Deleted {deleted_positions} position(s)")

        session.commit()
        log("[OK] Reset complete — owner and company row untouched\n")
        return company_id
    finally:
        session.close()


# ============================================================================
# STEP 2 — reseed, via the real API, authenticated as the existing owner
# ============================================================================

def mint_owner_token() -> str:
    """Never touches/reads the owner's password — this is the same token-
    minting function POST /auth/login calls internally after a successful
    password check. We already know who the owner is (their email); we just
    need a bearer token to drive the rest of this script through the API."""
    session = SessionLocal()
    try:
        owner = session.query(User).filter(User.email == OWNER_EMAIL).first()
        if owner is None:
            log(f"[FAIL] Owner {OWNER_EMAIL} disappeared between reset and reseed — aborting")
            sys.exit(1)
        return create_access_token(subject=owner.email)
    finally:
        session.close()


POSITIONS = ["Продавець-консультант", "Менеджер з продажу", "Керівник напрямку"]


def create_positions(client: httpx.Client, token: str) -> dict[str, int]:
    headers = {"Authorization": f"Bearer {token}"}
    position_id_by_name: dict[str, int] = {}

    log(f"--- Creating {len(POSITIONS)} positions ---")
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
    {"email": "aleksandrov+2@gmail.com", "first_name": "Олена", "last_name": "Продавець", "position": "Продавець-консультант"},
    {"email": "aleksandrov+3@gmail.com", "first_name": "Максим", "last_name": "Менеджер", "position": "Менеджер з продажу"},
    {"email": "aleksandrov+4@gmail.com", "first_name": "Дмитро", "last_name": "Консультант", "position": "Керівник напрямку"},
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

        # No email-confirmation step exists anywhere in this app — POST
        # /auth/register with a valid invite token creates an immediately
        # usable, already-active account. There's nothing further to "confirm".
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
# Listings — 15 non-sold across every other status + 10 taken to "sold"
# ============================================================================

LEAD_SOURCES = ["tiktok", "instagram", "facebook", "referral", "saw_ad_online"]


def lead_source_for(index: int) -> str:
    return LEAD_SOURCES[index % len(LEAD_SOURCES)]


EMP2, EMP3, EMP4 = "aleksandrov+2@gmail.com", "aleksandrov+3@gmail.com", "aleksandrov+4@gmail.com"

# action: "none" | "on_service" | "remove" | "sold"
# sold_month_ago / sold_day: which past month + day of month the sale should
# APPEAR to have closed on (0 = this month). Only meaningful when action="sold".
LISTINGS: list[dict] = [
    # --- draft (4) ---
    {"create": dict(brand="Toyota", model="Camry", year="2019", mileage="65000", vin="TESTSEED000000001",
        seller_name="Богдан Гриценко", seller_phone="+380671440001",
        body_type="sedan", transmission="automatic", engine="2.5L", fuel_type="petrol", color="white",
        condition="used", purchase_price=13500, additional_expenses=300, sale_price=16800,
        status="draft", date_added=shift_days(-5)),
     "employee_email": None, "action": "none"},
    {"create": dict(brand="Volkswagen", model="Passat", year="2018", mileage="98000", vin="TESTSEED000000002",
        seller_name="Марія Дяченко", seller_phone="+380671440002",
        body_type="sedan", transmission="manual", engine="1.6 TDI", fuel_type="diesel", color="silver",
        condition="used", purchase_price=10200, additional_expenses=450, sale_price=12900,
        status="draft", date_added=shift_days(-2)),
     "employee_email": EMP2, "action": "none"},
    {"create": dict(brand="Ford", model="Focus", year="2020", mileage="42000", vin="TESTSEED000000003",
        seller_name="Ігор Савчук", seller_phone="+380671440003",
        body_type="hatchback", transmission="automatic", engine="1.5L", fuel_type="petrol", color="blue",
        condition="used", purchase_price=11800, additional_expenses=200, sale_price=14200,
        status="draft", date_added=shift_days(-1)),
     "employee_email": EMP3, "action": "none"},
    {"create": dict(brand="Nissan", model="Qashqai", year="2019", mileage="71000", vin="TESTSEED000000004",
        seller_name="Олена Бабич", seller_phone="+380671440004",
        body_type="suv", transmission="automatic", engine="1.3 DIG-T", fuel_type="petrol", color="gray",
        condition="used", purchase_price=14500, additional_expenses=350, sale_price=17600,
        status="draft", date_added=shift_days(-8)),
     "employee_email": None, "action": "none"},
    # --- active (4) ---
    {"create": dict(brand="Honda", model="CR-V", year="2021", mileage="25000", vin="TESTSEED000000005",
        seller_name="Тарас Мороз", seller_phone="+380671440005", seller_email="taras.moroz.seed@example.com",
        body_type="suv", transmission="automatic", engine="1.5 Turbo", fuel_type="petrol", color="black",
        condition="used", purchase_price=22500, additional_expenses=400, sale_price=27200,
        status="active", deadline_date=shift_days(20), date_added=shift_days(-14)),
     "employee_email": EMP4, "action": "none"},
    {"create": dict(brand="Mazda", model="6", year="2019", mileage="58000", vin="TESTSEED000000006",
        seller_name="Юрій Романенко", seller_phone="+380671440006",
        body_type="sedan", transmission="automatic", engine="2.0L", fuel_type="petrol", color="red",
        condition="used", purchase_price=15800, additional_expenses=300, sale_price=19100,
        status="active", deadline_date=shift_days(15), date_added=shift_days(-20)),
     "employee_email": EMP2, "action": "none"},
    {"create": dict(brand="Skoda", model="Octavia", year="2020", mileage="38000", vin="TESTSEED000000007",
        seller_name="Христина Панченко", seller_phone="+380671440007",
        body_type="hatchback", transmission="manual", engine="1.6 TDI", fuel_type="diesel", color="white",
        condition="used", purchase_price=16200, additional_expenses=250, sale_price=19500,
        status="active", deadline_date=shift_days(30), date_added=shift_days(-6)),
     "employee_email": EMP3, "action": "none"},
    {"create": dict(brand="Hyundai", model="Tucson", year="2021", mileage="19000", vin="TESTSEED000000008",
        seller_name="Денис Кучер", seller_phone="+380671440008",
        body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="blue",
        condition="used", purchase_price=24800, additional_expenses=500, sale_price=29900,
        status="active", deadline_date=shift_days(-3), date_added=shift_days(-45)),
     "employee_email": None, "action": "none"},
    # --- reserved (3) ---
    {"create": dict(brand="Kia", model="Sportage", year="2018", mileage="88000", vin="TESTSEED000000009",
        seller_name="Володимир Гончар", seller_phone="+380671440009",
        body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="silver",
        condition="used", purchase_price=15500, additional_expenses=350, sale_price=18700, discount_amount=300,
        status="reserved", deadline_date=shift_days(9), date_added=shift_days(-16)),
     "employee_email": EMP4, "action": "none", "buyer": {"name": "Максим Іллєнко", "phone": "+380671440101"}},
    {"create": dict(brand="Renault", model="Kadjar", year="2019", mileage="63000", vin="TESTSEED000000010",
        seller_name="Анна Ткач", seller_phone="+380671440010",
        body_type="suv", transmission="manual", engine="1.3 TCe", fuel_type="petrol", color="orange",
        condition="used", purchase_price=13900, additional_expenses=280, sale_price=16800,
        status="reserved", deadline_date=shift_days(6), date_added=shift_days(-11)),
     "employee_email": EMP2, "action": "none", "buyer": {"name": "Катерина Левченко", "phone": "+380671440102"}},
    {"create": dict(brand="Opel", model="Astra", year="2017", mileage="105000", vin="TESTSEED000000011",
        seller_name="Павло Демченко", seller_phone="+380671440011",
        body_type="hatchback", transmission="manual", engine="1.4L", fuel_type="petrol", color="gray",
        condition="used", purchase_price=8600, additional_expenses=400, sale_price=10900,
        status="reserved", deadline_date=shift_days(4), date_added=shift_days(-25)),
     "employee_email": None, "action": "none", "buyer": {"name": "Артем Гайдук", "phone": "+380671440103"}},
    # --- on_service (3) ---
    {"create": dict(brand="BMW", model="X3", year="2019", mileage="72000", vin="TESTSEED000000012",
        seller_name="Софія Кравченко", seller_phone="+380671440012",
        body_type="suv", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="black",
        condition="used", purchase_price=26500, additional_expenses=600, sale_price=32000,
        status="active", date_added=shift_days(-30)),
     "employee_email": EMP3, "action": "on_service",
     "service_note": "Заміна гальмівної системи (диски+колодки)", "service_start_days_ago": 3, "service_expected_end_days": 4},
    {"create": dict(brand="Audi", model="Q5", year="2018", mileage="91000", vin="TESTSEED000000013",
        seller_name="Роман Кузьменко", seller_phone="+380671440013",
        body_type="suv", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="white",
        condition="used", condition_description="Потребує кузовного ремонту переднього крила",
        purchase_price=20500, additional_expenses=800, sale_price=25200,
        status="active", date_added=shift_days(-19)),
     "employee_email": EMP4, "action": "on_service",
     "service_note": "Кузовний ремонт переднього крила та фарбування", "service_start_days_ago": 6, "service_expected_end_days": 9},
    {"create": dict(brand="Mercedes-Benz", model="C200", year="2020", mileage="45000", vin="TESTSEED000000014",
        seller_name="Ольга Стельмах", seller_phone="+380671440014",
        body_type="sedan", transmission="automatic", engine="2.0L", fuel_type="petrol", color="black",
        condition="used", purchase_price=27800, additional_expenses=500, sale_price=33500,
        status="active", date_added=shift_days(-4)),
     "employee_email": EMP2, "action": "on_service",
     "service_note": "Плановий ТО перед виставленням на продаж", "service_start_days_ago": 1, "service_expected_end_days": 2},
    # --- removed (1) ---
    {"create": dict(brand="Chevrolet", model="Cruze", year="2016", mileage="130000", vin="TESTSEED000000015",
        seller_name="Наталія Бондаренко", seller_phone="+380671440015",
        body_type="sedan", transmission="manual", engine="1.6L", fuel_type="petrol", color="white",
        condition="used", condition_description="Продавець передумав продавати",
        purchase_price=6200, additional_expenses=150, sale_price=8100,
        status="active", date_added=shift_days(-22)),
     "employee_email": None, "action": "remove"},

    # =========================== SOLD (10) ===========================
    # --- this month (4): Olena x2, Maksym x1, Dmytro x1 ---
    {"create": dict(brand="Toyota", model="RAV4", year="2020", mileage="41000", vin="TESTSEED000000016",
        seller_name="Дмитро Савенко", seller_phone="+380671440016",
        body_type="suv", transmission="automatic", engine="2.0L", fuel_type="petrol", color="silver",
        condition="used", purchase_price=21500, additional_expenses=400, sale_price=25800,
        status="active", date_added=shift_days(-35)),
     "employee_email": EMP2, "action": "sold", "final_price": 25500, "sold_month_ago": 0, "sold_day": 2,
     "buyer": {"name": "Іван Марченко", "phone": "+380671440201"}},
    {"create": dict(brand="Volkswagen", model="Tiguan", year="2019", mileage="55000", vin="TESTSEED000000017",
        seller_name="Валентина Шевчук", seller_phone="+380671440017",
        body_type="suv", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="blue",
        condition="used", purchase_price=18700, additional_expenses=500, sale_price=22900,
        status="active", date_added=shift_days(-40)),
     "employee_email": EMP2, "action": "sold", "final_price": 22400, "sold_month_ago": 0, "sold_day": 3,
     "buyer": {"name": "Тетяна Кравець", "phone": "+380671440202"}},
    {"create": dict(brand="Ford", model="Kuga", year="2018", mileage="68000", vin="TESTSEED000000018",
        seller_name="Олексій Гуменюк", seller_phone="+380671440018",
        body_type="suv", transmission="automatic", engine="1.5 EcoBoost", fuel_type="petrol", color="red",
        condition="used", purchase_price=14200, additional_expenses=350, sale_price=17500,
        status="active", date_added=shift_days(-38)),
     "employee_email": EMP3, "action": "sold", "final_price": 17100, "sold_month_ago": 0, "sold_day": 1,
     "buyer": {"name": "Сергій Малець", "phone": "+380671440203"}},
    {"create": dict(brand="Nissan", model="X-Trail", year="2019", mileage="49000", vin="TESTSEED000000019",
        seller_name="Лариса Кучерява", seller_phone="+380671440019",
        body_type="suv", transmission="automatic", engine="1.6 DIG-T", fuel_type="petrol", color="gray",
        condition="used", purchase_price=17800, additional_expenses=300, sale_price=21600,
        status="active", date_added=shift_days(-33)),
     "employee_email": EMP4, "action": "sold", "final_price": 21300, "sold_month_ago": 0, "sold_day": 2,
     "buyer": {"name": "Оксана Бурлака", "phone": "+380671440204"}},
    # --- last month (3): Olena x1, Maksym x1, Dmytro x1 ---
    {"create": dict(brand="Honda", model="Civic", year="2018", mileage="76000", vin="TESTSEED000000020",
        seller_name="Микола Захарчук", seller_phone="+380671440020",
        body_type="sedan", transmission="automatic", engine="1.5 Turbo", fuel_type="petrol", color="black",
        condition="used", purchase_price=13400, additional_expenses=350, sale_price=16500,
        status="active", date_added=shift_days(-70)),
     "employee_email": EMP2, "action": "sold", "final_price": 16200, "sold_month_ago": 1, "sold_day": 12,
     "buyer": {"name": "Андрій Пасічник", "phone": "+380671440205"}},
    {"create": dict(brand="Mazda", model="CX-5", year="2019", mileage="52000", vin="TESTSEED000000021",
        seller_name="Ірина Мельниченко", seller_phone="+380671440021",
        body_type="suv", transmission="automatic", engine="2.5L", fuel_type="petrol", color="white",
        condition="used", purchase_price=19800, additional_expenses=450, sale_price=24000,
        status="active", date_added=shift_days(-75)),
     "employee_email": EMP3, "action": "sold", "final_price": 23600, "sold_month_ago": 1, "sold_day": 18,
     "buyer": {"name": "Вікторія Онищенко", "phone": "+380671440206"}},
    {"create": dict(brand="Skoda", model="Superb", year="2017", mileage="99000", vin="TESTSEED000000022",
        seller_name="Геннадій Ковальов", seller_phone="+380671440022",
        body_type="sedan", transmission="automatic", engine="2.0 TDI", fuel_type="diesel", color="silver",
        condition="used", purchase_price=15600, additional_expenses=600, sale_price=19200,
        status="active", date_added=shift_days(-80)),
     "employee_email": EMP4, "action": "sold", "final_price": 18700, "sold_month_ago": 1, "sold_day": 25,
     "buyer": {"name": "Роксолана Гайова", "phone": "+380671440207"}},
    # --- 2 months ago (3): Olena x1, Maksym x1, Dmytro x1 ---
    {"create": dict(brand="Hyundai", model="Elantra", year="2017", mileage="87000", vin="TESTSEED000000023",
        seller_name="Вадим Остапенко", seller_phone="+380671440023",
        body_type="sedan", transmission="automatic", engine="1.6L", fuel_type="petrol", color="blue",
        condition="used", purchase_price=9800, additional_expenses=250, sale_price=12200,
        status="active", date_added=shift_days(-100)),
     "employee_email": EMP2, "action": "sold", "final_price": 11900, "sold_month_ago": 2, "sold_day": 8,
     "buyer": {"name": "Марина Шпак", "phone": "+380671440208"}},
    {"create": dict(brand="Kia", model="Ceed", year="2018", mileage="94000", vin="TESTSEED000000024",
        seller_name="Björn Wagner", seller_phone="+380671440024",
        body_type="hatchback", transmission="automatic", engine="1.6L", fuel_type="petrol", color="green",
        condition="used", purchase_price=10500, additional_expenses=300, sale_price=13100, discount_amount=200,
        status="active", date_added=shift_days(-95)),
     "employee_email": EMP3, "action": "sold", "final_price": 12700, "sold_month_ago": 2, "sold_day": 15,
     "buyer": {"name": "Євген Пилипенко", "phone": "+380671440209"}},
    {"create": dict(brand="Renault", model="Megane", year="2016", mileage="118000", vin="TESTSEED000000025",
        seller_name="Кароліна Юрчук", seller_phone="+380671440025",
        body_type="hatchback", transmission="manual", engine="1.5 dCi", fuel_type="diesel", color="white",
        condition="used", purchase_price=8100, additional_expenses=350, sale_price=10400,
        status="active", date_added=shift_days(-110)),
     "employee_email": EMP4, "action": "sold", "final_price": 10100, "sold_month_ago": 2, "sold_day": 20,
     "buyer": {"name": "Назар Гриценко", "phone": "+380671440210"}},
]


def create_listings(client: httpx.Client, token: str, employee_id_by_email: dict[str, int]) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    created: list[dict] = []

    log(f"\n--- Creating {len(LISTINGS)} listings (15 non-sold + 10 to be sold) ---")
    for index, entry in enumerate(LISTINGS):
        payload = dict(entry["create"])
        payload["seller_lead_source"] = lead_source_for(index)
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
        log(f"[OK] Created '{label}' -> id={listing['id']} lead_source={payload['seller_lead_source']}")
        created.append({**entry, "id": listing["id"], "label": label, "index": index})

    return created


def mark_listings_on_service(client: httpx.Client, token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    count = 0

    log("\n--- Marking listings on_service via POST /listings/{id}/mark-on-service ---")
    for item in created:
        if item["action"] != "on_service":
            continue

        payload = {
            "service_note": item["service_note"],
            "service_start_date": shift_days(-item["service_start_days_ago"]),
            "service_expected_end_date": shift_days(item["service_expected_end_days"]),
        }
        response = client.post(f"/listings/{item['id']}/mark-on-service", json=payload, headers=headers)
        if response.status_code != 200:
            log(f"[FAIL] mark-on-service '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        log(f"[OK] On service: '{item['label']}' (id={item['id']}) — {item['service_note']}")
        count += 1

    return count


def remove_listings(client: httpx.Client, token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    count = 0

    log("\n--- Marking listings removed via PATCH /listings/{id} ---")
    for item in created:
        if item["action"] != "remove":
            continue

        response = client.patch(f"/listings/{item['id']}", json={"status": "removed"}, headers=headers)
        if response.status_code != 200:
            log(f"[FAIL] remove '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        log(f"[OK] Removed '{item['label']}' (id={item['id']})")
        count += 1

    return count


def mark_listings_sold(client: httpx.Client, token: str, created: list[dict]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    count = 0

    log("\n--- Marking listings sold via POST /listings/{id}/mark-sold ---")
    for item in created:
        if item["action"] != "sold":
            continue

        response = client.post(
            f"/listings/{item['id']}/mark-sold",
            json={"final_sale_price": item["final_price"]},
            headers=headers,
        )
        if response.status_code != 200:
            log(f"[FAIL] mark-sold '{item['label']}' (id={item['id']}): {response.status_code} {response.text}")
            continue

        listing = response.json()
        log(f"[OK] Sold '{item['label']}' (id={item['id']}) -> net_profit={listing['net_profit']}")
        count += 1

    return count


def backdate_sold_dates(created: list[dict]) -> int:
    """The one deliberate direct-DB exception described in the module
    docstring — every computed/snapshot field is already correct at this
    point (set by the real mark-sold call above); only the date moves, so
    sales are spread across this month and the previous two."""
    to_backdate = [item for item in created if item["action"] == "sold"]
    if not to_backdate:
        return 0

    log(f"\n--- Backdating sale dates for {len(to_backdate)} listing(s) across the last 3 months ---")
    session = SessionLocal()
    count = 0
    try:
        for item in to_backdate:
            target_date = day_in_month(item["sold_month_ago"], item["sold_day"])
            target_datetime = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)

            listing = session.query(Listing).filter(Listing.id == item["id"]).first()
            if listing is None:
                log(f"[FAIL] Backdate '{item['label']}': listing {item['id']} not found")
                continue
            listing.date_sold = target_date
            listing.archived_at = target_datetime

            deal_history_entry = (
                session.query(DealHistory)
                .filter(DealHistory.listing_id == item["id"], DealHistory.deal_type == "sold")
                .first()
            )
            if deal_history_entry is not None:
                deal_history_entry.date_closed = target_date

            session.commit()
            log(f"[OK] Backdated '{item['label']}' (id={item['id']}) -> date_closed={target_date.isoformat()}")
            count += 1
        return count
    finally:
        session.close()


def create_buyers(client: httpx.Client, token: str, created: list[dict], employee_id_by_email: dict[str, int]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    count = 0

    log("\n--- Creating buyer clients for reserved/sold listings ---")
    for item in created:
        buyer = item.get("buyer")
        if buyer is None:
            continue

        payload = {
            "listing_id": item["id"],
            "client_type": "buyer",
            "name": buyer["name"],
            "phone": buyer["phone"],
            "lead_source": lead_source_for(item["index"] + 1),
        }
        response = client.post("/clients", json=payload, headers=headers)
        if response.status_code != 201:
            log(f"[FAIL] Create buyer '{buyer['name']}' for '{item['label']}': {response.status_code} {response.text}")
            continue

        buyer_client = response.json()
        log(f"[OK] Buyer '{buyer['name']}' -> id={buyer_client['id']} listing='{item['label']}' lead_source={payload['lead_source']}")
        count += 1

        employee_email = item["employee_email"]
        if employee_email is not None:
            employee_id = employee_id_by_email.get(employee_email)
            if employee_id is not None:
                client.patch(f"/clients/{buyer_client['id']}", json={"employee_id": employee_id}, headers=headers)

    return count


# ============================================================================
# Sales plans — current month + 2 past months, via POST /sales-plans
# ============================================================================

# (months_ago, {employee_email: target_count})
SALES_PLANS: list[tuple[int, dict[str, int]]] = [
    (0, {EMP2: 2, EMP3: 3, EMP4: 1}),  # this month: Olena met(2/2), Maksym short so far(1/3), Dmytro met(1/1)
    (1, {EMP2: 1, EMP3: 2, EMP4: 1}),  # last month: Olena met(1/1), Maksym missed(1/2), Dmytro met(1/1)
    (2, {EMP2: 2, EMP3: 1, EMP4: 1}),  # 2 months ago: Olena missed(1/2), Maksym met(1/1), Dmytro met(1/1)
]


def create_sales_plans(client: httpx.Client, token: str, employee_id_by_email: dict[str, int]) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    count = 0

    log("\n--- Assigning sales plans via POST /sales-plans (current + 2 past months) ---")
    for months_ago, targets in SALES_PLANS:
        month_value = f"{month_start(months_ago).year}-{month_start(months_ago).month:02d}"
        for employee_email, target_count in targets.items():
            employee_id = employee_id_by_email.get(employee_email)
            if employee_id is None:
                continue
            response = client.post(
                "/sales-plans",
                json={"employee_id": employee_id, "month": month_value, "target_count": target_count},
                headers=headers,
            )
            if response.status_code != 201:
                log(f"[FAIL] Plan {employee_email} {month_value}: {response.status_code} {response.text}")
                continue
            log(f"[OK] Plan {employee_email} {month_value} target={target_count}")
            count += 1

    return count


# ============================================================================

def main() -> None:
    company_id = reset_company_data()
    token = mint_owner_token()

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        position_id_by_name = create_positions(client, token)
        employee_id_by_email = create_employees(client, token, position_id_by_name)

        created_listings = create_listings(client, token, employee_id_by_email)
        on_service_count = mark_listings_on_service(client, token, created_listings)
        removed_count = remove_listings(client, token, created_listings)
        # Buyers must be attached BEFORE mark-sold — the API correctly
        # refuses to add a buyer to an already-closed listing (mirrors real
        # life: you know the buyer before the deal closes), so this order
        # also determines whether DealHistory's buyer_name/buyer_phone
        # snapshot ends up populated or null.
        buyer_count = create_buyers(client, token, created_listings, employee_id_by_email)
        sold_count = mark_listings_sold(client, token, created_listings)
        backdated_count = backdate_sold_dates(created_listings)
        plan_count = create_sales_plans(client, token, employee_id_by_email)

        status_counts: dict[str, int] = {}
        for item in created_listings:
            final_status = {
                "on_service": "on_service", "remove": "removed", "sold": "sold", "none": "created-as-is",
            }[item["action"]]
            status_counts[final_status] = status_counts.get(final_status, 0) + 1

        log("\n=== SUMMARY ===")
        log(f"Company id:          {company_id}")
        log(f"Owner login:         {OWNER_EMAIL} (password unchanged)")
        log(f"Employees created:   {len(employee_id_by_email)} / {len(EMPLOYEES)} (all password: {EMPLOYEE_PASSWORD})")
        for employee in EMPLOYEES:
            log(f"  - {employee['email']} ({employee['first_name']} {employee['last_name']})")
        log(f"Positions created:   {len(position_id_by_name)} / {len(POSITIONS)}")
        log(f"Listings created:    {len(created_listings)} / {len(LISTINGS)}")
        log(f"  by action: on_service={on_service_count} removed={removed_count} sold={sold_count} (rest stay draft/active/reserved)")
        log(f"Sale dates backdated: {backdated_count}")
        log(f"Buyer clients created: {buyer_count}")
        log(f"Sales plans assigned: {plan_count}")


if __name__ == "__main__":
    main()
