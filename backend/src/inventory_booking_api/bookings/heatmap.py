from collections import OrderedDict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.bookings.availability import build_heatmap_buckets, comparable_datetime
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import (
    AvailabilityHeatmapRead,
    HeatmapCellRead,
    HeatmapItemRead,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit

RESERVING_BOOKING_STATUSES = (BookingStatus.RESERVED,)
HEATMAP_CACHE_MAX_ITEMS = 24
HeatmapCacheKey = tuple[str, str, str, UUID | None, tuple[object, ...]]
heatmap_cache: OrderedDict[HeatmapCacheKey, AvailabilityHeatmapRead] = OrderedDict()


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
    stock_asset_ids = [
        asset_id
        for asset_id, _name, _unit_name, _total_quantity, _physical_available in stock_assets
    ]
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

    for asset_id, name, unit_name, total_quantity, physical_available in stock_assets:
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
                    available_quantity=max(
                        0,
                        physical_available - reserved_quantity - held_quantity,
                    ),
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


async def list_heatmap_stock_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(
        select(Asset).where(Asset.asset_type == AssetType.STOCK).order_by(Asset.name)
    )
    return list(result.scalars().all())


async def list_heatmap_stock_totals(
    session: AsyncSession,
    location_id: UUID | None,
) -> list[tuple[UUID, str, str | None, int, int]]:
    filters = [
        Asset.asset_type == AssetType.STOCK,
        StockBatch.status.in_((AssetStatus.AVAILABLE, AssetStatus.CHECKED_OUT)),
    ]
    if location_id is not None:
        filters.append(StockBatch.location_id == location_id)

    result = await session.execute(
        select(
            Asset.id,
            Asset.name,
            Asset.unit_name,
            func.coalesce(func.sum(StockBatch.quantity), 0).label("total_quantity"),
            func.coalesce(
                func.sum(
                    case(
                        (StockBatch.status == AssetStatus.AVAILABLE, StockBatch.quantity),
                        else_=0,
                    )
                ),
                0,
            ).label("physical_available"),
        )
        .join(StockBatch, StockBatch.asset_id == Asset.id)
        .where(*filters)
        .group_by(Asset.id, Asset.name, Asset.unit_name)
        .having(func.coalesce(func.sum(StockBatch.quantity), 0) > 0)
        .order_by(Asset.name)
    )
    return [
        (asset_id, name, unit_name, int(total_quantity), int(physical_available))
        for asset_id, name, unit_name, total_quantity, physical_available in result.all()
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
        Booking.status.in_(RESERVING_BOOKING_STATUSES),
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
            Booking.status.in_(RESERVING_BOOKING_STATUSES),
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

    rows = await session.execute(
        text(
            """
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
            WHERE bl.quantity IS NOT NULL
                AND a.asset_type = 'stock'
                AND bk.status = 'reserved'
                AND bl.starts_at < :ends_at
                AND bl.ends_at > :starts_at
                AND (
                    CAST(:location_id AS UUID) IS NULL
                    OR bl.location_id = CAST(:location_id AS UUID)
                )
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

    rows = await session.execute(
        text(
            """
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
            WHERE bal.quantity IS NOT NULL
                AND a.asset_type = 'stock'
                AND ba.status = 'active'
                AND ba.expires_at > :now
                AND bal.starts_at < :ends_at
                AND bal.ends_at > :starts_at
                AND (
                    CAST(:location_id AS UUID) IS NULL
                    OR bal.location_id = CAST(:location_id AS UUID)
                )
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


