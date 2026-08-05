from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import (
    AvailabilityDayRead,
    AvailabilityDaysRead,
    AvailabilityLineRead,
    AvailabilityRead,
    BookingCreate,
    BookingLineCreate,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.users.models import User

ACTIVE_BOOKING_STATUSES = (BookingStatus.RESERVED, BookingStatus.CHECKED_OUT)
HEATMAP_MAX_BUCKETS = 370


def comparable_datetime(value: datetime) -> datetime:
    """Normalize aware datetimes for reliable overlap comparisons."""

    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def ranges_overlap(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    return comparable_datetime(left_start) < comparable_datetime(right_end) and comparable_datetime(
        left_end
    ) > comparable_datetime(right_start)


def max_concurrent_quantity(
    impacts: list[tuple[int, datetime, datetime]],
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    """Return the highest simultaneous quantity impact inside a requested range."""

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


def booking_line_starts_at(payload: BookingCreate, line: BookingLineCreate) -> datetime:
    return line.starts_at if line.starts_at is not None else payload.starts_at


def booking_line_ends_at(payload: BookingCreate, line: BookingLineCreate) -> datetime:
    return line.ends_at if line.ends_at is not None else payload.ends_at



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

