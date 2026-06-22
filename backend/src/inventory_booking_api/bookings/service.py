from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import BookingCreate
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockLevel
from inventory_booking_api.users.models import User

ACTIVE_BOOKING_STATUSES = (BookingStatus.RESERVED, BookingStatus.CHECKED_OUT)


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


async def create_booking(
    session: AsyncSession,
    payload: BookingCreate,
    actor: User,
) -> tuple[Booking, list[BookingLine]]:
    await validate_booking_lines(session, payload)

    booking = Booking(
        requested_by_user_id=actor.id,
        title=payload.title,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        notes=payload.notes,
        status=BookingStatus.RESERVED,
    )
    session.add(booking)
    await session.flush()

    booking_lines = [
        BookingLine(booking_id=booking.id, **line.model_dump()) for line in payload.lines
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
    await session.commit()
    await session.refresh(booking)
    for line in booking_lines:
        await session.refresh(line)
    return booking, booking_lines


async def cancel_booking(session: AsyncSession, booking: Booking, actor: User) -> Booking:
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


async def validate_booking_lines(session: AsyncSession, payload: BookingCreate) -> None:
    seen_lines: set[tuple[UUID, UUID | None]] = set()
    for line in payload.lines:
        line_key = (line.asset_id, line.location_id)
        if line_key in seen_lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate booking line for the same asset/location.",
            )
        seen_lines.add(line_key)

        asset = await session.get(Asset, line.asset_id)
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking line asset does not exist.",
            )
        if asset.status != AssetStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset {asset.name} is not available.",
            )

        if asset.asset_type == AssetType.TRACKED:
            await validate_tracked_line(session, payload, line.asset_id, line.quantity)
        else:
            await validate_stock_line(
                session,
                payload,
                line.asset_id,
                line.location_id,
                line.quantity,
            )


async def validate_tracked_line(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    quantity: int | None,
) -> None:
    if quantity not in (None, 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracked booking lines must not request a quantity above 1.",
        )

    result = await session.execute(
        select(BookingLine.id)
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(
            BookingLine.asset_id == asset_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.starts_at < payload.ends_at,
            Booking.ends_at > payload.starts_at,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tracked asset is already booked for this time range.",
        )


async def validate_stock_line(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    location_id: UUID | None,
    quantity: int | None,
) -> None:
    if location_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock booking lines require a location_id.",
        )
    if quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock booking lines require a quantity.",
        )

    stock_level = await get_stock_level(session, asset_id, location_id)
    if stock_level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stock level exists for this asset/location.",
        )

    overlapping_quantity = await get_overlapping_stock_quantity(
        session, payload, asset_id, location_id
    )
    if stock_level.quantity_total - overlapping_quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough stock is available for this time range.",
        )


async def get_stock_level(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
) -> StockLevel | None:
    result = await session.execute(
        select(StockLevel).where(
            StockLevel.asset_id == asset_id,
            StockLevel.location_id == location_id,
        )
    )
    return result.scalar_one_or_none()


async def get_overlapping_stock_quantity(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    location_id: UUID,
) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(BookingLine.quantity), 0))
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(
            BookingLine.asset_id == asset_id,
            BookingLine.location_id == location_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.starts_at < payload.ends_at,
            Booking.ends_at > payload.starts_at,
        )
    )
    return int(result.scalar_one())
