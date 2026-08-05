from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audited_item_event
from inventory_booking_api.core.locks import acquire_advisory_locks, asset_lock_key
from inventory_booking_api.inventory.asset_schemas import (
    StockLevelRead,
    StockTransfer,
    TrackedAssetTransfer,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch
from inventory_booking_api.inventory.state import (
    apply_primary_unit_state,
    copy_unit_state_to_asset,
    get_available_stock_batch,
    get_mergeable_stock_batch,
    require_primary_tracked_unit,
    stock_batch_to_read,
)
from inventory_booking_api.users.models import User


async def transfer_tracked_asset(
    session: AsyncSession,
    asset: Asset,
    payload: TrackedAssetTransfer,
    actor: User,
) -> Asset:
    await acquire_advisory_locks(session, [asset_lock_key(asset.id)])
    if asset.asset_type != AssetType.TRACKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only tracked item definitions can use tracked transfer.",
        )
    unit = await require_primary_tracked_unit(session, asset)
    if unit.status in (AssetStatus.CHECKED_OUT, AssetStatus.LOST, AssetStatus.RETIRED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tracked unit in status {unit.status.value} cannot be transferred.",
        )

    from_location_id = unit.current_location_id
    unit.current_location_id = payload.to_location_id
    unit.current_holder_user_id = payload.to_holder_user_id
    copy_unit_state_to_asset(asset, unit)
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.MOVED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="asset",
        audit_entity_id=unit.id,
        audit_summary=f"Transferred asset {asset.name}",
        item_notes=payload.notes,
        item_details={
            "tracked_unit_id": str(unit.id),
            "from_location_id": str(from_location_id) if from_location_id else None,
            "to_location_id": str(payload.to_location_id) if payload.to_location_id else None,
            "to_holder_user_id": str(payload.to_holder_user_id)
            if payload.to_holder_user_id
            else None,
        },
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def transfer_stock(
    session: AsyncSession,
    payload: StockTransfer,
    actor: User,
) -> tuple[StockLevelRead, StockLevelRead]:
    await acquire_advisory_locks(session, [asset_lock_key(payload.asset_id)])
    if payload.from_location_id == payload.to_location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination locations must differ.",
        )

    asset = await session.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset does not exist.")
    if asset.asset_type != AssetType.STOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only stock item definitions can use stock transfer.",
        )

    source = await get_available_stock_batch(session, payload.asset_id, payload.from_location_id)
    if source is None or source.quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough available stock to transfer.",
        )

    source.quantity -= payload.quantity
    destination = await get_mergeable_stock_batch(session, payload.asset_id, payload.to_location_id)
    if destination is None:
        destination = StockBatch(
            asset_id=payload.asset_id,
            location_id=payload.to_location_id,
            quantity=payload.quantity,
            status=AssetStatus.AVAILABLE,
            condition=source.condition,
        )
        session.add(destination)
        await session.flush()
    else:
        destination.quantity += payload.quantity

    if source.quantity == 0:
        await session.delete(source)
        source_read = StockLevelRead(
            id=source.id,
            asset_id=source.asset_id,
            location_id=source.location_id,
            quantity_total=0,
            quantity_reserved=0,
            quantity_checked_out=0,
        )
    else:
        source_read = await stock_batch_to_read(session, source)

    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.MOVED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="stock_batch",
        audit_entity_id=destination.id,
        audit_summary=f"Transferred {payload.quantity} {asset.name}",
        item_notes=payload.notes,
        item_details={
            "from_location_id": str(payload.from_location_id),
            "to_location_id": str(payload.to_location_id),
            "quantity": payload.quantity,
        },
    )
    await session.commit()
    await session.refresh(destination)
    return source_read, await stock_batch_to_read(session, destination)


