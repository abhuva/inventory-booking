from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import (
    AvailabilityLineRead,
    AvailabilityRead,
    BookingCreate,
    BookingLineCreate,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
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
    *,
    excluded_basket_id: UUID | None = None,
    commit: bool = True,
) -> tuple[Booking, list[BookingLine]]:
    await validate_booking_lines(session, payload, excluded_basket_id=excluded_basket_id)

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
    if commit:
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


async def preview_availability(
    session: AsyncSession,
    payload: BookingCreate,
    *,
    excluded_basket_id: UUID | None = None,
) -> AvailabilityRead:
    line_results: list[AvailabilityLineRead] = []
    seen_lines: set[tuple[UUID, UUID | None]] = set()
    for line in payload.lines:
        line_key = (line.asset_id, line.location_id)
        if line_key in seen_lines:
            line_results.append(
                build_availability_line(
                    line,
                    available=False,
                    reason="Duplicate booking line for the same asset/location.",
                )
            )
            continue
        seen_lines.add(line_key)
        line_results.append(
            await preview_line_availability(
                session,
                payload,
                line,
                excluded_basket_id=excluded_basket_id,
            )
        )

    return AvailabilityRead(
        available=all(line.available for line in line_results),
        lines=line_results,
    )


async def validate_booking_lines(
    session: AsyncSession,
    payload: BookingCreate,
    *,
    excluded_basket_id: UUID | None = None,
) -> None:
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
        if asset.asset_type == AssetType.TRACKED:
            await validate_tracked_line(
                session,
                payload,
                line.asset_id,
                line.quantity,
                excluded_basket_id=excluded_basket_id,
            )
        else:
            await validate_stock_line(
                session,
                payload,
                line.asset_id,
                line.location_id,
                line.quantity,
                excluded_basket_id=excluded_basket_id,
            )


async def validate_tracked_line(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    quantity: int | None,
    *,
    excluded_basket_id: UUID | None = None,
) -> None:
    unit = await get_primary_tracked_unit(session, asset_id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracked booking line has no physical unit.",
        )
    if unit.status != AssetStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracked unit is not available.",
        )
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
    if await has_overlapping_tracked_basket_hold(
        session,
        payload,
        asset_id,
        excluded_basket_id=excluded_basket_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tracked asset is temporarily held in another basket for this time range.",
        )


async def validate_stock_line(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    location_id: UUID | None,
    quantity: int | None,
    *,
    excluded_basket_id: UUID | None = None,
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

    stock_quantity = await get_available_stock_quantity(session, asset_id, location_id)
    overlapping_quantity = await get_overlapping_stock_quantity(
        session, payload, asset_id, location_id
    )
    held_quantity = await get_overlapping_stock_basket_quantity(
        session,
        payload,
        asset_id,
        location_id,
        excluded_basket_id=excluded_basket_id,
    )
    if stock_quantity - overlapping_quantity - held_quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough stock is available for this time range.",
        )


async def get_available_stock_quantity(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(StockBatch.quantity), 0)).where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.holder_user_id.is_(None),
            StockBatch.status == AssetStatus.AVAILABLE,
        )
    )
    return int(result.scalar_one())


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


async def preview_line_availability(
    session: AsyncSession,
    payload: BookingCreate,
    line: BookingLineCreate,
    *,
    excluded_basket_id: UUID | None = None,
) -> AvailabilityLineRead:
    asset = await session.get(Asset, line.asset_id)
    if asset is None:
        return build_availability_line(line, available=False, reason="Asset does not exist.")
    if asset.asset_type == AssetType.TRACKED:
        return await preview_tracked_line(
            session,
            payload,
            line,
            excluded_basket_id=excluded_basket_id,
        )
    return await preview_stock_line(
        session,
        payload,
        line,
        excluded_basket_id=excluded_basket_id,
    )


