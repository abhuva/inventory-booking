from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import (
    AvailabilityDayRead,
    AvailabilityDaysRead,
    AvailabilityHeatmapRead,
    AvailabilityLineRead,
    AvailabilityRead,
    BookingCreate,
    BookingLineCreate,
    BookingUpdate,
    HeatmapCellRead,
    HeatmapItemRead,
)
from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.persons.models import Person
from inventory_booking_api.returns.models import Return, ReturnLine
from inventory_booking_api.users.models import User

ACTIVE_BOOKING_STATUSES = (BookingStatus.RESERVED, BookingStatus.CHECKED_OUT)
HEATMAP_MAX_BUCKETS = 370
HEATMAP_CACHE_MAX_ITEMS = 24
HeatmapCacheKey = tuple[str, str, str, UUID | None, tuple[object, ...]]
heatmap_cache: OrderedDict[HeatmapCacheKey, AvailabilityHeatmapRead] = OrderedDict()


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
    await validate_booking_person(session, payload.person_id)
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
    if commit:
        await session.commit()
        await session.refresh(booking)
        for line in booking_lines:
            await session.refresh(line)
    return booking, booking_lines


async def update_booking(
    session: AsyncSession,
    booking: Booking,
    payload: BookingUpdate,
    actor: User,
) -> Booking:
    """Update editable booking metadata and revalidate active reservations."""

    lines = await list_booking_lines(session, booking.id)
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


def booking_line_starts_at(payload: BookingCreate, line: BookingLineCreate) -> datetime:
    return line.starts_at if line.starts_at is not None else payload.starts_at


def booking_line_ends_at(payload: BookingCreate, line: BookingLineCreate) -> datetime:
    return line.ends_at if line.ends_at is not None else payload.ends_at


def booking_line_values(payload: BookingCreate, line: BookingLineCreate) -> dict[str, object]:
    return {
        "asset_id": line.asset_id,
        "location_id": line.location_id,
        "starts_at": booking_line_starts_at(payload, line),
        "ends_at": booking_line_ends_at(payload, line),
        "quantity": line.quantity,
        "notes": line.notes,
    }


def has_overlapping_payload_tracked_line(
    payload: BookingCreate,
    target_line: BookingLineCreate,
) -> bool:
    target_start = booking_line_starts_at(payload, target_line)
    target_end = booking_line_ends_at(payload, target_line)
    overlap_count = 0
    for line in payload.lines:
        if line.asset_id != target_line.asset_id:
            continue
        if ranges_overlap(
            target_start,
            target_end,
            booking_line_starts_at(payload, line),
            booking_line_ends_at(payload, line),
        ):
            overlap_count += 1
    return overlap_count > 1


def max_payload_stock_quantity(payload: BookingCreate, target_line: BookingLineCreate) -> int:
    if target_line.location_id is None:
        return int(target_line.quantity or 0)
    impacts = [
        (
            int(line.quantity or 0),
            booking_line_starts_at(payload, line),
            booking_line_ends_at(payload, line),
        )
        for line in payload.lines
        if line.asset_id == target_line.asset_id and line.location_id == target_line.location_id
    ]
    return max_concurrent_quantity(
        impacts,
        booking_line_starts_at(payload, target_line),
        booking_line_ends_at(payload, target_line),
    )


def ranges_overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    return comparable_datetime(left_start) < comparable_datetime(right_end) and comparable_datetime(
        left_end
    ) > comparable_datetime(right_start)


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
    seen_lines: set[tuple[UUID, UUID | None, datetime, datetime]] = set()
    for line in payload.lines:
        line_key = (
            line.asset_id,
            line.location_id,
            booking_line_starts_at(payload, line),
            booking_line_ends_at(payload, line),
        )
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


