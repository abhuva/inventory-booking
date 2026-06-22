from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import hash_password
from inventory_booking_api.main import app
from inventory_booking_api.models import Base
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User

ADMIN_EMAIL = "admin@example.org"
ADMIN_PASSWORD = "correct horse battery staple"
USER_EMAIL = "user@example.org"
USER_PASSWORD = "user password 123"
BOOKING_START = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
BOOKING_END = BOOKING_START + timedelta(days=3)


@pytest.fixture
def client() -> Generator[TestClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            session.add_all(
                [
                    User(
                        email=ADMIN_EMAIL,
                        display_name="Admin",
                        role=UserRole.ADMIN,
                        password_hash=hash_password(ADMIN_PASSWORD),
                        is_active=True,
                    ),
                    User(
                        email=USER_EMAIL,
                        display_name="User",
                        role=UserRole.USER,
                        password_hash=hash_password(USER_PASSWORD),
                        is_active=True,
                    ),
                ]
            )
            await session.commit()

    async def drop_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    import asyncio

    asyncio.run(create_schema())
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(drop_schema())


def login(
    client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD
) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    csrf_token = client.cookies.get("inventory_booking_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


def test_write_endpoints_require_session(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "Juggling"})

    assert response.status_code == 401


def test_session_mutations_require_csrf_token(client: TestClient) -> None:
    login(client)

    response = client.post("/categories", json={"name": "Juggling"})

    assert response.status_code == 403


def test_login_me_and_logout(client: TestClient) -> None:
    csrf_headers = login(client)

    me_response = client.get("/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == ADMIN_EMAIL

    logout_response = client.post("/auth/logout", headers=csrf_headers)

    assert logout_response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})

    assert response.status_code == 401


