from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import hash_password
from inventory_booking_api.main import app
from inventory_booking_api.models import Base
from inventory_booking_api.settings import Settings, get_settings
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User
from inventory_booking_api.users.router import _failed_login_attempts

ADMIN_EMAIL = "admin@example.org"
ADMIN_PASSWORD = "correct horse battery staple"
USER_EMAIL = "user@example.org"
USER_PASSWORD = "user password 123"
BOOKING_START = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
BOOKING_END = BOOKING_START + timedelta(days=3)


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient]:
    settings = get_settings()
    original_upload_dir = settings.asset_upload_dir
    original_location_upload_dir = settings.location_upload_dir
    settings.asset_upload_dir = str(tmp_path / "asset-uploads")
    settings.location_upload_dir = str(tmp_path / "location-uploads")
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

    _failed_login_attempts.clear()
    asyncio.run(create_schema())
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    _failed_login_attempts.clear()
    settings.asset_upload_dir = original_upload_dir
    settings.location_upload_dir = original_location_upload_dir
    asyncio.run(drop_schema())


def login(
    client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD
) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    csrf_token = client.cookies.get("inventory_booking_csrf")
    assert csrf_token is not None
    return {"X-CSRF-Token": csrf_token}


def image_bytes(format_name: str) -> bytes:
    image = Image.new("RGB", (2, 2), color=(255, 0, 0))
    output = BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()


def test_write_endpoints_require_session(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "Juggling"})

    assert response.status_code == 401


def test_domain_read_endpoints_require_session(client: TestClient) -> None:
    list_paths = [
        "/categories",
        "/locations",
        "/assets",
        "/stock-levels",
        "/bookings",
        "/checkouts",
        "/returns",
    ]
    detail_paths = [
        "/categories/00000000-0000-0000-0000-000000000001",
        "/locations/00000000-0000-0000-0000-000000000001",
        "/assets/00000000-0000-0000-0000-000000000001",
        "/stock-levels/00000000-0000-0000-0000-000000000001",
        "/bookings/00000000-0000-0000-0000-000000000001",
        "/checkouts/00000000-0000-0000-0000-000000000001",
        "/returns/00000000-0000-0000-0000-000000000001",
    ]

    for path in [*list_paths, *detail_paths]:
        response = client.get(path)

        assert response.status_code == 401, path


def test_security_headers_are_applied(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "same-origin"


def test_session_mutations_require_csrf_token(client: TestClient) -> None:
    login(client)

    response = client.post("/categories", json={"name": "Juggling"})

    assert response.status_code == 403


def test_session_mutations_reject_untrusted_origin(client: TestClient) -> None:
    headers = login(client)

    response = client.post(
        "/categories",
        json={"name": "Juggling"},
        headers={**headers, "Origin": "https://evil.example.org"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid request origin."


def test_login_me_and_logout(client: TestClient) -> None:
    csrf_headers = login(client)

    me_response = client.get("/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == ADMIN_EMAIL

    logout_response = client.post("/auth/logout", headers=csrf_headers)

    assert logout_response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_current_user_can_update_account(client: TestClient) -> None:
    csrf_headers = login(client)

    update_response = client.patch(
        "/auth/me",
        json={
            "email": "renamed-admin@example.org",
            "display_name": "Renamed Admin",
            "password": "new correct horse password",
        },
        headers=csrf_headers,
    )
    logout_response = client.post("/auth/logout", headers=csrf_headers)
    login_headers = login(client, "renamed-admin@example.org", "new correct horse password")
    me_response = client.get("/auth/me", headers=login_headers)

    assert update_response.status_code == 200
    assert update_response.json()["email"] == "renamed-admin@example.org"
    assert update_response.json()["display_name"] == "Renamed Admin"
    assert update_response.json()["role"] == "admin"
    assert logout_response.status_code == 204
    assert me_response.json()["display_name"] == "Renamed Admin"


def test_invalid_login_is_rejected(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})

    assert response.status_code == 401


def test_login_rate_limit_rejects_repeated_failures(client: TestClient) -> None:
    for _ in range(5):
        response = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})

        assert response.status_code == 401

    limited_response = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "still wrong"}
    )

    assert limited_response.status_code == 429


def test_production_settings_reject_local_defaults() -> None:
    with pytest.raises(ValidationError, match="Unsafe production settings"):
        Settings(app_env="production")


def test_production_settings_accept_safe_values() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://inventory:secret@example.org:5432/inventory_booking",
        internal_api_token="not-the-local-token",
        session_cookie_secure=True,
        cors_origins="https://inventory.example.org",
    )

    assert settings.app_env == "production"


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


def test_deactivating_user_revokes_existing_sessions(client: TestClient) -> None:
    with TestClient(app) as user_client:
        login(user_client, USER_EMAIL, USER_PASSWORD)
        assert user_client.get("/auth/me").status_code == 200

        admin_headers = login(client)
        users = client.get("/users", headers=admin_headers).json()
        user_id = next(user["id"] for user in users if user["email"] == USER_EMAIL)
        update_response = client.patch(
            f"/users/{user_id}",
            headers=admin_headers,
            json={"is_active": False},
        )

        assert update_response.status_code == 200
        assert user_client.get("/auth/me").status_code == 401


def test_normal_user_cannot_manage_users(client: TestClient) -> None:
    headers = login(client, USER_EMAIL, USER_PASSWORD)

    response = client.get("/users", headers=headers)

    assert response.status_code == 403


def test_normal_user_cannot_read_audit_logs(client: TestClient) -> None:
    headers = login(client, USER_EMAIL, USER_PASSWORD)

    response = client.get("/audit/logs", headers=headers)

    assert response.status_code == 403


