from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.models import ItemEvent
from inventory_booking_api.baskets.models import BasketLine
from inventory_booking_api.bookings.models import BookingLine
from inventory_booking_api.checkouts.models import CheckoutLine
from inventory_booking_api.inventory.asset_schemas import StockLevelRead
from inventory_booking_api.inventory.enums import AssetType
from inventory_booking_api.inventory.models import Asset, AssetImage, StockBatch, TrackedUnit
from inventory_booking_api.inventory.state import (
    apply_primary_unit_state,
    count_where,
    get_display_stock_batch,
    stock_batch_to_read,
)
from inventory_booking_api.qr.models import QrCode
from inventory_booking_api.returns.models import ReturnLine


async def list_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(select(Asset).order_by(Asset.name))
    assets = list(result.scalars().all())
    for asset in assets:
        await apply_primary_unit_state(session, asset)
    return assets


async def get_asset(session: AsyncSession, asset_id: UUID) -> Asset | None:
    asset = await session.get(Asset, asset_id)
    if asset is not None:
        await apply_primary_unit_state(session, asset)
    return asset


async def get_inventory_total_value(session: AsyncSession) -> Decimal:
    tracked_result = await session.execute(
        select(func.coalesce(func.sum(TrackedUnit.replacement_value), Decimal("0.00")))
    )
    stock_result = await session.execute(
        select(
            func.coalesce(
                func.sum(Asset.replacement_value * StockBatch.quantity),
                Decimal("0.00"),
            )
        )
        .join(StockBatch, StockBatch.asset_id == Asset.id)
        .where(Asset.asset_type == AssetType.STOCK)
    )
    return Decimal(tracked_result.scalar_one()) + Decimal(stock_result.scalar_one())


async def asset_reference_counts(session: AsyncSession, asset_id: UUID) -> dict[str, int]:
    return {
        "booking_lines": await count_where(
            session, select(func.count(BookingLine.id)).where(BookingLine.asset_id == asset_id)
        ),
        "basket_lines": await count_where(
            session, select(func.count(BasketLine.id)).where(BasketLine.asset_id == asset_id)
        ),
        "checkout_lines": await count_where(
            session, select(func.count(CheckoutLine.id)).where(CheckoutLine.asset_id == asset_id)
        ),
        "return_lines": await count_where(
            session, select(func.count(ReturnLine.id)).where(ReturnLine.asset_id == asset_id)
        ),
        "item_events": await count_where(
            session, select(func.count(ItemEvent.id)).where(ItemEvent.asset_id == asset_id)
        ),
        "stock_batches": await count_where(
            session, select(func.count(StockBatch.id)).where(StockBatch.asset_id == asset_id)
        ),
        "tracked_units": await count_where(
            session, select(func.count(TrackedUnit.id)).where(TrackedUnit.asset_id == asset_id)
        ),
        "asset_images": await count_where(
            session, select(func.count(AssetImage.id)).where(AssetImage.asset_id == asset_id)
        ),
        "qr_codes": await count_where(
            session, select(func.count(QrCode.id)).where(QrCode.asset_id == asset_id)
        ),
    }


async def list_stock_levels(session: AsyncSession) -> list[StockLevelRead]:
    result = await session.execute(
        select(StockBatch)
        .where(StockBatch.holder_user_id.is_(None))
        .order_by(StockBatch.created_at)
    )
    stock_levels: list[StockLevelRead] = []
    seen: set[tuple[UUID, UUID | None]] = set()
    for batch in result.scalars().all():
        key = (batch.asset_id, batch.location_id)
        if key in seen:
            continue
        seen.add(key)
        stock_levels.append(await stock_batch_to_read(session, batch))
    return stock_levels


async def get_stock_level(session: AsyncSession, stock_level_id: UUID) -> StockLevelRead | None:
    batch = await session.get(StockBatch, stock_level_id)
    if batch is None:
        return None
    batch = await get_display_stock_batch(session, batch.asset_id, batch.location_id)
    return await stock_batch_to_read(session, batch) if batch is not None else None