async def preview_tracked_line(
    session: AsyncSession,
    payload: BookingCreate,
    line: BookingLineCreate,
    *,
    excluded_basket_id: UUID | None = None,
) -> AvailabilityLineRead:
    unit = await get_primary_tracked_unit(session, line.asset_id)
    if unit is None:
        return build_availability_line(
            line,
            available=False,
            available_quantity=0,
            reason="Tracked booking line has no physical unit.",
        )
    if unit.status != AssetStatus.AVAILABLE:
        return build_availability_line(
            line,
            available=False,
            available_quantity=0,
            reason="Tracked unit is not available.",
        )
    if line.quantity not in (None, 1):
        return build_availability_line(
            line,
            available=False,
            available_quantity=1,
            reason="Tracked booking lines must not request a quantity above 1.",
        )

    result = await session.execute(
        select(BookingLine.id)
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(
            BookingLine.asset_id == line.asset_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.starts_at < payload.ends_at,
            Booking.ends_at > payload.starts_at,
        )
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return build_availability_line(
            line,
            available=False,
            available_quantity=0,
            reason="Tracked asset is already booked for this time range.",
        )
    if await has_overlapping_tracked_basket_hold(
        session,
        payload,
        line.asset_id,
        excluded_basket_id=excluded_basket_id,
    ):
        return build_availability_line(
            line,
            available=False,
            available_quantity=0,
            reason="Tracked asset is temporarily held in another basket for this time range.",
        )
    return build_availability_line(line, available=True, available_quantity=1)


async def preview_stock_line(
    session: AsyncSession,
    payload: BookingCreate,
    line: BookingLineCreate,
    *,
    excluded_basket_id: UUID | None = None,
) -> AvailabilityLineRead:
    if line.location_id is None:
        return build_availability_line(
            line,
            available=False,
            reason="Stock booking lines require a location_id.",
        )
    if line.quantity is None:
        return build_availability_line(
            line,
            available=False,
            reason="Stock booking lines require a quantity.",
        )

    stock_quantity = await get_available_stock_quantity(session, line.asset_id, line.location_id)
    overlapping_quantity = await get_overlapping_stock_quantity(
        session,
        payload,
        line.asset_id,
        line.location_id,
    )
    held_quantity = await get_overlapping_stock_basket_quantity(
        session,
        payload,
        line.asset_id,
        line.location_id,
        excluded_basket_id=excluded_basket_id,
    )
    available_quantity = stock_quantity - overlapping_quantity - held_quantity
    return build_availability_line(
        line,
        available=available_quantity >= line.quantity,
        available_quantity=available_quantity,
        reason=None
        if available_quantity >= line.quantity
        else "Not enough stock is available for this time range.",
    )


def build_availability_line(
    line: BookingLineCreate,
    *,
    available: bool,
    reason: str | None = None,
    available_quantity: int | None = None,
) -> AvailabilityLineRead:
    return AvailabilityLineRead(
        asset_id=line.asset_id,
        location_id=line.location_id,
        requested_quantity=line.quantity,
        available_quantity=available_quantity,
        available=available,
        reason=reason,
    )


async def get_primary_tracked_unit(session: AsyncSession, asset_id: UUID) -> TrackedUnit | None:
    result = await session.execute(
        select(TrackedUnit).where(TrackedUnit.asset_id == asset_id).order_by(TrackedUnit.created_at)
    )
    return result.scalars().first()


async def has_overlapping_tracked_basket_hold(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    *,
    excluded_basket_id: UUID | None = None,
) -> bool:
    result = await session.execute(
        basket_hold_query(payload, excluded_basket_id=excluded_basket_id)
        .with_only_columns(BasketLine.id)
        .where(BasketLine.asset_id == asset_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_overlapping_stock_basket_quantity(
    session: AsyncSession,
    payload: BookingCreate,
    asset_id: UUID,
    location_id: UUID,
    *,
    excluded_basket_id: UUID | None = None,
) -> int:
    result = await session.execute(
        basket_hold_query(payload, excluded_basket_id=excluded_basket_id)
        .with_only_columns(func.coalesce(func.sum(BasketLine.quantity), 0))
        .where(
            BasketLine.asset_id == asset_id,
            BasketLine.location_id == location_id,
        )
    )
    return int(result.scalar_one())


def basket_hold_query(
    payload: BookingCreate,
    *,
    excluded_basket_id: UUID | None = None,
):
    query = (
        select(BasketLine)
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(
            Basket.status == BasketStatus.ACTIVE,
            Basket.expires_at > datetime.now(UTC),
            Basket.starts_at < payload.ends_at,
            Basket.ends_at > payload.starts_at,
        )
    )
    if excluded_basket_id is not None:
        query = query.where(Basket.id != excluded_basket_id)
    return query