def test_normal_user_cannot_perform_admin_only_mutations(client: TestClient) -> None:
    admin_headers = login(client)
    asset = client.post(
        "/assets",
        json={"name": "Admin Asset", "asset_type": "tracked"},
        headers=admin_headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Admin booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": asset["id"], "quantity": 1}],
        },
        headers=admin_headers,
    ).json()
    assert client.post("/auth/logout", headers=admin_headers).status_code == 204

    user_headers = login(client, USER_EMAIL, USER_PASSWORD)

    assert (
        client.post("/categories", json={"name": "User Category"}, headers=user_headers).status_code
        == 403
    )
    assert client.delete(f"/assets/{asset['id']}", headers=user_headers).status_code == 403
    assert client.delete(f"/bookings/{booking['id']}", headers=user_headers).status_code == 403


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


def test_create_and_update_person(client: TestClient) -> None:
    headers = login(client)

    create_response = client.post(
        "/persons",
        json={
            "display_name": "External Trainer",
            "person_type": "external",
            "email": "TRAINER@example.org",
            "phone": "12345",
            "notes": "Rents juggling material.",
        },
        headers=headers,
    )
    created = create_response.json()
    update_response = client.patch(
        f"/persons/{created['id']}",
        json={"display_name": "External Trainer Updated", "person_type": "team"},
        headers=headers,
    )
    list_response = client.get("/persons", headers=headers)

    assert create_response.status_code == 200
    assert created["email"] == "trainer@example.org"
    assert update_response.status_code == 200
    assert update_response.json()["display_name"] == "External Trainer Updated"
    assert update_response.json()["person_type"] == "team"
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == created["id"]


def test_location_can_reference_responsible_person(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Storage Responsible", "person_type": "team"},
        headers=headers,
    ).json()

    location_response = client.post(
        "/locations",
        json={
            "name": "Responsible Storage",
            "type": "storage",
            "responsible_person_id": person["id"],
        },
        headers=headers,
    )

    assert location_response.status_code == 200
    assert location_response.json()["responsible_person_id"] == person["id"]


