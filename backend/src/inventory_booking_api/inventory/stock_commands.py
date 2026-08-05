from fastapi import HTTPException, status
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
    get_checked_out_stock_batch,
    get_mergeable_stock_batch,
    stock_batch_to_read,
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
    batch = await get_mergeable_stock_batch(session, payload.asset_id, payload.location_id)
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
    values = payload.model_dump(exclude_unset=True)
    aggregate = await stock_batch_to_read(session, batch)
    response_override: StockLevelRead | None = None
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
        available_quantity = values["quantity_total"] - checked_out_quantity
        if available_quantity == 0 and batch.status == AssetStatus.AVAILABLE:
            response_override = StockLevelRead(
                id=batch.id,
                asset_id=batch.asset_id,
                location_id=batch.location_id,
                quantity_total=checked_out_quantity,
                quantity_reserved=0,
                quantity_checked_out=checked_out_quantity,
            )
            await session.delete(batch)
        elif batch.status == AssetStatus.AVAILABLE:
            batch.quantity = available_quantity
        else:
            response_override = StockLevelRead(
                id=batch.id,
                asset_id=batch.asset_id,
                location_id=batch.location_id,
                quantity_total=checked_out_quantity,
                quantity_reserved=0,
                quantity_checked_out=checked_out_quantity,
            )
    if "quantity_checked_out" in values:
        checked_out_quantity = values["quantity_checked_out"] or 0
        if checked_out_quantity < 0 or checked_out_quantity >= aggregate.quantity_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Checked-out quantity must be lower than total quantity.",
            )
        available_quantity = aggregate.quantity_total - checked_out_quantity
        batch.quantity = available_quantity
        checked_out_batch = await get_checked_out_stock_batch(
            session,
            batch.asset_id,
            batch.location_id,
        )
        if checked_out_quantity == 0 and checked_out_batch is not None:
            await session.delete(checked_out_batch)
        elif checked_out_batch is None:
            session.add(
                StockBatch(
                    asset_id=batch.asset_id,
                    location_id=batch.location_id,
                    quantity=checked_out_quantity,
                    status=AssetStatus.CHECKED_OUT,
                    condition=batch.condition,
                )
            )
        else:
            checked_out_batch.quantity = checked_out_quantity
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=batch.asset_id,
        event_type=ItemEventType.UPDATED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="stock_level",
        audit_entity_id=batch.id,
        audit_summary="Updated stock level",
        item_notes="Updated stock batch",
        item_details={"stock_batch_id": str(batch.id), "quantity": batch.quantity},
    )
    await session.commit()
    if response_override is not None:
        return response_override
    await session.refresh(batch)
    return await stock_batch_to_read(session, batch)


