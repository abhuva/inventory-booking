from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.bookings.availability import (
    booking_line_ends_at,
    booking_line_starts_at,
    validate_booking_lines,
)
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.queries import booking_reference_counts, list_booking_lines
from inventory_booking_api.bookings.schemas import (
    BookingCreate,
    BookingLineCreate,
    BookingUpdate,
)
from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.core.locks import (
    acquire_advisory_locks,
    asset_lock_key,
    booking_lock_key,
)
from inventory_booking_api.inventory.models import StockBatch
from inventory_booking_api.persons.models import Person
from inventory_booking_api.returns.models import Return, ReturnLine
from inventory_booking_api.users.models import User

ACTIVE_BOOKING_STATUSES = (BookingStatus.RESERVED, BookingStatus.CHECKED_OUT)


async def create_booking(
    session: AsyncSession,
    payload: BookingCreate,
    actor: User,
    *,
    excluded_basket_id: UUID | None = None,
) -> tuple[Booking, list[BookingLine]]:
    booking, booking_lines = await create_booking_without_commit(
        session,
        payload,
        actor,
        excluded_basket_id=excluded_basket_id,
    )
    await session.commit()
    await session.refresh(booking)
    for line in booking_lines:
        await session.refresh(line)
    return booking, booking_lines


async def create_booking_without_commit(
    session: AsyncSession,
    payload: BookingCreate,
    actor: User,
    *,
    excluded_basket_id: UUID | None = None,
) -> tuple[Booking, list[BookingLine]]:
    """Create booking rows as part of a larger command transaction."""

    await validate_booking_person(session, payload.person_id)
    await acquire_advisory_locks(session, [asset_lock_key(line.asset_id) for line in payload.lines])
    await validate_booking_lines(session, payload, excluded_basket_id=excluded_basket_id)
    aggregate_starts_at = min(booking_line_starts_at(payload, line) for line in payload.lines)
    aggregate_ends_at = max(booking_line_ends_at(payload, line) for line in payload.lines)

    booking = Booking(
        requested_by_user_id=actor.id,
        person_id=payload.person_id,
        title=payload.title,
        starts_at=aggregate_starts_at,
        ends_at=aggregate_ends_at,
        notes=payload.notes,
        status=BookingStatus.RESERVED,
    )
    session.add(booking)
    await session.flush()

    booking_lines = [
        BookingLine(
            booking_id=booking.id,
            **booking_line_values(payload, line),
        )
        for line in payload.lines
    ]
    session.add_all(booking_lines)

    for line in booking_lines:
        await write_item_event(
            session,
            asset_id=line.asset_id,
            event_type=ItemEventType.RESERVED,
            actor=actor,
            notes=f"Reserved for booking {booking.title}",
            details={
                "booking_id": str(booking.id),
                "location_id": str(line.location_id) if line.location_id else None,
                "quantity": line.quantity,
            },
        )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="booking",
        entity_id=booking.id,
        summary=f"Created booking {booking.title}",
    )
    return booking, booking_lines