async def build_stock_availability_heatmap(
    session: AsyncSession,
    *,
    starts_at: datetime,
    ends_at: datetime,
    bucket: str,
    location_id: UUID | None = None,
) -> AvailabilityHeatmapRead:
    buckets = build_heatmap_buckets(starts_at, ends_at, bucket)
    cache_key = (
        starts_at.isoformat(),
        ends_at.isoformat(),
        bucket,
        location_id,
        await get_heatmap_state_fingerprint(session),
    )
    cached_heatmap = read_heatmap_cache(cache_key)
    if cached_heatmap is not None:
        return cached_heatmap

    stock_assets = await list_heatmap_stock_totals(session, location_id)
    stock_asset_ids = [asset_id for asset_id, _name, _unit_name, _total_quantity in stock_assets]
    tracked_assets = await list_heatmap_tracked_totals(session, location_id)
    tracked_asset_ids = [
        asset_id
        for asset_id, _name, _unit_name, _total_quantity, _physical_available in tracked_assets
    ]
    reserved_quantities = initialize_heatmap_quantities(stock_asset_ids, buckets)
    held_quantities = initialize_heatmap_quantities(stock_asset_ids, buckets)
    if is_postgresql_session(session):
        reserved_quantities = await aggregate_heatmap_booking_quantities_postgresql(
            session,
            buckets=buckets,
            starts_at=starts_at,
            ends_at=ends_at,
            bucket=bucket,
            asset_ids=stock_asset_ids,
            location_id=location_id,
        )
        held_quantities = await aggregate_heatmap_basket_quantities_postgresql(
            session,
            buckets=buckets,
            starts_at=starts_at,
            ends_at=ends_at,
            bucket=bucket,
            asset_ids=stock_asset_ids,
            location_id=location_id,
        )
    else:
        booking_impacts = await list_heatmap_booking_impacts(
            session,
            starts_at=starts_at,
            ends_at=ends_at,
            asset_ids=stock_asset_ids,
            location_id=location_id,
        )
        basket_impacts = await list_heatmap_basket_impacts(
            session,
            starts_at=starts_at,
            ends_at=ends_at,
            asset_ids=stock_asset_ids,
            location_id=location_id,
        )
        apply_heatmap_impacts(reserved_quantities, buckets, booking_impacts)
        apply_heatmap_impacts(held_quantities, buckets, basket_impacts)

    tracked_reserved_quantities = initialize_heatmap_quantities(tracked_asset_ids, buckets)
    tracked_held_quantities = initialize_heatmap_quantities(tracked_asset_ids, buckets)
    tracked_booking_impacts = await list_heatmap_tracked_booking_impacts(
        session,
        starts_at=starts_at,
        ends_at=ends_at,
        asset_ids=tracked_asset_ids,
    )
    tracked_basket_impacts = await list_heatmap_tracked_basket_impacts(
        session,
        starts_at=starts_at,
        ends_at=ends_at,
        asset_ids=tracked_asset_ids,
    )
    apply_heatmap_impacts(tracked_reserved_quantities, buckets, tracked_booking_impacts)
    apply_heatmap_impacts(tracked_held_quantities, buckets, tracked_basket_impacts)
    items: list[HeatmapItemRead] = []

    for asset_id, name, unit_name, total_quantity in stock_assets:
        cells: list[HeatmapCellRead] = []
        for bucket_index, (bucket_start, bucket_end) in enumerate(buckets):
            reserved_quantity = reserved_quantities[asset_id][bucket_index]
            held_quantity = held_quantities[asset_id][bucket_index]
            cells.append(
                HeatmapCellRead(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    total_quantity=total_quantity,
                    reserved_quantity=reserved_quantity,
                    held_quantity=held_quantity,
                    available_quantity=max(0, total_quantity - reserved_quantity - held_quantity),
                )
            )

        items.append(
            HeatmapItemRead(
                asset_id=asset_id,
                name=name,
                asset_type=AssetType.STOCK,
                unit_name=unit_name,
                total_quantity=total_quantity,
                cells=cells,
            )
        )

    for asset_id, name, unit_name, total_quantity, physical_available in tracked_assets:
        cells = []
        for bucket_index, (bucket_start, bucket_end) in enumerate(buckets):
            reserved_quantity = tracked_reserved_quantities[asset_id][bucket_index]
            held_quantity = tracked_held_quantities[asset_id][bucket_index]
            available_quantity = max(
                0,
                min(1, physical_available) - min(1, reserved_quantity + held_quantity),
            )
            cells.append(
                HeatmapCellRead(
                    bucket_start=bucket_start,
                    bucket_end=bucket_end,
                    total_quantity=total_quantity,
                    reserved_quantity=min(1, reserved_quantity),
                    held_quantity=min(1, held_quantity),
                    available_quantity=available_quantity,
                )
            )

        items.append(
            HeatmapItemRead(
                asset_id=asset_id,
                name=name,
                asset_type=AssetType.TRACKED,
                unit_name=unit_name,
                total_quantity=total_quantity,
                cells=cells,
            )
        )
    items.sort(key=lambda item: item.name.lower())

    heatmap = AvailabilityHeatmapRead(
        starts_at=starts_at,
        ends_at=ends_at,
        bucket=bucket,
        location_id=location_id,
        items=items,
    )
    write_heatmap_cache(cache_key, heatmap)
    return heatmap


async def build_asset_availability_days(
    session: AsyncSession,
    *,
    asset_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    quantity: int,
    location_id: UUID | None,
    actor: User,
) -> AvailabilityDaysRead:
    if quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="quantity must be at least 1.",
        )
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    buckets = build_heatmap_buckets(starts_at, ends_at, "day")
    excluded_basket_id = await get_active_basket_id_for_user(session, actor.id)
    days: list[AvailabilityDayRead] = []
    for bucket_start, bucket_end in buckets:
        if asset.asset_type == AssetType.STOCK:
            day = await build_stock_availability_day(
                session,
                asset_id=asset.id,
                location_id=location_id,
                quantity=quantity,
                bucket_start=bucket_start,
                bucket_end=bucket_end,
                excluded_basket_id=excluded_basket_id,
            )
        else:
            day = await build_tracked_availability_day(
                session,
                asset_id=asset.id,
                quantity=quantity,
                bucket_start=bucket_start,
                bucket_end=bucket_end,
                excluded_basket_id=excluded_basket_id,
            )
        days.append(day)

    return AvailabilityDaysRead(
        asset_id=asset.id,
        location_id=location_id,
        quantity=quantity,
        starts_at=starts_at,
        ends_at=ends_at,
        days=days,
    )


