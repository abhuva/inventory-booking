from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def acquire_advisory_locks(session: AsyncSession, keys: Iterable[str]) -> None:
    """Acquire deterministic transaction-scoped advisory locks on PostgreSQL."""

    if session.get_bind().dialect.name != "postgresql":
        return

    for key in sorted(set(keys)):
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": key},
        )


def asset_lock_key(asset_id: UUID) -> str:
    return f"asset:{asset_id}"


def booking_lock_key(booking_id: UUID) -> str:
    return f"booking:{booking_id}"


def checkout_lock_key(checkout_id: UUID) -> str:
    return f"checkout:{checkout_id}"
