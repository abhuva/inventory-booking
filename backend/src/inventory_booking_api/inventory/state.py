from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import ItemEventType
from inventory_booking_api.inventory.asset_schemas import StockLevelRead
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit


async def get_primary_tracked_unit(session: AsyncSession, asset_id: UUID) -> TrackedUnit | None:
    result = await session.execute(
        select(TrackedUnit).where(TrackedUnit.asset_id == asset_id).order_by(TrackedUnit.created_at)
    )
    return result.scalars().first()


async def require_primary_tracked_unit(session: AsyncSession, asset: Asset) -> TrackedUnit:
    if asset.asset_type != AssetType.TRACKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only tracked item definitions support this operation.",
        )
    unit = await get_primary_tracked_unit(session, asset.id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tracked unit missing.")
    return unit


async def apply_primary_unit_state(session: AsyncSession, asset: Asset) -> None:
    if asset.asset_type != AssetType.TRACKED:
        return
    unit = await get_primary_tracked_unit(session, asset.id)
    if unit is not None:
        copy_unit_state_to_asset(asset, unit)


def copy_unit_state_to_asset(asset: Asset, unit: TrackedUnit) -> None:
    asset.status = unit.status
    asset.condition = unit.condition
    asset.current_location_id = unit.current_location_id
    asset.current_holder_user_id = unit.current_holder_user_id
    asset.manufacturer = unit.manufacturer
    asset.model = unit.model
    asset.serial_number = unit.serial_number
    asset.asset_tag = unit.asset_tag
    asset.replacement_value = unit.replacement_value
    asset.notes = unit.notes


async def get_available_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> StockBatch | None:
    result = await session.execute(
        select(StockBatch)
        .where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.holder_user_id.is_(None),
            StockBatch.status == AssetStatus.AVAILABLE,
        )
        .order_by(StockBatch.created_at)
    )
    return result.scalars().first()


async def get_mergeable_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> StockBatch | None:
    return await get_available_stock_batch(session, asset_id, location_id)


async def get_display_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> StockBatch | None:
    available_batch = await get_available_stock_batch(session, asset_id, location_id)
    if available_batch is not None:
        return available_batch
    return await get_checked_out_stock_batch(session, asset_id, location_id)


async def stock_batch_to_read(session: AsyncSession, batch: StockBatch) -> StockLevelRead:
    checked_out_quantity = await get_checked_out_stock_quantity(
        session,
        batch.asset_id,
        batch.location_id,
    )
    available_quantity = batch.quantity if batch.status == AssetStatus.AVAILABLE else 0
    return StockLevelRead(
        id=batch.id,
        asset_id=batch.asset_id,
        location_id=batch.location_id,
        quantity_total=available_quantity + checked_out_quantity,
        quantity_reserved=0,
        quantity_checked_out=checked_out_quantity,
    )


async def get_checked_out_stock_quantity(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> int:
    result = await session.execute(
        select(StockBatch.quantity).where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.status == AssetStatus.CHECKED_OUT,
        )
    )
    return sum(result.scalars().all())


async def get_checked_out_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> StockBatch | None:
    result = await session.execute(
        select(StockBatch).where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.status == AssetStatus.CHECKED_OUT,
        )
    )
    return result.scalars().first()


def asset_state_event_type(status_value: AssetStatus) -> ItemEventType:
    if status_value == AssetStatus.DAMAGED:
        return ItemEventType.DAMAGED
    if status_value == AssetStatus.LOST:
        return ItemEventType.LOST
    if status_value == AssetStatus.RETIRED:
        return ItemEventType.RETIRED
    return ItemEventType.FOUND


async def count_where(session: AsyncSession, statement) -> int:
    return int((await session.execute(statement)).scalar_one())
