from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus
from inventory_booking_api.inventory.models import StockBatch
from inventory_booking_api.inventory.state import get_mergeable_stock_batch


@dataclass(frozen=True)
class StockPortion:
    condition: AssetCondition
    quantity: int


async def consume_stock_batches(
    session: AsyncSession,
    batches: list[StockBatch],
    quantity: int,
) -> list[StockPortion]:
    if quantity < 1 or sum(batch.quantity for batch in batches) < quantity:
        raise ValueError("Stock batch quantity is insufficient.")

    remaining = quantity
    quantities_by_condition: dict[AssetCondition, int] = {}
    for batch in batches:
        consumed = min(batch.quantity, remaining)
        quantities_by_condition[batch.condition] = (
            quantities_by_condition.get(batch.condition, 0) + consumed
        )
        batch.quantity -= consumed
        remaining -= consumed
        if batch.quantity == 0:
            await session.delete(batch)
        if remaining == 0:
            break

    return [
        StockPortion(condition=condition, quantity=portion_quantity)
        for condition, portion_quantity in quantities_by_condition.items()
    ]


async def merge_available_stock(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    condition: AssetCondition,
    quantity: int,
) -> StockBatch:
    batch = await get_mergeable_stock_batch(session, asset_id, location_id, condition)
    if batch is None:
        batch = StockBatch(
            asset_id=asset_id,
            location_id=location_id,
            holder_user_id=None,
            checkout_line_id=None,
            status=AssetStatus.AVAILABLE,
            condition=condition,
            quantity=quantity,
        )
        session.add(batch)
    else:
        batch.quantity += quantity
    return batch


async def merge_available_portions(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    portions: list[StockPortion],
) -> list[StockBatch]:
    return [
        await merge_available_stock(
            session,
            asset_id,
            location_id,
            portion.condition,
            portion.quantity,
        )
        for portion in portions
    ]