async def update_booking(
    session: AsyncSession,
    booking: Booking,
    payload: BookingUpdate,
    actor: User,
) -> Booking:
    """Update editable booking metadata and revalidate active reservations."""

    lines = await list_booking_lines(session, booking.id)
    await acquire_advisory_locks(
        session,
        [booking_lock_key(booking.id), *(asset_lock_key(line.asset_id) for line in lines)],
    )
    next_status = payload.status if payload.status is not None else booking.status
    next_person_id = payload.person_id if payload.person_id is not None else booking.person_id
    next_starts_at = payload.starts_at if payload.starts_at is not None else booking.starts_at
    next_ends_at = payload.ends_at if payload.ends_at is not None else booking.ends_at
    if next_starts_at >= next_ends_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Booking starts_at must be before ends_at.",
        )
    await validate_booking_person(session, next_person_id)
    time_range_changed = next_starts_at != booking.starts_at or next_ends_at != booking.ends_at
    made_active = (
        booking.status not in ACTIVE_BOOKING_STATUSES and next_status in ACTIVE_BOOKING_STATUSES
    )
    if next_status in ACTIVE_BOOKING_STATUSES and (time_range_changed or made_active):
        await validate_booking_lines(
            session,
            BookingCreate(
                title=booking.title,
                person_id=next_person_id,
                starts_at=next_starts_at,
                ends_at=next_ends_at,
                notes=booking.notes,
                lines=[
                    BookingLineCreate(
                        asset_id=line.asset_id,
                        location_id=line.location_id,
                        starts_at=next_starts_at,
                        ends_at=next_ends_at,
                        quantity=line.quantity,
                        notes=line.notes,
                    )
                    for line in lines
                ],
            ),
            excluded_booking_id=booking.id,
        )

    booking.status = next_status
    booking.person_id = next_person_id
    booking.starts_at = next_starts_at
    booking.ends_at = next_ends_at
    if time_range_changed:
        for line in lines:
            line.starts_at = next_starts_at
            line.ends_at = next_ends_at
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="booking",
        entity_id=booking.id,
        summary=f"Updated booking {booking.title}",
    )
    await session.commit()
    await session.refresh(booking)
    return booking


async def delete_booking(session: AsyncSession, booking: Booking, actor: User) -> None:
    lines = await list_booking_lines(session, booking.id)
    await acquire_advisory_locks(
        session,
        [booking_lock_key(booking.id), *(asset_lock_key(line.asset_id) for line in lines)],
    )
    counts = await booking_reference_counts(session, booking.id)
    checkout_ids = list(
        (
            await session.execute(select(Checkout.id).where(Checkout.booking_id == booking.id))
        ).scalars()
    )
    if checkout_ids:
        return_ids = list(
            (
                await session.execute(select(Return.id).where(Return.checkout_id.in_(checkout_ids)))
            ).scalars()
        )
        if return_ids:
            await session.execute(delete(ReturnLine).where(ReturnLine.return_id.in_(return_ids)))
            await session.execute(delete(Return).where(Return.id.in_(return_ids)))
        checkout_line_ids = list(
            (
                await session.execute(
                    select(CheckoutLine.id).where(CheckoutLine.checkout_id.in_(checkout_ids))
                )
            ).scalars()
        )
        if checkout_line_ids:
            await session.execute(
                update(StockBatch)
                .where(StockBatch.checkout_line_id.in_(checkout_line_ids))
                .values(checkout_line_id=None)
            )
            await session.execute(
                delete(CheckoutLine).where(CheckoutLine.id.in_(checkout_line_ids))
            )
        await session.execute(delete(Checkout).where(Checkout.id.in_(checkout_ids)))
    await session.execute(delete(BookingLine).where(BookingLine.booking_id == booking.id))
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="booking",
        entity_id=booking.id,
        summary=f"Deleted booking {booking.title}",
        details=counts,
    )
    await session.delete(booking)
    await session.commit()


async def validate_booking_person(session: AsyncSession, person_id: UUID | None) -> None:
    """Reject a booking person reference that does not exist."""

    if person_id is None:
        return
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person does not exist.",
        )


def booking_line_values(payload: BookingCreate, line: BookingLineCreate) -> dict[str, object]:
    return {
        "asset_id": line.asset_id,
        "location_id": line.location_id,
        "starts_at": booking_line_starts_at(payload, line),
        "ends_at": booking_line_ends_at(payload, line),
        "quantity": line.quantity,
        "notes": line.notes,
    }


async def cancel_booking(session: AsyncSession, booking: Booking, actor: User) -> Booking:
    lines = await list_booking_lines(session, booking.id)
    await acquire_advisory_locks(
        session,
        [booking_lock_key(booking.id), *(asset_lock_key(line.asset_id) for line in lines)],
    )
    if booking.status == BookingStatus.CANCELLED:
        return booking
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active bookings can be cancelled.",
        )

    booking.status = BookingStatus.CANCELLED
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="booking",
        entity_id=booking.id,
        summary=f"Cancelled booking {booking.title}",
    )
    await session.commit()
    await session.refresh(booking)
    return booking