def test_delete_person_clears_booking_and_location_references(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Delete Person", "person_type": "external"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Delete Person Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    location = client.post(
        "/locations",
        json={
            "name": "Delete Person Storage",
            "type": "storage",
            "responsible_person_id": person["id"],
        },
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Delete Person Booking",
            "person_id": person["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()

    delete_response = client.delete(f"/persons/{person['id']}", headers=headers)
    booking_response = client.get(f"/bookings/{booking['id']}", headers=headers)
    location_response = client.get(f"/locations/{location['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert booking_response.json()["person_id"] is None
    assert location_response.json()["responsible_person_id"] is None
    assert client.get(f"/persons/{person['id']}", headers=headers).status_code == 404


def test_delete_location_clears_inventory_references(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Delete Location Storage", "type": "storage"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={
            "name": "Delete Location Rig",
            "asset_type": "tracked",
            "home_location_id": location["id"],
            "current_location_id": location["id"],
        },
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Delete Location Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={"asset_id": stock_asset["id"], "location_id": location["id"], "quantity_total": 6},
        headers=headers,
    )

    delete_response = client.delete(f"/locations/{location['id']}", headers=headers)
    asset_response = client.get(f"/assets/{tracked_asset['id']}", headers=headers)
    stock_levels_response = client.get("/stock-levels", headers=headers)

    assert delete_response.status_code == 204
    assert asset_response.json()["home_location_id"] is None
    assert asset_response.json()["current_location_id"] is None
    assert all(level["location_id"] != location["id"] for level in stock_levels_response.json())
    assert client.get(f"/locations/{location['id']}", headers=headers).status_code == 404


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


def test_delete_unused_asset_removes_definition(client: TestClient) -> None:
    headers = login(client)
    asset = client.post(
        "/assets",
        json={"name": "Delete Unused Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    delete_response = client.delete(f"/assets/{asset['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert client.get(f"/assets/{asset['id']}", headers=headers).status_code == 404


def test_delete_asset_with_booking_history_is_rejected(client: TestClient) -> None:
    headers = login(client)
    asset = client.post(
        "/assets",
        json={"name": "Delete Protected Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    client.post(
        "/bookings",
        json={
            "title": "Delete Protected Booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": asset["id"]}],
        },
        headers=headers,
    )

    delete_response = client.delete(f"/assets/{asset['id']}", headers=headers)

    assert delete_response.status_code == 409
    assert "historical references" in delete_response.json()["detail"]["message"]
    assert client.get(f"/assets/{asset['id']}", headers=headers).status_code == 200


def test_asset_description_is_separate_from_notes(client: TestClient) -> None:
    headers = login(client)
    asset = client.post(
        "/assets",
        json={
            "name": "Described Rig",
            "asset_type": "tracked",
            "description": "Public recognition text.",
            "notes": "Internal handling note.",
        },
        headers=headers,
    ).json()

    update_response = client.patch(
        f"/assets/{asset['id']}",
        json={"description": "Updated visible description.", "notes": "Updated private note."},
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated visible description."
    assert update_response.json()["notes"] == "Updated private note."


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


def test_asset_image_upload_fetch_replace_and_delete(client: TestClient) -> None:
    headers = login(client)
    asset = client.post(
        "/assets",
        json={"name": "Photo Aerial Stand", "asset_type": "tracked"},
        headers=headers,
    ).json()
    webp_bytes = image_bytes("WEBP")

    upload_response = client.post(
        f"/assets/{asset['id']}/image",
        files={"file": ("asset.webp", webp_bytes, "image/webp")},
        headers=headers,
    )

    assert upload_response.status_code == 200
    created = upload_response.json()
    assert created["asset_id"] == asset["id"]
    assert created["mime_type"] == "image/webp"
    assert created["size_bytes"] > 0
    assert created["width"] == 2
    assert created["height"] == 2

    list_response = client.get("/assets/images", headers=headers)
    content_response = client.get(f"/assets/{asset['id']}/image/content", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()[0]["asset_id"] == asset["id"]
    assert content_response.status_code == 200
    assert content_response.headers["content-type"].startswith("image/webp")
    assert len(content_response.content) == created["size_bytes"]

    replacement_bytes = image_bytes("JPEG")
    replace_response = client.post(
        f"/assets/{asset['id']}/image",
        files={"file": ("asset.jpg", replacement_bytes, "image/jpeg")},
        headers=headers,
    )
    replacement_content_response = client.get(
        f"/assets/{asset['id']}/image/content", headers=headers
    )
    delete_response = client.delete(f"/assets/{asset['id']}/image", headers=headers)
    missing_response = client.get(f"/assets/{asset['id']}/image", headers=headers)
    audit_response = client.get("/audit/logs", headers=headers)

    assert replace_response.status_code == 200
    assert replace_response.json()["mime_type"] == "image/jpeg"
    assert replace_response.json()["width"] == 2
    assert replace_response.json()["height"] == 2
    assert replacement_content_response.status_code == 200
    assert len(replacement_content_response.content) == replace_response.json()["size_bytes"]
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404
    assert any(entry["entity_type"] == "asset_image" for entry in audit_response.json())


def test_asset_image_upload_rejects_unsupported_content(client: TestClient) -> None:
    headers = login(client)
    asset = client.post(
        "/assets",
        json={"name": "Rejected Photo Asset", "asset_type": "tracked"},
        headers=headers,
    ).json()

    response = client.post(
        f"/assets/{asset['id']}/image",
        files={"file": ("asset.svg", b"<svg></svg>", "image/svg+xml")},
        headers=headers,
    )

    assert response.status_code == 400


def test_location_image_upload_fetch_replace_and_delete(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Photo Storage", "type": "storage"},
        headers=headers,
    ).json()
    webp_bytes = image_bytes("WEBP")

    upload_response = client.post(
        f"/locations/{location['id']}/image",
        files={"file": ("location.webp", webp_bytes, "image/webp")},
        headers=headers,
    )

    assert upload_response.status_code == 200
    created = upload_response.json()
    assert created["location_id"] == location["id"]
    assert created["mime_type"] == "image/webp"
    assert created["size_bytes"] > 0
    assert created["width"] == 2
    assert created["height"] == 2

    list_response = client.get("/locations/images", headers=headers)
    content_response = client.get(f"/locations/{location['id']}/image/content", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()[0]["location_id"] == location["id"]
    assert content_response.status_code == 200
    assert content_response.headers["content-type"].startswith("image/webp")
    assert len(content_response.content) == created["size_bytes"]

    replacement_bytes = image_bytes("JPEG")
    replace_response = client.post(
        f"/locations/{location['id']}/image",
        files={"file": ("location.jpg", replacement_bytes, "image/jpeg")},
        headers=headers,
    )
    replacement_content_response = client.get(
        f"/locations/{location['id']}/image/content",
        headers=headers,
    )
    delete_response = client.delete(f"/locations/{location['id']}/image", headers=headers)
    missing_response = client.get(f"/locations/{location['id']}/image", headers=headers)
    audit_response = client.get("/audit/logs", headers=headers)

    assert replace_response.status_code == 200
    assert replace_response.json()["mime_type"] == "image/jpeg"
    assert replace_response.json()["width"] == 2
    assert replace_response.json()["height"] == 2
    assert replacement_content_response.status_code == 200
    assert len(replacement_content_response.content) == replace_response.json()["size_bytes"]
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404
    assert any(entry["entity_type"] == "location_image" for entry in audit_response.json())


def test_location_image_upload_rejects_unsupported_content(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Rejected Photo Location", "type": "storage"},
        headers=headers,
    ).json()

    response = client.post(
        f"/locations/{location['id']}/image",
        files={"file": ("location.svg", b"<svg></svg>", "image/svg+xml")},
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


def test_stock_level_can_be_reduced_to_zero(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Adjustment Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Adjustment Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    stock_level = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 3,
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"/stock-levels/{stock_level['id']}",
        json={"quantity_total": 0},
        headers=headers,
    )
    list_response = client.get("/stock-levels")

    assert response.status_code == 200
    assert response.json()["quantity_total"] == 0
    assert not any(entry["id"] == stock_level["id"] for entry in list_response.json())


def test_user_can_read_item_events_but_not_audit_logs(client: TestClient) -> None:
    admin_headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "User Visible History Rig", "asset_type": "tracked"},
        headers=admin_headers,
    ).json()
    client.cookies.clear()
    user_headers = login(client, email=USER_EMAIL, password=USER_PASSWORD)

    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": tracked_asset["id"]},
        headers=user_headers,
    )
    audit_response = client.get("/audit/logs", headers=user_headers)

    assert event_response.status_code == 200
    assert event_response.json()[0]["asset_id"] == tracked_asset["id"]
    assert audit_response.status_code == 403


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


def test_booking_exposes_created_at_and_requester(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Created At Booking Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    create_response = client.post(
        "/bookings",
        json={
            "title": "Created timestamp booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    )
    created = create_response.json()
    list_response = client.get("/bookings", headers=headers)
    detail_response = client.get(f"/bookings/{created['id']}", headers=headers)

    assert create_response.status_code == 200
    assert created["requested_by_user_id"]
    assert created["created_at"]
    assert list_response.status_code == 200
    assert list_response.json()[0]["created_at"] == created["created_at"]
    assert detail_response.status_code == 200
    assert detail_response.json()["created_at"] == created["created_at"]


def test_delete_booking_removes_booking_and_lines(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Delete Booking Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Delete Booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()

    delete_response = client.delete(f"/bookings/{booking['id']}", headers=headers)
    list_response = client.get("/bookings", headers=headers)

    assert delete_response.status_code == 204
    assert client.get(f"/bookings/{booking['id']}", headers=headers).status_code == 404
    assert all(entry["id"] != booking["id"] for entry in list_response.json())


def test_booking_update_changes_status_person_and_dates(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Updated Booking Person", "person_type": "external"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Updated Booking Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Editable booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()
    next_start = BOOKING_END + timedelta(days=2)
    next_end = next_start + timedelta(days=1)

    response = client.patch(
        f"/bookings/{booking['id']}",
        json={
            "status": "completed",
            "person_id": person["id"],
            "starts_at": next_start.isoformat(),
            "ends_at": next_end.isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["person_id"] == person["id"]
    assert response.json()["starts_at"].startswith(next_start.isoformat().replace("+00:00", ""))


def test_booking_update_rejects_new_tracked_conflict(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Update Conflict Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    first = client.post(
        "/bookings",
        json={
            "title": "First update booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()
    second_start = BOOKING_END + timedelta(days=2)
    second_end = second_start + timedelta(days=1)
    second = client.post(
        "/bookings",
        json={
            "title": "Second update booking",
            "starts_at": second_start.isoformat(),
            "ends_at": second_end.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()

    response = client.patch(
        f"/bookings/{first['id']}",
        json={"starts_at": second_start.isoformat(), "ends_at": second_end.isoformat()},
        headers=headers,
    )
    unchanged_response = client.get(f"/bookings/{first['id']}", headers=headers)

    assert second["id"] != first["id"]
    assert response.status_code == 409
    assert unchanged_response.json()["starts_at"] == first["starts_at"]


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
    assert any(entry["summary"].startswith("Cancelled booking") for entry in audit_response.json())


def test_checkout_tracked_booking_updates_asset_and_audit(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Checkout Trampoline", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Checkout camp",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()

    checkout_response = client.post(
        "/checkouts",
        json={"booking_id": booking["id"], "condition_out": "good"},
        headers=headers,
    )
    asset_response = client.get(f"/assets/{tracked_asset['id']}")
    audit_response = client.get("/audit/logs", headers=headers)

    assert checkout_response.status_code == 200
    assert checkout_response.json()["booking_id"] == booking["id"]
    assert checkout_response.json()["lines"][0]["condition_out"] == "good"
    assert asset_response.json()["status"] == "checked_out"
    assert asset_response.json()["condition"] == "good"
    assert any(entry["entity_type"] == "checkout" for entry in audit_response.json())


def test_duplicate_checkout_is_rejected(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Duplicate Checkout Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Duplicate checkout",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()

    first_response = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers)
    second_response = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_stock_checkout_rejects_insufficient_current_stock(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Checkout Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Checkout Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    stock_level = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 5,
        },
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Stock checkout",
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
    ).json()
    client.patch(
        f"/stock-levels/{stock_level['id']}",
        json={"quantity_total": 3},
        headers=headers,
    )

    response = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers)

    assert response.status_code == 409


def test_tracked_return_damaged_updates_asset_and_audit(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Return Aerial Stand", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Damaged return",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()
    checkout = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers).json()
    checkout_line_id = checkout["lines"][0]["id"]

    return_response = client.post(
        "/returns",
        json={
            "checkout_id": checkout["id"],
            "lines": [{"checkout_line_id": checkout_line_id, "condition_in": "damaged"}],
        },
        headers=headers,
    )
    asset_response = client.get(f"/assets/{tracked_asset['id']}")
    audit_response = client.get("/audit/logs", headers=headers)

    assert return_response.status_code == 200
    assert return_response.json()["lines"][0]["condition_in"] == "damaged"
    assert asset_response.json()["status"] == "damaged"
    assert asset_response.json()["condition"] == "damaged"
    assert any(entry["entity_type"] == "return" for entry in audit_response.json())


def test_stock_partial_return_updates_checkout_and_stock(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Return Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Return Scarves", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    stock_level = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 10,
        },
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Partial stock return",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {
                    "asset_id": stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 6,
                }
            ],
        },
        headers=headers,
    ).json()
    checkout = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers).json()
    checkout_line_id = checkout["lines"][0]["id"]

    return_response = client.post(
        "/returns",
        json={
            "checkout_id": checkout["id"],
            "lines": [{"checkout_line_id": checkout_line_id, "quantity": 2}],
        },
        headers=headers,
    )
    checkout_response = client.get(f"/checkouts/{checkout['id']}")
    stock_response = client.get(f"/stock-levels/{stock_level['id']}")

    assert return_response.status_code == 200
    assert checkout_response.json()["status"] == "partially_returned"
    assert checkout_response.json()["lines"][0]["quantity_returned"] == 2
    assert stock_response.json()["quantity_checked_out"] == 4


def test_stock_return_rejects_over_return(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Over Return Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Over Return Clubs", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 4,
        },
        headers=headers,
    )
    booking = client.post(
        "/bookings",
        json={
            "title": "Over return",
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
    ).json()
    checkout = client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers).json()
    checkout_line_id = checkout["lines"][0]["id"]

    response = client.post(
        "/returns",
        json={
            "checkout_id": checkout["id"],
            "lines": [{"checkout_line_id": checkout_line_id, "quantity": 5}],
        },
        headers=headers,
    )

    assert response.status_code == 409


def test_transfer_tracked_asset_updates_location_and_audit(client: TestClient) -> None:
    headers = login(client)
    source_location = client.post(
        "/locations",
        json={"name": "Transfer Source", "type": "storage"},
        headers=headers,
    ).json()
    destination_location = client.post(
        "/locations",
        json={"name": "Transfer Destination", "type": "room"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={
            "name": "Transfer Trampoline",
            "asset_type": "tracked",
            "current_location_id": source_location["id"],
        },
        headers=headers,
    ).json()

    response = client.post(
        f"/assets/{tracked_asset['id']}/transfer",
        json={"to_location_id": destination_location["id"], "notes": "Moved to workshop room"},
        headers=headers,
    )
    audit_response = client.get("/audit/logs", headers=headers)
    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": tracked_asset["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["current_location_id"] == destination_location["id"]
    assert any(entry["summary"].startswith("Transferred asset") for entry in audit_response.json())
    assert event_response.json()[0]["event_type"] == "moved"


def test_transfer_checked_out_tracked_asset_is_rejected(client: TestClient) -> None:
    headers = login(client)
    destination_location = client.post(
        "/locations",
        json={"name": "Rejected Transfer Destination", "type": "room"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Checked Out Transfer Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Checked out transfer",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()
    client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers)

    response = client.post(
        f"/assets/{tracked_asset['id']}/transfer",
        json={"to_location_id": destination_location["id"]},
        headers=headers,
    )

    assert response.status_code == 409


def test_transfer_stock_moves_available_quantity(client: TestClient) -> None:
    headers = login(client)
    source_location = client.post(
        "/locations",
        json={"name": "Stock Transfer Source", "type": "storage"},
        headers=headers,
    ).json()
    destination_location = client.post(
        "/locations",
        json={"name": "Stock Transfer Destination", "type": "room"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Transfer Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": source_location["id"],
            "quantity_total": 10,
        },
        headers=headers,
    )

    response = client.post(
        "/stock-levels/transfer",
        json={
            "asset_id": stock_asset["id"],
            "from_location_id": source_location["id"],
            "to_location_id": destination_location["id"],
            "quantity": 4,
        },
        headers=headers,
    )

    assert response.status_code == 200
    quantities = {entry["location_id"]: entry["quantity_total"] for entry in response.json()}
    assert quantities[source_location["id"]] == 6
    assert quantities[destination_location["id"]] == 4


def test_transfer_stock_rejects_checked_out_quantity(client: TestClient) -> None:
    headers = login(client)
    source_location = client.post(
        "/locations",
        json={"name": "Checked Stock Source", "type": "storage"},
        headers=headers,
    ).json()
    destination_location = client.post(
        "/locations",
        json={"name": "Checked Stock Destination", "type": "room"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Checked Stock Transfer", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    stock_level = client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": source_location["id"],
            "quantity_total": 5,
        },
        headers=headers,
    ).json()
    client.patch(
        f"/stock-levels/{stock_level['id']}",
        json={"quantity_checked_out": 3},
        headers=headers,
    )

    response = client.post(
        "/stock-levels/transfer",
        json={
            "asset_id": stock_asset["id"],
            "from_location_id": source_location["id"],
            "to_location_id": destination_location["id"],
            "quantity": 3,
        },
        headers=headers,
    )

    assert response.status_code == 409


def test_maintenance_lifecycle_updates_asset_and_events(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Maintenance Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    start_response = client.post(
        f"/assets/{tracked_asset['id']}/maintenance/start",
        json={"notes": "Inspect welds"},
        headers=headers,
    )
    complete_response = client.post(
        f"/assets/{tracked_asset['id']}/maintenance/complete",
        json={"condition": "good", "notes": "Ready"},
        headers=headers,
    )
    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": tracked_asset["id"]},
        headers=headers,
    )

    assert start_response.status_code == 200
    assert start_response.json()["status"] == "maintenance"
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "available"
    assert complete_response.json()["condition"] == "good"
    event_types = [entry["event_type"] for entry in event_response.json()]
    assert "maintenance_started" in event_types
    assert "maintenance_completed" in event_types


def test_checked_out_asset_cannot_enter_maintenance(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Busy Maintenance Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    booking = client.post(
        "/bookings",
        json={
            "title": "Busy maintenance",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    ).json()
    client.post("/checkouts", json={"booking_id": booking["id"]}, headers=headers)

    response = client.post(
        f"/assets/{tracked_asset['id']}/maintenance/start",
        json={},
        headers=headers,
    )

    assert response.status_code == 409


def test_asset_state_change_marks_lost_and_retired(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "State Change Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    lost_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "lost", "notes": "Missing after workshop"},
        headers=headers,
    )
    retired_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "retired", "condition": "damaged"},
        headers=headers,
    )
    reactivate_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "available"},
        headers=headers,
    )

    assert lost_response.status_code == 200
    assert lost_response.json()["status"] == "lost"
    assert retired_response.status_code == 200
    assert retired_response.json()["status"] == "retired"
    assert reactivate_response.status_code == 409


def test_normal_user_cannot_mark_asset_lost_or_retired(client: TestClient) -> None:
    admin_headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Protected State Rig", "asset_type": "tracked"},
        headers=admin_headers,
    ).json()
    assert client.post("/auth/logout", headers=admin_headers).status_code == 204
    user_headers = login(client, USER_EMAIL, USER_PASSWORD)

    damaged_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "damaged", "condition": "damaged"},
        headers=user_headers,
    )
    lost_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "lost"},
        headers=user_headers,
    )
    retired_response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "retired"},
        headers=user_headers,
    )

    assert damaged_response.status_code == 200
    assert lost_response.status_code == 403
    assert retired_response.status_code == 403


def test_asset_state_change_rejects_unsupported_status(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Unsupported State Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()

    response = client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "checked_out"},
        headers=headers,
    )

    assert response.status_code == 400


def test_qr_create_assign_and_resolve_tracked_asset(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "QR Aerial Stand", "asset_type": "tracked"},
        headers=headers,
    ).json()

    qr_response = client.post("/qr-codes", json={"label": "Label 001"}, headers=headers)
    token = qr_response.json()["token"]
    assign_response = client.post(
        f"/qr-codes/{token}/assign",
        json={"asset_id": tracked_asset["id"], "notes": "Applied sticker"},
        headers=headers,
    )
    resolve_response = client.get(f"/qr-codes/{token}/resolve", headers=headers)
    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": tracked_asset["id"]},
        headers=headers,
    )

    assert qr_response.status_code == 200
    assert len(token) >= 24
    assert assign_response.status_code == 200
    assert assign_response.json()["asset_id"] == tracked_asset["id"]
    assert resolve_response.status_code == 200
    assert resolve_response.json()["assigned"] is True
    assert resolve_response.json()["asset"]["id"] == tracked_asset["id"]
    assert event_response.json()[0]["event_type"] == "qr_assigned"


def test_qr_assignment_accepts_stock_asset(client: TestClient) -> None:
    headers = login(client)
    stock_asset = client.post(
        "/assets",
        json={"name": "QR Stock Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    token = client.post("/qr-codes", json={}, headers=headers).json()["token"]

    response = client.post(
        f"/qr-codes/{token}/assign",
        json={"asset_id": stock_asset["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["asset_id"] == stock_asset["id"]


def test_asset_qr_endpoint_creates_and_returns_existing_qr(client: TestClient) -> None:
    headers = login(client)
    stock_asset = client.post(
        "/assets",
        json={"name": "Asset QR Stock Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()

    missing_response = client.get(f"/assets/{stock_asset['id']}/qr", headers=headers)
    create_response = client.post(f"/assets/{stock_asset['id']}/qr", headers=headers)
    second_create_response = client.post(f"/assets/{stock_asset['id']}/qr", headers=headers)
    get_response = client.get(f"/assets/{stock_asset['id']}/qr", headers=headers)
    event_response = client.get(
        "/audit/item-events",
        params={"asset_id": stock_asset["id"]},
        headers=headers,
    )

    assert missing_response.status_code == 404
    assert create_response.status_code == 200
    assert create_response.json()["asset_id"] == stock_asset["id"]
    assert len(create_response.json()["token"]) >= 24
    assert second_create_response.status_code == 200
    assert second_create_response.json()["id"] == create_response.json()["id"]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == create_response.json()["id"]
    assert event_response.json()[0]["event_type"] == "qr_assigned"


def test_qr_assignment_rejects_lost_asset(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "QR Lost Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    client.post(
        f"/assets/{tracked_asset['id']}/state",
        json={"status": "lost"},
        headers=headers,
    )
    token = client.post("/qr-codes", json={}, headers=headers).json()["token"]

    response = client.post(
        f"/qr-codes/{token}/assign",
        json={"asset_id": tracked_asset["id"]},
        headers=headers,
    )

    assert response.status_code == 409


def test_qr_endpoints_require_session_and_do_not_enumerate(client: TestClient) -> None:
    unauthenticated_response = client.post("/qr-codes", json={})
    headers = login(client)
    missing_response = client.get("/qr-codes/not-a-real-token/resolve", headers=headers)

    assert unauthenticated_response.status_code == 401
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "QR label not found."


def test_basket_hold_blocks_other_user_booking(client: TestClient) -> None:
    admin_headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Held Basket Person", "person_type": "external"},
        headers=admin_headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Held Aerial Stand", "asset_type": "tracked"},
        headers=admin_headers,
    ).json()
    basket = client.post(
        "/basket",
        json={
            "title": "Held workshop basket",
            "person_id": person["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
        },
        headers=admin_headers,
    ).json()
    line_response = client.post(
        f"/basket/{basket['id']}/lines",
        json={"asset_id": tracked_asset["id"]},
        headers=admin_headers,
    )

    client.cookies.clear()
    user_headers = login(client, USER_EMAIL, USER_PASSWORD)
    booking_response = client.post(
        "/bookings",
        json={
            "title": "Conflicting real booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=user_headers,
    )

    assert line_response.status_code == 200
    assert line_response.json()["lines"][0]["asset_id"] == tracked_asset["id"]
    assert booking_response.status_code == 409
    assert "temporarily held" in booking_response.json()["detail"]


def test_confirm_basket_creates_booking_and_clears_active_basket(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Confirmed Basket Person", "person_type": "external"},
        headers=headers,
    ).json()
    tracked_asset = client.post(
        "/assets",
        json={"name": "Confirm Basket Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    basket = client.post(
        "/basket",
        json={
            "title": "Confirmed basket booking",
            "person_id": person["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "notes": "Bundle for project week",
        },
        headers=headers,
    ).json()
    client.post(
        f"/basket/{basket['id']}/lines",
        json={"asset_id": tracked_asset["id"]},
        headers=headers,
    )

    confirm_response = client.post(f"/basket/{basket['id']}/confirm", headers=headers)
    active_response = client.get("/basket/active", headers=headers)

    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["title"] == "Confirmed basket booking"
    assert confirmed["person_id"] == person["id"]
    assert confirmed["lines"][0]["asset_id"] == tracked_asset["id"]
    assert active_response.status_code == 200
    assert active_response.json() is None


def test_basket_lines_keep_independent_dates(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Mixed Date Person", "person_type": "external"},
        headers=headers,
    ).json()
    location = client.post(
        "/locations",
        json={"name": "Mixed Date Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Mixed Date Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 9,
        },
        headers=headers,
    )
    first_start = BOOKING_START
    first_end = BOOKING_START + timedelta(days=2)
    second_start = BOOKING_START + timedelta(days=10)
    second_end = second_start + timedelta(days=3)
    basket = client.post(
        "/basket",
        json={
            "title": "Mixed date basket",
            "person_id": person["id"],
            "starts_at": first_start.isoformat(),
            "ends_at": first_end.isoformat(),
        },
        headers=headers,
    ).json()

    first_line_response = client.post(
        f"/basket/{basket['id']}/lines",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "starts_at": first_start.isoformat(),
            "ends_at": first_end.isoformat(),
            "quantity": 4,
        },
        headers=headers,
    )
    second_line_response = client.post(
        f"/basket/{basket['id']}/lines",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "starts_at": second_start.isoformat(),
            "ends_at": second_end.isoformat(),
            "quantity": 4,
        },
        headers=headers,
    )
    confirm_response = client.post(f"/basket/{basket['id']}/confirm", headers=headers)

    assert first_line_response.status_code == 200
    assert len(first_line_response.json()["lines"]) == 1
    assert second_line_response.status_code == 200
    assert len(second_line_response.json()["lines"]) == 2
    basket_payload = second_line_response.json()
    assert basket_payload["starts_at"].startswith(first_start.strftime("%Y-%m-%dT%H:%M:%S"))
    assert basket_payload["ends_at"].startswith(second_end.strftime("%Y-%m-%dT%H:%M:%S"))
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert len(confirmed["lines"]) == 2
    assert {line["starts_at"][:19] for line in confirmed["lines"]} == {
        first_start.strftime("%Y-%m-%dT%H:%M:%S"),
        second_start.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def test_stock_availability_uses_max_concurrent_overlap(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Concurrent Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Concurrent Props", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 9,
        },
        headers=headers,
    )
    first_start = BOOKING_START
    first_end = BOOKING_START + timedelta(days=2)
    second_start = first_end
    second_end = second_start + timedelta(days=2)
    for index, (starts_at, ends_at) in enumerate(
        ((first_start, first_end), (second_start, second_end)),
        start=1,
    ):
        response = client.post(
            "/bookings",
            json={
                "title": f"Non-overlapping stock booking {index}",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
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
        assert response.status_code == 200

    preview_response = client.post(
        "/bookings/availability",
        json={
            "title": "Full range request",
            "starts_at": first_start.isoformat(),
            "ends_at": second_end.isoformat(),
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

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["available"] is True
    assert preview["lines"][0]["available_quantity"] == 4


def test_update_basket_line_changes_dates_and_quantity(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Editable Basket Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Editable Basket Props", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 9,
        },
        headers=headers,
    )
    basket = client.post(
        "/basket",
        json={
            "title": "Editable basket",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
        },
        headers=headers,
    ).json()
    line = client.post(
        f"/basket/{basket['id']}/lines",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity": 2,
        },
        headers=headers,
    ).json()["lines"][0]
    next_start = BOOKING_START + timedelta(days=5)
    next_end = next_start + timedelta(days=2)

    response = client.patch(
        f"/basket/{basket['id']}/lines/{line['id']}",
        json={
            "starts_at": next_start.isoformat(),
            "ends_at": next_end.isoformat(),
            "quantity": 4,
        },
        headers=headers,
    )

    assert response.status_code == 200
    updated_line = response.json()["lines"][0]
    assert updated_line["quantity"] == 4
    assert updated_line["starts_at"].startswith(next_start.strftime("%Y-%m-%dT%H:%M:%S"))
    assert updated_line["ends_at"].startswith(next_end.strftime("%Y-%m-%dT%H:%M:%S"))
    assert response.json()["starts_at"].startswith(next_start.strftime("%Y-%m-%dT%H:%M:%S"))
    assert response.json()["ends_at"].startswith(next_end.strftime("%Y-%m-%dT%H:%M:%S"))


def test_update_basket_line_rejects_unavailable_quantity(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Rejected Basket Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Rejected Basket Props", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 9,
        },
        headers=headers,
    )
    basket = client.post(
        "/basket",
        json={
            "title": "Rejected basket",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
        },
        headers=headers,
    ).json()
    first_line = client.post(
        f"/basket/{basket['id']}/lines",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "quantity": 6,
        },
        headers=headers,
    ).json()["lines"][0]
    second_line = client.post(
        f"/basket/{basket['id']}/lines",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "starts_at": (BOOKING_START + timedelta(days=5)).isoformat(),
            "ends_at": (BOOKING_END + timedelta(days=5)).isoformat(),
            "quantity": 4,
        },
        headers=headers,
    ).json()["lines"][1]

    response = client.patch(
        f"/basket/{basket['id']}/lines/{second_line['id']}",
        json={
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "quantity": 4,
        },
        headers=headers,
    )

    assert first_line["quantity"] == 6
    assert response.status_code == 409
    assert response.json()["detail"] == "Not enough stock is available for this time range."


def test_stock_availability_heatmap_reports_bookings_and_basket_holds(client: TestClient) -> None:
    headers = login(client)
    person = client.post(
        "/persons",
        json={"display_name": "Heatmap Basket Person", "person_type": "external"},
        headers=headers,
    ).json()
    location = client.post(
        "/locations",
        json={"name": "Heatmap Storage", "type": "storage"},
        headers=headers,
    ).json()
    booked_stock_asset = client.post(
        "/assets",
        json={"name": "Heatmap Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    held_stock_asset = client.post(
        "/assets",
        json={"name": "Heatmap Clubs", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    booked_tracked_asset = client.post(
        "/assets",
        json={
            "name": "Heatmap Aerial Stand",
            "asset_type": "tracked",
            "current_location_id": location["id"],
        },
        headers=headers,
    ).json()
    available_tracked_asset = client.post(
        "/assets",
        json={
            "name": "Heatmap Unicycle",
            "asset_type": "tracked",
            "current_location_id": location["id"],
        },
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": booked_stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 10,
        },
        headers=headers,
    )
    client.post(
        "/stock-levels",
        json={
            "asset_id": held_stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 8,
        },
        headers=headers,
    )
    client.post(
        "/bookings",
        json={
            "title": "Heatmap booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {
                    "asset_id": booked_stock_asset["id"],
                    "location_id": location["id"],
                    "quantity": 3,
                },
                {"asset_id": booked_tracked_asset["id"]},
            ],
        },
        headers=headers,
    )
    basket = client.post(
        "/basket",
        json={
            "title": "Heatmap basket",
            "person_id": person["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
        },
        headers=headers,
    ).json()
    client.post(
        f"/basket/{basket['id']}/lines",
        json={"asset_id": held_stock_asset["id"], "location_id": location["id"], "quantity": 2},
        headers=headers,
    )

    response = client.get(
        "/bookings/availability/heatmap",
        params={
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": (BOOKING_START + timedelta(days=1)).isoformat(),
            "bucket": "day",
            "location_id": location["id"],
        },
        headers=headers,
    )

    assert response.status_code == 200
    items = {item["asset_id"]: item for item in response.json()["items"]}
    booked_cell = items[booked_stock_asset["id"]]["cells"][0]
    held_cell = items[held_stock_asset["id"]]["cells"][0]
    booked_tracked_cell = items[booked_tracked_asset["id"]]["cells"][0]
    available_tracked_cell = items[available_tracked_asset["id"]]["cells"][0]
    assert items[booked_stock_asset["id"]]["asset_type"] == "stock"
    assert items[booked_tracked_asset["id"]]["asset_type"] == "tracked"
    assert booked_cell["total_quantity"] == 10
    assert booked_cell["reserved_quantity"] == 3
    assert booked_cell["held_quantity"] == 0
    assert booked_cell["available_quantity"] == 7
    assert held_cell["total_quantity"] == 8
    assert held_cell["reserved_quantity"] == 0
    assert held_cell["held_quantity"] == 2
    assert held_cell["available_quantity"] == 6
    assert booked_tracked_cell["total_quantity"] == 1
    assert booked_tracked_cell["reserved_quantity"] == 1
    assert booked_tracked_cell["held_quantity"] == 0
    assert booked_tracked_cell["available_quantity"] == 0
    assert available_tracked_cell["total_quantity"] == 1
    assert available_tracked_cell["reserved_quantity"] == 0
    assert available_tracked_cell["held_quantity"] == 0
    assert available_tracked_cell["available_quantity"] == 1

    multi_day_response = client.get(
        "/bookings/availability/heatmap",
        params={
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "bucket": "day",
            "location_id": location["id"],
        },
        headers=headers,
    )

    assert multi_day_response.status_code == 200
    multi_day_items = {item["asset_id"]: item for item in multi_day_response.json()["items"]}
    assert [
        cell["reserved_quantity"] for cell in multi_day_items[booked_stock_asset["id"]]["cells"]
    ] == [3, 3, 3]
    assert [
        cell["held_quantity"] for cell in multi_day_items[held_stock_asset["id"]]["cells"]
    ] == [2, 2, 2]
    assert [
        cell["available_quantity"]
        for cell in multi_day_items[booked_tracked_asset["id"]]["cells"]
    ] == [0, 0, 0]


def test_availability_days_reports_stock_conflicts(client: TestClient) -> None:
    headers = login(client)
    location = client.post(
        "/locations",
        json={"name": "Date Picker Storage", "type": "storage"},
        headers=headers,
    ).json()
    stock_asset = client.post(
        "/assets",
        json={"name": "Date Picker Balls", "asset_type": "stock", "unit_name": "piece"},
        headers=headers,
    ).json()
    client.post(
        "/stock-levels",
        json={
            "asset_id": stock_asset["id"],
            "location_id": location["id"],
            "quantity_total": 4,
        },
        headers=headers,
    )
    client.post(
        "/bookings",
        json={
            "title": "Date picker booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [
                {"asset_id": stock_asset["id"], "location_id": location["id"], "quantity": 3}
            ],
        },
        headers=headers,
    )

    response = client.get(
        "/bookings/availability/days",
        params={
            "asset_id": stock_asset["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": (BOOKING_START + timedelta(days=1)).isoformat(),
            "quantity": 2,
            "location_id": location["id"],
        },
        headers=headers,
    )

    assert response.status_code == 200
    day = response.json()["days"][0]
    assert day["available_quantity"] == 1
    assert day["requested_quantity"] == 2
    assert day["available"] is False


def test_availability_days_reports_tracked_asset_conflict(client: TestClient) -> None:
    headers = login(client)
    tracked_asset = client.post(
        "/assets",
        json={"name": "Date Picker Rig", "asset_type": "tracked"},
        headers=headers,
    ).json()
    client.post(
        "/bookings",
        json={
            "title": "Tracked date picker booking",
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": BOOKING_END.isoformat(),
            "lines": [{"asset_id": tracked_asset["id"]}],
        },
        headers=headers,
    )

    response = client.get(
        "/bookings/availability/days",
        params={
            "asset_id": tracked_asset["id"],
            "starts_at": BOOKING_START.isoformat(),
            "ends_at": (BOOKING_START + timedelta(days=1)).isoformat(),
            "quantity": 1,
        },
        headers=headers,
    )

    assert response.status_code == 200
    day = response.json()["days"][0]
    assert day["total_quantity"] == 1
    assert day["reserved_quantity"] == 1
    assert day["available_quantity"] == 0
    assert day["available"] is False
