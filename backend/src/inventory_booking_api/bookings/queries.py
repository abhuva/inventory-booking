from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.returns.models import Return


async def list_bookings(session: AsyncSession) -> list[Booking]:
    result = await session.execute(select(Booking).order_by(Booking.starts_at.desc()))
    return list(result.scalars().all())


async def get_booking(session: AsyncSession, booking_id: UUID) -> Booking | None:
    return await session.get(Booking, booking_id)


async def list_booking_lines(session: AsyncSession, booking_id: UUID) -> list[BookingLine]:
    result = await session.execute(
        select(BookingLine)
        .where(BookingLine.booking_id == booking_id)
        .order_by(BookingLine.created_at)
    )
    return list(result.scalars().all())


async def booking_reference_counts(session: AsyncSession, booking_id: UUID) -> dict[str, int]:
    checkout_ids = list(
        (
            await session.execute(select(Checkout.id).where(Checkout.booking_id == booking_id))
        ).scalars()
    )
    return {
        "booking_lines": await count_where(
            session, select(func.count(BookingLine.id)).where(BookingLine.booking_id == booking_id)
        ),
        "checkouts": len(checkout_ids),
        "checkout_lines": await count_where(
            session,
            select(func.count(CheckoutLine.id)).where(CheckoutLine.checkout_id.in_(checkout_ids)),
        )
        if checkout_ids
        else 0,
        "returns": await count_where(
            session, select(func.count(Return.id)).where(Return.checkout_id.in_(checkout_ids))
        )
        if checkout_ids
        else 0,
    }


async def count_where(session: AsyncSession, statement) -> int:
    result = await session.execute(statement)
    return int(result.scalar_one())
