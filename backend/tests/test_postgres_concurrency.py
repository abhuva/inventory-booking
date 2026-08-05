import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from inventory_booking_api.bookings.commands import create_booking
from inventory_booking_api.bookings.models import Booking
from inventory_booking_api.bookings.schemas import BookingCreate, BookingLineCreate
from inventory_booking_api.checkouts.schemas import CheckoutCreate
from inventory_booking_api.checkouts.service import create_checkout
from inventory_booking_api.core.security import hash_password
from inventory_booking_api.inventory.asset_schemas import (
    StockLevelRead,
    StockLevelUpdate,
    StockTransfer,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.inventory.movement_commands import transfer_stock
from inventory_booking_api.inventory.stock_commands import update_stock_level
from inventory_booking_api.locations.models import Location
from inventory_booking_api.models import Base
from inventory_booking_api.returns.schemas import ReturnCreate, ReturnLineCreate
from inventory_booking_api.returns.service import create_return
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User

POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="Set POSTGRES_TEST_DATABASE_URL to run PostgreSQL concurrency integration tests.",
)

BOOKING_START = datetime(2026, 6, 25, 9, tzinfo=UTC)
BOOKING_END = BOOKING_START + timedelta(days=2)


def test_concurrent_double_booking_same_tracked_asset_is_serialized() -> None:
    async def scenario(session_factory: async_sessionmaker[AsyncSession], actor: User) -> None:
        async with session_factory() as session:
            asset = await create_tracked_asset(session, "Concurrent Tracked")
        payload = BookingCreate(
            title="Tracked race",
            starts_at=BOOKING_START,
            ends_at=BOOKING_END,
            lines=[BookingLineCreate(asset_id=asset.id)],
        )

        outcomes = await run_two_commands(
            session_factory,
            lambda session: create_booking(session, payload, actor),
            lambda session: create_booking(
                session,
                payload.model_copy(update={"title": "Tracked race duplicate"}),
                actor,
            ),
        )

        assert count_successes(outcomes) == 1
        assert one_http_status(outcomes, 409)
        async with session_factory() as session:
            assert await count_bookings(session) == 1

    run_postgres_scenario(scenario)


def test_concurrent_double_booking_same_stock_quantity_is_serialized() -> None:
    async def scenario(session_factory: async_sessionmaker[AsyncSession], actor: User) -> None:
        async with session_factory() as session:
            location = Location(name="Concurrent Stock Storage", type="storage")
            asset = Asset(name="Concurrent Balls", asset_type=AssetType.STOCK, unit_name="piece")
            session.add_all([location, asset])
            await session.flush()
            session.add(
                StockBatch(
                    asset_id=asset.id,
                    location_id=location.id,
                    status=AssetStatus.AVAILABLE,
                    quantity=5,
                )
            )
            await session.commit()
        payload = BookingCreate(
            title="Stock race",
            starts_at=BOOKING_START,
            ends_at=BOOKING_END,
            lines=[
                BookingLineCreate(asset_id=asset.id, location_id=location.id, quantity=5),
            ],
        )

        outcomes = await run_two_commands(
            session_factory,
            lambda session: create_booking(session, payload, actor),
            lambda session: create_booking(
                session,
                payload.model_copy(update={"title": "Stock race duplicate"}),
                actor,
            ),
        )

        assert count_successes(outcomes) == 1
        assert one_http_status(outcomes, 409)
        async with session_factory() as session:
            assert await count_bookings(session) == 1

    run_postgres_scenario(scenario)


def test_concurrent_checkout_and_stock_mutation_cannot_overdraw_stock() -> None:
    async def scenario(session_factory: async_sessionmaker[AsyncSession], actor: User) -> None:
        async with session_factory() as session:
            location = Location(name="Checkout Race Storage", type="storage")
            asset = Asset(name="Checkout Race Balls", asset_type=AssetType.STOCK, unit_name="piece")
            session.add_all([location, asset])
            await session.flush()
            batch = StockBatch(
                asset_id=asset.id,
                location_id=location.id,
                status=AssetStatus.AVAILABLE,
                quantity=5,
            )
            session.add(batch)
            await session.commit()
            stock_level = StockLevelRead(
                id=batch.id,
                asset_id=asset.id,
                location_id=location.id,
                quantity_total=5,
                quantity_reserved=0,
                quantity_checked_out=0,
            )

        booking_payload = BookingCreate(
            title="Checkout race",
            starts_at=BOOKING_START,
            ends_at=BOOKING_END,
            lines=[
                BookingLineCreate(asset_id=asset.id, location_id=location.id, quantity=5),
            ],
        )
        async with session_factory() as session:
            booking, _lines = await create_booking(session, booking_payload, actor)

        outcomes = await run_two_commands(
            session_factory,
            lambda session: create_checkout(session, CheckoutCreate(booking_id=booking.id), actor),
            lambda session: update_stock_level(
                session,
                stock_level,
                StockLevelUpdate(quantity_total=3),
                actor,
            ),
        )

        assert count_successes(outcomes) == 1
        assert any(isinstance(outcome, HTTPException) for outcome in outcomes)
        async with session_factory() as session:
            available_quantity, checked_out_quantity = await stock_quantities(session, asset.id)
            assert available_quantity + checked_out_quantity in (3, 5)
            assert checked_out_quantity in (0, 5)

    run_postgres_scenario(scenario)


