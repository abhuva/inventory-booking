from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audited_item_event
from inventory_booking_api.core.locks import acquire_advisory_locks, asset_lock_key
from inventory_booking_api.inventory.asset_schemas import (
    StockLevelCreate,
    StockLevelRead,
    StockLevelUpdate,
)
from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch
from inventory_booking_api.inventory.state import (
    get_display_stock_batch,
    get_mergeable_stock_batch,
    list_available_stock_batches,
    stock_batch_to_read,
)
from inventory_booking_api.inventory.stock_batch_operations import (
    consume_stock_batches,
    merge_available_portions,
    merge_available_stock,
)
from inventory_booking_api.users.models import User


async def create_stock_level(
    session: AsyncSession,
    payload: StockLevelCreate,
    actor: User,
) -> StockLevelRead:
    await acquire_advisory_locks(session, [asset_lock_key(payload.asset_id)])
    asset = await session.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset does not exist.")
    if asset.asset_type != AssetType.STOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock batches can only be created for stock item definitions.",
        )
    batch = await get_mergeable_stock_batch(
        session,
        payload.asset_id,
        payload.location_id,
        AssetCondition.UNKNOWN,
    )
    if batch is None:
        batch = StockBatch(
            asset_id=payload.asset_id,
            location_id=payload.location_id,
            quantity=payload.quantity_total,
            status=AssetStatus.AVAILABLE,
            condition=AssetCondition.UNKNOWN,
        )
        session.add(batch)
    else:
        batch.quantity += payload.quantity_total
    await session.flush()
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        audit_action=AuditAction.CREATE,
        audit_entity_type="stock_level",
        audit_entity_id=batch.id,
        audit_summary=f"Created stock level for {asset.name}",
        item_notes="Created stock batch",
        item_details={
            "stock_batch_id": str(batch.id),
            "location_id": str(batch.location_id) if batch.location_id else None,
            "quantity": payload.quantity_total,
        },
    )
    await session.commit()
    await session.refresh(batch)
    return await stock_batch_to_read(session, batch)


async def update_stock_level(
    session: AsyncSession,
    stock_level: StockLevelRead,
    payload: StockLevelUpdate,
    actor: User,
) -> StockLevelRead:
    batch = await session.get(StockBatch, stock_level.id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock batch not found.")
    await acquire_advisory_locks(session, [asset_lock_key(batch.asset_id)])
    batch_id = batch.id
    asset_id = batch.asset_id
    location_id = batch.location_id
    values = payload.model_dump(exclude_unset=True)
    aggregate = await stock_batch_to_read(session, batch)
    if "quantity_total" in values:
        if values["quantity_total"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock batch quantity is required.",
            )
        checked_out_quantity = aggregate.quantity_checked_out
        if values["quantity_total"] < checked_out_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total quantity cannot be lower than checked-out quantity.",
            )
        target_available = values["quantity_total"] - checked_out_quantity
        current_available = aggregate.quantity_total - checked_out_quantity
        if target_available < current_available:
            available_batches = await list_available_stock_batches(
                session,
                asset_id,
                location_id,
            )
            await consume_stock_batches(
                session,
                available_batches,
                current_available - target_available,
            )
        elif target_available > current_available:
            condition = (
                batch.condition if batch.status == AssetStatus.AVAILABLE else AssetCondition.UNKNOWN
            )
            await merge_available_stock(
                session,
                asset_id,
                location_id,
                condition,
                target_available - current_available,
            )
    if "quantity_checked_out" in values:
        await session.flush()
        display_batch = await get_display_stock_batch(session, asset_id, location_id)
        if display_batch is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set checked-out quantity without stock.",
            )
        aggregate = await stock_batch_to_read(session, display_batch)
        target_checked_out = values["quantity_checked_out"] or 0
        if target_checked_out < 0 or target_checked_out >= aggregate.quantity_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Checked-out quantity must be lower than total quantity.",
            )
        current_checked_out = aggregate.quantity_checked_out
        if target_checked_out > current_checked_out:
            available_batches = await list_available_stock_batches(
                session,
                asset_id,
                location_id,
            )
            portions = await consume_stock_batches(
                session,
                available_batches,
                target_checked_out - current_checked_out,
            )
            for portion in portions:
                checked_out_batch = await get_manual_checked_out_stock_batch(
                    session,
                    asset_id,
                    location_id,
                    portion.condition,
                )
                if checked_out_batch is None:
                    session.add(
                        StockBatch(
                            asset_id=asset_id,
                            location_id=location_id,
                            quantity=portion.quantity,
                            status=AssetStatus.CHECKED_OUT,
                            condition=portion.condition,
                        )
                    )
                else:
                    checked_out_batch.quantity += portion.quantity
        elif target_checked_out < current_checked_out:
            checked_out_batches = await list_checked_out_stock_batches(
                session,
                asset_id,
                location_id,
            )
            if any(item.checkout_line_id is not None for item in checked_out_batches):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Booking checkout quantities must be returned through check-in.",
                )
            portions = await consume_stock_batches(
                session,
                checked_out_batches,
                current_checked_out - target_checked_out,
            )
            await merge_available_portions(
                session,
                asset_id,
                location_id,
                portions,
            )
    await session.flush()
    display_batch = await get_display_stock_batch(session, asset_id, location_id)
    response = (
        await stock_batch_to_read(session, display_batch)
        if display_batch is not None
        else StockLevelRead(
            id=batch_id,
            asset_id=asset_id,
            location_id=location_id,
            quantity_total=0,
            quantity_reserved=0,
            quantity_checked_out=0,
        )
    )
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset_id,
        event_type=ItemEventType.UPDATED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="stock_level",
        audit_entity_id=batch_id,
        audit_summary="Updated stock level",
        item_notes="Updated stock batch",
        item_details={"stock_batch_id": str(batch_id), "quantity": response.quantity_total},
    )
    await session.commit()
    return response


async def list_checked_out_stock_batches(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
) -> list[StockBatch]:
    result = await session.execute(
        select(StockBatch)
        .where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.status == AssetStatus.CHECKED_OUT,
        )
        .order_by(StockBatch.created_at)
    )
    return list(result.scalars().all())


async def get_manual_checked_out_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    condition: AssetCondition,
) -> StockBatch | None:
    result = await session.execute(
        select(StockBatch).where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.status == AssetStatus.CHECKED_OUT,
            StockBatch.checkout_line_id.is_(None),
            StockBatch.holder_user_id.is_(None),
            StockBatch.condition == condition,
        )
    )
    return result.scalars().first()