async def validate_booking_lines(
    session: AsyncSession,
    payload: BookingCreate,
    *,
    excluded_basket_id: UUID | None = None,
    excluded_booking_id: UUID | None = None,
) -> None:
    seen_lines: set[tuple[UUID, UUID | None, datetime, datetime]] = set()
    for line in payload.lines:
        line_key = (
            line.asset_id,
            line.location_id,
            booking_line_starts_at(payload, line),
            booking_line_ends_at(payload, line),
        )
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
            if has_overlapping_payload_tracked_line(payload, line):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tracked asset has overlapping booking lines.",
                )
            await validate_tracked_line(
                session,
                line.asset_id,
                booking_line_starts_at(payload, line),
                booking_line_ends_at(payload, line),
                line.quantity,
                excluded_basket_id=excluded_basket_id,
                excluded_booking_id=excluded_booking_id,
            )
        else:
            await validate_stock_line(
                session,
                line.asset_id,
                line.location_id,
                booking_line_starts_at(payload, line),
                booking_line_ends_at(payload, line),
                line.quantity,
                max_payload_stock_quantity(payload, line),
                excluded_basket_id=excluded_basket_id,
                excluded_booking_id=excluded_booking_id,
            )


async def validate_tracked_line(
    session: AsyncSession,
    asset_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    quantity: int | None,
    *,
    excluded_basket_id: UUID | None = None,
    excluded_booking_id: UUID | None = None,
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

    filters = [
        BookingLine.asset_id == asset_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        BookingLine.starts_at < ends_at,
        BookingLine.ends_at > starts_at,
    ]
    if excluded_booking_id is not None:
        filters.append(Booking.id != excluded_booking_id)
    result = await session.execute(
        select(BookingLine.id)
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(*filters)
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tracked asset is already booked for this time range.",
        )
    if await has_overlapping_tracked_basket_hold(
        session,
        asset_id,
        starts_at,
        ends_at,
        excluded_basket_id=excluded_basket_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tracked asset is temporarily held in another basket for this time range.",
        )


async def validate_stock_line(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    quantity: int | None,
    requested_quantity: int,
    *,
    excluded_basket_id: UUID | None = None,
    excluded_booking_id: UUID | None = None,
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
    overlapping_quantity = await get_overlapping_stock_impact_quantity(
        session,
        asset_id,
        location_id,
        starts_at,
        ends_at,
        excluded_booking_id=excluded_booking_id,
        excluded_basket_id=excluded_basket_id,
    )
    if stock_quantity - overlapping_quantity < requested_quantity:
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


async def get_available_stock_quantity_for_heatmap(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> int:
    filters = [
        StockBatch.asset_id == asset_id,
        StockBatch.holder_user_id.is_(None),
        StockBatch.status == AssetStatus.AVAILABLE,
    ]
    if location_id is not None:
        filters.append(StockBatch.location_id == location_id)

    result = await session.execute(
        select(func.coalesce(func.sum(StockBatch.quantity), 0)).where(*filters)
    )
    return int(result.scalar_one())


async def get_overlapping_stock_quantity(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_booking_id: UUID | None = None,
) -> int:
    filters = [
        BookingLine.asset_id == asset_id,
        BookingLine.location_id == location_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        BookingLine.starts_at < ends_at,
        BookingLine.ends_at > starts_at,
    ]
    if excluded_booking_id is not None:
        filters.append(Booking.id != excluded_booking_id)
    result = await session.execute(
        select(func.coalesce(func.sum(BookingLine.quantity), 0))
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(*filters)
    )
    return int(result.scalar_one())


async def get_overlapping_stock_impact_quantity(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_booking_id: UUID | None = None,
    excluded_basket_id: UUID | None = None,
) -> int:
    booking_filters = [
        BookingLine.asset_id == asset_id,
        BookingLine.location_id == location_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        BookingLine.starts_at < ends_at,
        BookingLine.ends_at > starts_at,
    ]
    if excluded_booking_id is not None:
        booking_filters.append(Booking.id != excluded_booking_id)
    booking_rows = await session.execute(
        select(BookingLine.quantity, BookingLine.starts_at, BookingLine.ends_at)
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(*booking_filters)
    )

    basket_filters = [
        BasketLine.asset_id == asset_id,
        BasketLine.location_id == location_id,
        Basket.status == BasketStatus.ACTIVE,
        Basket.expires_at > datetime.now(UTC),
        BasketLine.starts_at < ends_at,
        BasketLine.ends_at > starts_at,
    ]
    if excluded_basket_id is not None:
        basket_filters.append(Basket.id != excluded_basket_id)
    basket_rows = await session.execute(
        select(BasketLine.quantity, BasketLine.starts_at, BasketLine.ends_at)
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(*basket_filters)
    )

    impacts = [
        (int(quantity or 0), impact_starts_at, impact_ends_at)
        for quantity, impact_starts_at, impact_ends_at in booking_rows.all()
    ]
    impacts.extend(
        (int(quantity or 0), impact_starts_at, impact_ends_at)
        for quantity, impact_starts_at, impact_ends_at in basket_rows.all()
    )
    return max_concurrent_quantity(impacts, starts_at, ends_at)


def max_concurrent_quantity(
    impacts: list[tuple[int, datetime, datetime]],
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    cut_points = {comparable_datetime(starts_at), comparable_datetime(ends_at)}
    normalized_impacts: list[tuple[int, datetime, datetime]] = []
    range_start = comparable_datetime(starts_at)
    range_end = comparable_datetime(ends_at)
    for quantity, impact_starts_at, impact_ends_at in impacts:
        if quantity <= 0:
            continue
        impact_start = max(comparable_datetime(impact_starts_at), range_start)
        impact_end = min(comparable_datetime(impact_ends_at), range_end)
        if impact_start >= impact_end:
            continue
        normalized_impacts.append((quantity, impact_start, impact_end))
        cut_points.add(impact_start)
        cut_points.add(impact_end)

    ordered_cut_points = sorted(cut_points)
    max_quantity = 0
    for start, end in zip(ordered_cut_points, ordered_cut_points[1:], strict=False):
        if start >= end:
            continue
        concurrent_quantity = sum(
            quantity
            for quantity, impact_start, impact_end in normalized_impacts
            if impact_start < end and impact_end > start
        )
        max_quantity = max(max_quantity, concurrent_quantity)
    return max_quantity


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
        if has_overlapping_payload_tracked_line(payload, line):
            return build_availability_line(
                line,
                available=False,
                available_quantity=0,
                reason="Tracked asset has overlapping booking lines.",
            )
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
            BookingLine.starts_at < booking_line_ends_at(payload, line),
            BookingLine.ends_at > booking_line_starts_at(payload, line),
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
        line.asset_id,
        booking_line_starts_at(payload, line),
        booking_line_ends_at(payload, line),
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
    overlapping_quantity = await get_overlapping_stock_impact_quantity(
        session,
        line.asset_id,
        line.location_id,
        booking_line_starts_at(payload, line),
        booking_line_ends_at(payload, line),
        excluded_basket_id=excluded_basket_id,
    )
    available_quantity = stock_quantity - overlapping_quantity
    requested_quantity = max_payload_stock_quantity(payload, line)
    return build_availability_line(
        line,
        available=available_quantity >= requested_quantity,
        available_quantity=available_quantity,
        reason=None
        if available_quantity >= requested_quantity
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
    asset_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_basket_id: UUID | None = None,
) -> bool:
    result = await session.execute(
        basket_hold_query(starts_at, ends_at, excluded_basket_id=excluded_basket_id)
        .with_only_columns(BasketLine.id)
        .where(BasketLine.asset_id == asset_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_overlapping_stock_basket_quantity(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_basket_id: UUID | None = None,
) -> int:
    result = await session.execute(
        basket_hold_query(starts_at, ends_at, excluded_basket_id=excluded_basket_id)
        .with_only_columns(func.coalesce(func.sum(BasketLine.quantity), 0))
        .where(
            BasketLine.asset_id == asset_id,
            BasketLine.location_id == location_id,
        )
    )
    return int(result.scalar_one())


async def get_overlapping_stock_basket_quantity_for_range(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    excluded_basket_id: UUID | None = None,
) -> int:
    filters = [
        BasketLine.asset_id == asset_id,
        Basket.status == BasketStatus.ACTIVE,
        Basket.expires_at > datetime.now(UTC),
        BasketLine.starts_at < ends_at,
        BasketLine.ends_at > starts_at,
    ]
    if location_id is not None:
        filters.append(BasketLine.location_id == location_id)
    if excluded_basket_id is not None:
        filters.append(Basket.id != excluded_basket_id)

    result = await session.execute(
        select(func.coalesce(func.sum(BasketLine.quantity), 0))
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(*filters)
    )
    return int(result.scalar_one())


async def build_stock_availability_day(
    session: AsyncSession,
    *,
    asset_id: UUID,
    location_id: UUID | None,
    quantity: int,
    bucket_start: datetime,
    bucket_end: datetime,
    excluded_basket_id: UUID | None,
) -> AvailabilityDayRead:
    total_quantity = await get_available_stock_quantity_for_heatmap(session, asset_id, location_id)
    reserved_quantity = await get_overlapping_stock_quantity_for_range(
        session,
        asset_id,
        location_id,
        bucket_start,
        bucket_end,
    )
    held_quantity = await get_overlapping_stock_basket_quantity_for_range(
        session,
        asset_id,
        location_id,
        bucket_start,
        bucket_end,
        excluded_basket_id=excluded_basket_id,
    )
    available_quantity = max(0, total_quantity - reserved_quantity - held_quantity)
    return AvailabilityDayRead(
        bucket_start=bucket_start,
        bucket_end=bucket_end,
        total_quantity=total_quantity,
        reserved_quantity=reserved_quantity,
        held_quantity=held_quantity,
        available_quantity=available_quantity,
        requested_quantity=quantity,
        available=available_quantity >= quantity,
        reason=None if available_quantity >= quantity else "Not enough stock available.",
    )


async def build_tracked_availability_day(
    session: AsyncSession,
    *,
    asset_id: UUID,
    quantity: int,
    bucket_start: datetime,
    bucket_end: datetime,
    excluded_basket_id: UUID | None,
) -> AvailabilityDayRead:
    unit = await get_primary_tracked_unit(session, asset_id)
    physical_available = 1 if unit is not None and unit.status == AssetStatus.AVAILABLE else 0
    reserved_quantity = await get_overlapping_tracked_quantity_for_range(
        session,
        asset_id,
        bucket_start,
        bucket_end,
    )
    held_quantity = await get_overlapping_tracked_basket_quantity_for_range(
        session,
        asset_id,
        bucket_start,
        bucket_end,
        excluded_basket_id=excluded_basket_id,
    )
    available_quantity = max(0, physical_available - reserved_quantity - held_quantity)
    return AvailabilityDayRead(
        bucket_start=bucket_start,
        bucket_end=bucket_end,
        total_quantity=physical_available,
        reserved_quantity=reserved_quantity,
        held_quantity=held_quantity,
        available_quantity=available_quantity,
        requested_quantity=quantity,
        available=quantity == 1 and available_quantity >= 1,
        reason=None if quantity == 1 and available_quantity >= 1 else "Tracked item unavailable.",
    )


async def get_overlapping_tracked_quantity_for_range(
    session: AsyncSession,
    asset_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    result = await session.execute(
        select(BookingLine.id)
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(
            BookingLine.asset_id == asset_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            BookingLine.starts_at < ends_at,
            BookingLine.ends_at > starts_at,
        )
        .limit(1)
    )
    return 1 if result.scalar_one_or_none() is not None else 0


async def get_overlapping_tracked_basket_quantity_for_range(
    session: AsyncSession,
    asset_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_basket_id: UUID | None = None,
) -> int:
    filters = [
        BasketLine.asset_id == asset_id,
        Basket.status == BasketStatus.ACTIVE,
        Basket.expires_at > datetime.now(UTC),
        BasketLine.starts_at < ends_at,
        BasketLine.ends_at > starts_at,
    ]
    if excluded_basket_id is not None:
        filters.append(Basket.id != excluded_basket_id)

    result = await session.execute(
        select(BasketLine.id)
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(*filters)
        .limit(1)
    )
    return 1 if result.scalar_one_or_none() is not None else 0


async def get_active_basket_id_for_user(session: AsyncSession, user_id: UUID) -> UUID | None:
    result = await session.execute(
        select(Basket.id)
        .where(
            Basket.user_id == user_id,
            Basket.status == BasketStatus.ACTIVE,
            Basket.expires_at > datetime.now(UTC),
        )
        .order_by(Basket.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_heatmap_stock_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(
        select(Asset).where(Asset.asset_type == AssetType.STOCK).order_by(Asset.name)
    )
    return list(result.scalars().all())


async def list_heatmap_stock_totals(
    session: AsyncSession,
    location_id: UUID | None,
) -> list[tuple[UUID, str, str | None, int]]:
    filters = [
        Asset.asset_type == AssetType.STOCK,
        StockBatch.holder_user_id.is_(None),
        StockBatch.status == AssetStatus.AVAILABLE,
    ]
    if location_id is not None:
        filters.append(StockBatch.location_id == location_id)

    result = await session.execute(
        select(
            Asset.id,
            Asset.name,
            Asset.unit_name,
            func.coalesce(func.sum(StockBatch.quantity), 0).label("total_quantity"),
        )
        .join(StockBatch, StockBatch.asset_id == Asset.id)
        .where(*filters)
        .group_by(Asset.id, Asset.name, Asset.unit_name)
        .having(func.coalesce(func.sum(StockBatch.quantity), 0) > 0)
        .order_by(Asset.name)
    )
    return [
        (asset_id, name, unit_name, int(total_quantity))
        for asset_id, name, unit_name, total_quantity in result.all()
    ]


async def list_heatmap_tracked_totals(
    session: AsyncSession,
    location_id: UUID | None,
) -> list[tuple[UUID, str, str | None, int, int]]:
    filters = [Asset.asset_type == AssetType.TRACKED]
    if location_id is not None:
        filters.append(TrackedUnit.current_location_id == location_id)

    result = await session.execute(
        select(
            Asset.id,
            Asset.name,
            Asset.unit_name,
            TrackedUnit.status,
        )
        .join(TrackedUnit, TrackedUnit.asset_id == Asset.id)
        .where(*filters)
        .order_by(Asset.name, TrackedUnit.created_at)
    )
    seen_asset_ids: set[UUID] = set()
    tracked_assets: list[tuple[UUID, str, str | None, int, int]] = []
    for asset_id, name, unit_name, unit_status in result.all():
        if asset_id in seen_asset_ids:
            continue
        seen_asset_ids.add(asset_id)
        physical_available = 1 if unit_status == AssetStatus.AVAILABLE else 0
        tracked_assets.append((asset_id, name, unit_name or "item", 1, physical_available))
    return tracked_assets


async def list_heatmap_booking_impacts(
    session: AsyncSession,
    *,
    starts_at: datetime,
    ends_at: datetime,
    asset_ids: list[UUID],
    location_id: UUID | None,
) -> list[tuple[UUID, int, datetime, datetime]]:
    if not asset_ids:
        return []

    filters = [
        BookingLine.asset_id.in_(asset_ids),
        BookingLine.quantity.is_not(None),
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        BookingLine.starts_at < ends_at,
        BookingLine.ends_at > starts_at,
    ]
    if location_id is not None:
        filters.append(BookingLine.location_id == location_id)

    result = await session.execute(
        select(
            BookingLine.asset_id,
            BookingLine.quantity,
            BookingLine.starts_at,
            BookingLine.ends_at,
        )
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(*filters)
    )
    return [
        (asset_id, int(quantity or 0), booking_starts_at, booking_ends_at)
        for asset_id, quantity, booking_starts_at, booking_ends_at in result.all()
    ]


async def list_heatmap_basket_impacts(
    session: AsyncSession,
    *,
    starts_at: datetime,
    ends_at: datetime,
    asset_ids: list[UUID],
    location_id: UUID | None,
) -> list[tuple[UUID, int, datetime, datetime]]:
    if not asset_ids:
        return []

    filters = [
        BasketLine.asset_id.in_(asset_ids),
        BasketLine.quantity.is_not(None),
        Basket.status == BasketStatus.ACTIVE,
        Basket.expires_at > datetime.now(UTC),
        BasketLine.starts_at < ends_at,
        BasketLine.ends_at > starts_at,
    ]
    if location_id is not None:
        filters.append(BasketLine.location_id == location_id)

    result = await session.execute(
        select(
            BasketLine.asset_id,
            BasketLine.quantity,
            BasketLine.starts_at,
            BasketLine.ends_at,
        )
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(*filters)
    )
    return [
        (asset_id, int(quantity or 0), basket_starts_at, basket_ends_at)
        for asset_id, quantity, basket_starts_at, basket_ends_at in result.all()
    ]


async def list_heatmap_tracked_booking_impacts(
    session: AsyncSession,
    *,
    starts_at: datetime,
    ends_at: datetime,
    asset_ids: list[UUID],
) -> list[tuple[UUID, int, datetime, datetime]]:
    if not asset_ids:
        return []

    result = await session.execute(
        select(
            BookingLine.asset_id,
            BookingLine.starts_at,
            BookingLine.ends_at,
        )
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(
            BookingLine.asset_id.in_(asset_ids),
            BookingLine.quantity.is_(None),
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            BookingLine.starts_at < ends_at,
            BookingLine.ends_at > starts_at,
        )
    )
    return [
        (asset_id, 1, booking_starts_at, booking_ends_at)
        for asset_id, booking_starts_at, booking_ends_at in result.all()
    ]


async def list_heatmap_tracked_basket_impacts(
    session: AsyncSession,
    *,
    starts_at: datetime,
    ends_at: datetime,
    asset_ids: list[UUID],
) -> list[tuple[UUID, int, datetime, datetime]]:
    if not asset_ids:
        return []

    result = await session.execute(
        select(
            BasketLine.asset_id,
            BasketLine.starts_at,
            BasketLine.ends_at,
        )
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(
            BasketLine.asset_id.in_(asset_ids),
            BasketLine.quantity.is_(None),
            Basket.status == BasketStatus.ACTIVE,
            Basket.expires_at > datetime.now(UTC),
            BasketLine.starts_at < ends_at,
            BasketLine.ends_at > starts_at,
        )
    )
    return [
        (asset_id, 1, basket_starts_at, basket_ends_at)
        for asset_id, basket_starts_at, basket_ends_at in result.all()
    ]


def initialize_heatmap_quantities(
    asset_ids: list[UUID],
    buckets: list[tuple[datetime, datetime]],
) -> dict[UUID, list[int]]:
    return {asset_id: [0 for _bucket in buckets] for asset_id in asset_ids}


async def aggregate_heatmap_booking_quantities_postgresql(
    session: AsyncSession,
    *,
    buckets: list[tuple[datetime, datetime]],
    starts_at: datetime,
    ends_at: datetime,
    bucket: str,
    asset_ids: list[UUID],
    location_id: UUID | None,
) -> dict[UUID, list[int]]:
    quantities = initialize_heatmap_quantities(asset_ids, buckets)
    if not asset_ids:
        return quantities

    filters = [
        "bl.quantity IS NOT NULL",
        "a.asset_type = 'stock'",
        "bk.status IN ('reserved', 'checked_out')",
        "bl.starts_at < :ends_at",
        "bl.ends_at > :starts_at",
    ]
    if location_id is not None:
        filters.append("bl.location_id = :location_id")
    rows = await session.execute(
        text(
            f"""
            WITH buckets AS (
                SELECT
                    series.bucket_start,
                    LEAST(
                        series.bucket_start + (:step_seconds * INTERVAL '1 second'),
                        CAST(:ends_at AS TIMESTAMP WITH TIME ZONE)
                    ) AS bucket_end
                FROM generate_series(
                    CAST(:starts_at AS TIMESTAMP WITH TIME ZONE),
                    CAST(:ends_at AS TIMESTAMP WITH TIME ZONE)
                        - (:step_seconds * INTERVAL '1 second'),
                    :step_seconds * INTERVAL '1 second'
                ) AS series(bucket_start)
            )
            SELECT
                bl.asset_id,
                buckets.bucket_start,
                COALESCE(SUM(bl.quantity), 0) AS quantity
            FROM buckets
            JOIN booking_lines bl
                ON bl.starts_at < buckets.bucket_end
                AND bl.ends_at > buckets.bucket_start
            JOIN bookings bk ON bl.booking_id = bk.id
            JOIN assets a ON a.id = bl.asset_id
            WHERE {" AND ".join(filters)}
            GROUP BY bl.asset_id, buckets.bucket_start
            """
        ),
        {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "step_seconds": heatmap_step_seconds(bucket),
            "location_id": location_id,
        },
    )
    apply_aggregated_heatmap_rows(quantities, buckets, rows.all())
    return quantities


async def aggregate_heatmap_basket_quantities_postgresql(
    session: AsyncSession,
    *,
    buckets: list[tuple[datetime, datetime]],
    starts_at: datetime,
    ends_at: datetime,
    bucket: str,
    asset_ids: list[UUID],
    location_id: UUID | None,
) -> dict[UUID, list[int]]:
    quantities = initialize_heatmap_quantities(asset_ids, buckets)
    if not asset_ids:
        return quantities

    filters = [
        "bal.quantity IS NOT NULL",
        "a.asset_type = 'stock'",
        "ba.status = 'active'",
        "ba.expires_at > :now",
        "bal.starts_at < :ends_at",
        "bal.ends_at > :starts_at",
    ]
    if location_id is not None:
        filters.append("bal.location_id = :location_id")
    rows = await session.execute(
        text(
            f"""
            WITH buckets AS (
                SELECT
                    series.bucket_start,
                    LEAST(
                        series.bucket_start + (:step_seconds * INTERVAL '1 second'),
                        CAST(:ends_at AS TIMESTAMP WITH TIME ZONE)
                    ) AS bucket_end
                FROM generate_series(
                    CAST(:starts_at AS TIMESTAMP WITH TIME ZONE),
                    CAST(:ends_at AS TIMESTAMP WITH TIME ZONE)
                        - (:step_seconds * INTERVAL '1 second'),
                    :step_seconds * INTERVAL '1 second'
                ) AS series(bucket_start)
            )
            SELECT
                bal.asset_id,
                buckets.bucket_start,
                COALESCE(SUM(bal.quantity), 0) AS quantity
            FROM buckets
            JOIN basket_lines bal
                ON bal.starts_at < buckets.bucket_end
                AND bal.ends_at > buckets.bucket_start
            JOIN baskets ba ON bal.basket_id = ba.id
            JOIN assets a ON a.id = bal.asset_id
            WHERE {" AND ".join(filters)}
            GROUP BY bal.asset_id, buckets.bucket_start
            """
        ),
        {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "step_seconds": heatmap_step_seconds(bucket),
            "location_id": location_id,
            "now": datetime.now(UTC),
        },
    )
    apply_aggregated_heatmap_rows(quantities, buckets, rows.all())
    return quantities


def apply_aggregated_heatmap_rows(
    quantities_by_asset: dict[UUID, list[int]],
    buckets: list[tuple[datetime, datetime]],
    rows: list[tuple[UUID | str, datetime, int]],
) -> None:
    bucket_indexes = {
        comparable_datetime(bucket_start): index
        for index, (bucket_start, _bucket_end) in enumerate(buckets)
    }
    for raw_asset_id, bucket_start, quantity in rows:
        asset_quantities = quantities_by_asset.get(normalize_uuid(raw_asset_id))
        bucket_index = bucket_indexes.get(comparable_datetime(bucket_start))
        if asset_quantities is None or bucket_index is None:
            continue
        asset_quantities[bucket_index] = int(quantity)


def apply_heatmap_impacts(
    quantities_by_asset: dict[UUID, list[int]],
    buckets: list[tuple[datetime, datetime]],
    impacts: list[tuple[UUID, int, datetime, datetime]],
) -> None:
    comparable_buckets = [
        (comparable_datetime(bucket_start), comparable_datetime(bucket_end))
        for bucket_start, bucket_end in buckets
    ]
    for asset_id, quantity, starts_at, ends_at in impacts:
        asset_quantities = quantities_by_asset.get(asset_id)
        if asset_quantities is None or quantity <= 0:
            continue
        comparable_starts_at = comparable_datetime(starts_at)
        comparable_ends_at = comparable_datetime(ends_at)
        for index, (bucket_start, bucket_end) in enumerate(comparable_buckets):
            if comparable_starts_at < bucket_end and comparable_ends_at > bucket_start:
                asset_quantities[index] += quantity


def comparable_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def heatmap_step_seconds(bucket: str) -> int:
    return 86_400 if bucket == "day" else 604_800


def normalize_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def is_postgresql_session(session: AsyncSession) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def read_heatmap_cache(cache_key: HeatmapCacheKey) -> AvailabilityHeatmapRead | None:
    heatmap = heatmap_cache.get(cache_key)
    if heatmap is None:
        return None
    heatmap_cache.move_to_end(cache_key)
    return heatmap


def write_heatmap_cache(cache_key: HeatmapCacheKey, heatmap: AvailabilityHeatmapRead) -> None:
    heatmap_cache[cache_key] = heatmap
    heatmap_cache.move_to_end(cache_key)
    while len(heatmap_cache) > HEATMAP_CACHE_MAX_ITEMS:
        heatmap_cache.popitem(last=False)


async def get_heatmap_state_fingerprint(session: AsyncSession) -> tuple[object, ...]:
    relevant_tables = (Asset, StockBatch, TrackedUnit, Booking, BookingLine, Basket, BasketLine)
    fingerprint: list[object] = []
    for table in relevant_tables:
        result = await session.execute(select(func.count(table.id), func.max(table.updated_at)))
        row_count, max_updated_at = result.one()
        fingerprint.extend((row_count, max_updated_at))
    return tuple(fingerprint)


async def count_where(session: AsyncSession, statement) -> int:
    return int((await session.execute(statement)).scalar_one())


def build_heatmap_buckets(
    starts_at: datetime,
    ends_at: datetime,
    bucket: str,
) -> list[tuple[datetime, datetime]]:
    if starts_at >= ends_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="starts_at must be before ends_at.",
        )
    if bucket == "day":
        step = timedelta(days=1)
    elif bucket == "week":
        step = timedelta(weeks=1)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="bucket must be day or week.",
        )

    buckets: list[tuple[datetime, datetime]] = []
    cursor = starts_at
    while cursor < ends_at:
        next_cursor = min(cursor + step, ends_at)
        buckets.append((cursor, next_cursor))
        cursor = next_cursor
        if len(buckets) > HEATMAP_MAX_BUCKETS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Heatmap range is too large.",
            )
    return buckets


async def get_overlapping_stock_quantity_for_range(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    filters = [
        BookingLine.asset_id == asset_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        BookingLine.starts_at < ends_at,
        BookingLine.ends_at > starts_at,
    ]
    if location_id is not None:
        filters.append(BookingLine.location_id == location_id)

    result = await session.execute(
        select(func.coalesce(func.sum(BookingLine.quantity), 0))
        .join(Booking, BookingLine.booking_id == Booking.id)
        .where(*filters)
    )
    return int(result.scalar_one())


def basket_hold_query(
    starts_at: datetime,
    ends_at: datetime,
    *,
    excluded_basket_id: UUID | None = None,
):
    query = (
        select(BasketLine)
        .join(Basket, BasketLine.basket_id == Basket.id)
        .where(
            Basket.status == BasketStatus.ACTIVE,
            Basket.expires_at > datetime.now(UTC),
            BasketLine.starts_at < ends_at,
            BasketLine.ends_at > starts_at,
        )
    )
    if excluded_basket_id is not None:
        query = query.where(Basket.id != excluded_basket_id)
    return query
