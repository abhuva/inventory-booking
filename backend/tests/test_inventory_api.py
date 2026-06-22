from collections.abc import AsyncGenerator, Generator

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
            session.add(
                User(
                    email=ADMIN_EMAIL,
                    display_name="Admin",
                    role=UserRole.ADMIN,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    is_active=True,
                )
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


def login(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )

    assert response.status_code == 200


def test_write_endpoints_require_session(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "Juggling"})

    assert response.status_code == 401


def test_login_me_and_logout(client: TestClient) -> None:
    login_response = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )

    assert login_response.status_code == 200
    assert login_response.json()["role"] == "admin"

    me_response = client.get("/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == ADMIN_EMAIL

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong"},
    )

    assert response.status_code == 401


def test_create_and_list_category(client: TestClient) -> None:
    login(client)

    response = client.post(
        "/categories",
        json={"name": "Juggling", "description": "Balls, clubs, rings"},
    )

    assert response.status_code == 200
    created = response.json()
    assert created["name"] == "Juggling"

    list_response = client.get("/categories")

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == created["id"]


def test_create_location(client: TestClient) -> None:
    login(client)

    response = client.post(
        "/locations",
        json={"name": "Main Storage", "type": "storage"},
    )

    assert response.status_code == 200
    assert response.json()["type"] == "storage"


def test_asset_mode_validation(client: TestClient) -> None:
    login(client)

    tracked_response = client.post(
        "/assets",
        json={"name": "Aerial Stand 01", "asset_type": "tracked"},
    )
    invalid_stock_response = client.post(
        "/assets",
        json={"name": "Juggling Balls", "asset_type": "stock"},
    )

    assert tracked_response.status_code == 200
    assert tracked_response.json()["unit_name"] is None
    assert invalid_stock_response.status_code == 422


def test_stock_level_requires_stock_asset(client: TestClient) -> None:
    login(client)

    location = client.post("/locations", json={"name": "Main Storage", "type": "storage"}).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Trampoline", "asset_type": "tracked"},
    ).json()

    response = client.post(
        "/stock-levels",
        json={
            "asset_id": tracked_asset["id"],
            "location_id": location["id"],
            "quantity_total": 4,
        },
    )

    assert response.status_code == 400


def test_create_stock_level_for_stock_asset(client: TestClient) -> None:
    login(client)

    location = client.post("/locations", json={"name": "Main Storage", "type": "storage"}).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Juggling Balls", "asset_type": "stock", "unit_name": "piece"},
    ).json()

    response = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 12,
        },
    )

    assert response.status_code == 200
    assert response.json()["quantity_total"] == 12