def test_concurrent_return_and_stock_transfer_preserve_total_quantity() -> None:
    async def scenario(session_factory: async_sessionmaker[AsyncSession], actor: User) -> None:
        async with session_factory() as session:
            source = Location(name="Return Race Source", type="storage")
            destination = Location(name="Return Race Destination", type="storage")
            asset = Asset(name="Return Race Balls", asset_type=AssetType.STOCK, unit_name="piece")
            session.add_all([source, destination, asset])
            await session.flush()
            session.add(
                StockBatch(
                    asset_id=asset.id,
                    location_id=source.id,
                    status=AssetStatus.AVAILABLE,
                    quantity=10,
                )
            )
            await session.commit()

        booking_payload = BookingCreate(
            title="Return race",
            starts_at=BOOKING_START,
            ends_at=BOOKING_END,
            lines=[
                BookingLineCreate(asset_id=asset.id, location_id=source.id, quantity=5),
            ],
        )
        async with session_factory() as session:
            booking, _lines = await create_booking(session, booking_payload, actor)
        async with session_factory() as session:
            checkout, checkout_lines = await create_checkout(
                session,
                CheckoutCreate(booking_id=booking.id),
                actor,
            )

        outcomes = await run_two_commands(
            session_factory,
            lambda session: create_return(
                session,
                ReturnCreate(
                    checkout_id=checkout.id,
                    lines=[ReturnLineCreate(checkout_line_id=checkout_lines[0].id, quantity=5)],
                ),
                actor,
            ),
            lambda session: transfer_stock(
                session,
                StockTransfer(
                    asset_id=asset.id,
                    from_location_id=source.id,
                    to_location_id=destination.id,
                    quantity=5,
                ),
                actor,
            ),
        )

        assert count_successes(outcomes) == 2
        async with session_factory() as session:
            available_quantity, checked_out_quantity = await stock_quantities(session, asset.id)
            assert available_quantity == 10
            assert checked_out_quantity == 0

    run_postgres_scenario(scenario)


def run_postgres_scenario(
    scenario: Callable[[async_sessionmaker[AsyncSession], User], Awaitable[None]],
) -> None:
    async def runner() -> None:
        assert POSTGRES_TEST_DATABASE_URL is not None
        engine = create_async_engine(POSTGRES_TEST_DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        try:
            async with session_factory() as session:
                actor = User(
                    email="concurrency-admin@example.org",
                    display_name="Concurrency Admin",
                    role=UserRole.ADMIN,
                    password_hash=hash_password("password"),
                    is_active=True,
                )
                session.add(actor)
                await session.commit()
            await scenario(session_factory, actor)
        finally:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
            await engine.dispose()

    asyncio.run(runner())


async def run_two_commands(
    session_factory: async_sessionmaker[AsyncSession],
    first: Callable[[AsyncSession], Awaitable[object]],
    second: Callable[[AsyncSession], Awaitable[object]],
) -> list[object]:
    async def run(command: Callable[[AsyncSession], Awaitable[object]]) -> object:
        try:
            async with session_factory() as session:
                return await command(session)
        except Exception as exc:  # noqa: BLE001 - tests assert the captured outcome.
            return exc

    return list(await asyncio.gather(run(first), run(second)))


async def create_tracked_asset(session: AsyncSession, name: str) -> Asset:
    asset = Asset(name=name, asset_type=AssetType.TRACKED)
    session.add(asset)
    await session.flush()
    session.add(
        TrackedUnit(
            asset_id=asset.id,
            label=name,
            status=AssetStatus.AVAILABLE,
        )
    )
    await session.commit()
    return asset


async def count_bookings(session: AsyncSession) -> int:
    result = await session.execute(select(Booking.id))
    return len(result.scalars().all())


async def stock_quantities(session: AsyncSession, asset_id: UUID) -> tuple[int, int]:
    result = await session.execute(select(StockBatch).where(StockBatch.asset_id == asset_id))
    available_quantity = 0
    checked_out_quantity = 0
    for batch in result.scalars().all():
        if batch.status == AssetStatus.AVAILABLE:
            available_quantity += batch.quantity
        elif batch.status == AssetStatus.CHECKED_OUT:
            checked_out_quantity += batch.quantity
    return available_quantity, checked_out_quantity


def count_successes(outcomes: list[object]) -> int:
    return sum(not isinstance(outcome, Exception) for outcome in outcomes)


def one_http_status(outcomes: list[object], status_code: int) -> bool:
    return any(
        isinstance(outcome, HTTPException) and outcome.status_code == status_code
        for outcome in outcomes
    )
