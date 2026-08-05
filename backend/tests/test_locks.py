import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from inventory_booking_api.core.locks import (
    acquire_advisory_locks,
    asset_lock_key,
    booking_lock_key,
    checkout_lock_key,
)


def test_advisory_locks_are_noop_for_sqlite() -> None:
    async def run_test() -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as session:
            await acquire_advisory_locks(session, ["asset:one", "asset:two"])

        await engine.dispose()

    asyncio.run(run_test())


def test_lock_keys_are_namespaced() -> None:
    identifier = UUID("00000000-0000-0000-0000-000000000001")

    assert asset_lock_key(identifier) == "asset:00000000-0000-0000-0000-000000000001"
    assert booking_lock_key(identifier) == "booking:00000000-0000-0000-0000-000000000001"
    assert checkout_lock_key(identifier) == "checkout:00000000-0000-0000-0000-000000000001"