def test_admin_can_manage_users(client: TestClient) -> None:
    headers = login(client)

    create_response = client.post(
        "/users",
        headers=headers,
        json={
            "email": "new-user@example.org",
            "display_name": "New User",
            "password": "new password 123",
            "role": "user",
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["email"] == "new-user@example.org"

    update_response = client.patch(
        f"/users/{created['id']}",
        headers=headers,
        json={"display_name": "Updated User"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "Updated User"


def test_normal_user_cannot_manage_users(client: TestClient) -> None:
    headers = login(client, USER_EMAIL, USER_PASSWORD)

    response = client.get("/users", headers=headers)

    assert response.status_code == 403


def test_normal_user_cannot_read_audit_logs(client: TestClient) -> None:
    headers = login(client, USER_EMAIL, USER_PASSWORD)

    response = client.get("/audit/logs", headers=headers)

    assert response.status_code == 403


def test_create_and_list_category(client: TestClient) -> None:
    headers = login(client)

    response = client.post(
        "/categories",
        json={"name": "Juggling", "description": "Balls, clubs, rings"},
        headers=headers,
    )

    assert response.status_code == 200
    created = response.json()
    assert created["name"] == "Juggling"

    list_response = client.get("/categories")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == created["id"]

    audit_response = client.get("/audit/logs", headers=headers)

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["entity_type"] == "category"
    assert audit_response.json()[0]["action"] == "create"


def test_create_location(client: TestClient) -> None:
    headers = login(client)

    response = client.post(
        "/locations",
        json={"name": "Main Storage", "type": "storage"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["type"] == "storage"

    audit_response = client.get("/audit/logs", headers=headers)

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["entity_type"] == "location"


def test_asset_mode_validation(client: TestClient) -> None:
    headers = login(client)

    tracked_response = client.post(
        "/assets",
        json={"name": "Aerial Stand 01", "asset_type": "tracked"},
        headers=headers,
    )
    invalid_stock_response = client.post(
        "/assets",
        json={"name": "Juggling Balls", "asset_type": "stock"},
        headers=headers,
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["unit_name"] is None
    assert invalid_stock_response.status_code == 422


def test_stock_level_requires_stock_asset(client: TestClient) -> None:
    headers = login(client)

    location = client.post(
        "/locations",
        json={"name": "Main Storage", "type": "storage"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Trampoline", "asset_type": "tracked"},
        headers=headers,
    ).json()

    response = client.post(
        "/stock-levels",
        json={
            "asset_id": tracked_asset["id"],
            "location_id": location["id"],
            "quantity_total": 4,
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_create_stock_level_for_stock_asset(client: TestClient) -> None:
    headers = login(client)

    location = client.post(
        "/locations",
        json={"name": "Main Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Juggling Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()

    response = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 12,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["quantity_total"] == 12

    audit_response = client.get("/audit/logs", headers=headers)
    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": stock_asset["id"]},
        headers=headers,
    )

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["entity_type"] == "stock_level"
    assert event_response.status_code == 200
    assert event_response.json()[0]["asset_id"] == stock_asset["id"]
    assert event_response.json()[0]["event_type"] == "updated"


def test_booking_rejects_invalid_time_range(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "German Wheel", "asset_type": "tracked"},
        headers=headers,
    ).json()

    response = client.post(
        "/bookings",
        json={
            "title": "Workshop",
            "starts_at": BOOKING_END.isoformat(),
            "ends_at": BOOKING_START.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_booking_mutations_require_session(client: TestClient) -> None:
    response = client.post(
        "/bookings",
        json={
            "title": "Unauthenticated booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": "00000000-0000-0000-0000-000000000000"}],
        },
    )

    assert response.status_code == 401


def test_booking_mutations_require_csrf_token(client: TestClient) -> None:
    login(client)

    response = client.post(
        "/bookings/availability",
        json={
            "title": "Missing CSRF",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": "00000000-0000-0000-0000-000000000000"}],
        },
    )

    assert response.status_code == 403


def test_booking_create_rejects_protected_field_injection(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Injected Booking Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    response = client.post(
        "/bookings",
        json={
            "title": "Injected booking",
            "status": "completed",
            "requested_by_user_id": "00000000-0000-0000-0000-000000000000",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"], "created_at": BOOKING_START.isoformat()}],
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_booking_rejects_overlapping_tracked_asset(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Aerial Stand", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking_payload = {
        "title": "Project week",
        "starts_at": BOOKING_START.isoformat(),
        "ends_at": BOOKING_END.isoformat(),
        "lines": [{"asset_id": tracked_asset["id"]}],
    }

    first_response = client.post("/bookings", json=booking_payload, headers=headers)
    second_response = client.post(
        "/bookings",
        json={
            **booking_payload,
            "title": "Conflicting project",
            "starts_at": (BOOKING_START + timedelta(days=1)).isoformat(),
            "ends_at": (BOOKING_END + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["lines"][0]["asset_id"] == tracked_asset["id"]
    assert second_response.status_code == 409

    audit_response = client.get("/audit/logs", headers=headers)

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["entity_type"] == "booking"
    assert audit_response.json()[0]["action"] == "create"


def test_availability_preview_reports_tracked_conflict(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Tightrope Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking_payload = {
        "title": "Existing booking",
        "starts_at": BOOKING_START.isoformat(),
        "ends_at": BOOKING_END.isoformat(),
        "lines": [{"asset_id": tracked_asset["id"]}],
    }
    client.post("/bookings", json=booking_payload, headers=headers)

    response = client.post(
        "/bookings/availability",
        json={**booking_payload, "title": "Preview only"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["lines"][0]["available"] is False
    assert "already booked" in response.json()["lines"][0]["reason"]


def test_booking_rejects_stock_overbooking(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Main Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Flower Sticks", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 5,
        },
        headers=headers,
    )

    first_response = client.post(
        "/bookings",
        json={
            "title": "Group A",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {
                    "asset_id": stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 3,
                }
            ],
        },
        headers=headers,
    )
    second_response = client.post(
        "/bookings",
        json={
            "title": "Group B",
            "starts_at": (BOOKING_START + timedelta(hours=1)).isoformat(),
            "ends_at": (BOOKING_END - timedelta(hours=1)).isoformat(),
            "lines": [
                {
                    "asset_id": stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 3,
                }
            ],
        },
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_availability_preview_reports_stock_quantity(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Prop Room", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Scarves", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 8,
        },
        headers=headers,
    )
    client.post(
        "/bookings",
        json={
            "title": "Booked scarves",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {
                    "asset_id": stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 5,
                }
            ],
        },
        headers=headers,
    )

    response = client.post(
        "/bookings/availability",
        json={
            "title": "Preview scarves",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {
                    "asset_id": stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 4,
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["lines"][0]["available_quantity"] == 3


def test_cancelled_booking_releases_tracked_asset(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Trampoline", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking_payload = {
        "title": "Camp",
        "starts_at": BOOKING_START.isoformat(),
        "ends_at": BOOKING_END.isoformat(),
        "lines": [{"asset_id": tracked_asset["id"]}],
    }
    booking = client.post("/bookings", json=booking_payload, headers=headers).json()

    cancel_response = client.post(f"/bookings/{booking['id']}/cancel", headers=headers)
    new_response = client.post(
        "/bookings",
        json={**booking_payload, "title": "Replacement camp"},
        headers=headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
    assert new_response.status_code == 200

    audit_response = client.get("/audit/logs", headers=headers)

    assert audit_response.status_code == 200
    assert any(
        entry["summary"].startswith("Cancelled booking") for entry in audit_response.json()
    )
