from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.inventory.asset_schemas import (
    AssetCreate,
    AssetStateChange,
    AssetUpdate,
    MaintenanceComplete,
    StockLevelCreate,
    StockLevelRead,
    StockLevelUpdate,
    StockTransfer,
    TrackedAssetTransfer,
)
from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.users.models import User

DEFINITION_FIELDS = {"name", "asset_type", "category_id", "unit_name", "description"}
TRACKED_UNIT_FIELDS = {
    "status",
    "condition",
    "current_location_id",
    "current_holder_user_id",
    "manufacturer",
    "model",
    "serial_number",
    "asset_tag",
    "replacement_value",
    "notes",
}


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


async def create_asset(session: AsyncSession, payload: AssetCreate, actor: User) -> Asset:
    values = payload.model_dump()
    definition_values = {key: value for key, value in values.items() if key in DEFINITION_FIELDS}
    asset = Asset(**definition_values)
    session.add(asset)
    await session.flush()

    if asset.asset_type == AssetType.TRACKED:
        unit_values = {key: values.get(key) for key in TRACKED_UNIT_FIELDS if key in values}
        unit = TrackedUnit(asset_id=asset.id, label=asset.name, **unit_values)
        session.add(unit)
        await session.flush()
        copy_unit_state_to_asset(asset, unit)

    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.CREATED,
        actor=actor,
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="asset_definition",
        entity_id=asset.id,
        summary=f"Created asset definition {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def update_asset(
    session: AsyncSession,
    asset: Asset,
    payload: AssetUpdate,
    actor: User,
) -> Asset:
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        if field in DEFINITION_FIELDS:
            setattr(asset, field, value)

    if asset.asset_type == AssetType.TRACKED:
        unit = await get_primary_tracked_unit(session, asset.id)
        if unit is None:
            unit = TrackedUnit(asset_id=asset.id, label=asset.name)
            session.add(unit)
            await session.flush()
        if "name" in values:
            unit.label = values["name"]
        for field, value in values.items():
            if field in TRACKED_UNIT_FIELDS:
                setattr(unit, field, value)
        copy_unit_state_to_asset(asset, unit)

    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="asset_definition",
        entity_id=asset.id,
        summary=f"Updated asset definition {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def list_stock_levels(session: AsyncSession) -> list[StockLevelRead]:
    result = await session.execute(
        select(StockBatch.asset_id, StockBatch.location_id)
        .distinct()
        .order_by(StockBatch.location_id)
    )
    stock_levels: list[StockLevelRead] = []
    for asset_id, location_id in result.all():
        batch = await get_display_stock_batch(session, asset_id, location_id)
        if batch is not None:
            stock_levels.append(await stock_batch_to_read(session, batch))
    return stock_levels


async def get_stock_level(session: AsyncSession, stock_level_id: UUID) -> StockLevelRead | None:
    batch = await session.get(StockBatch, stock_level_id)
    return await stock_batch_to_read(session, batch) if batch is not None else None


async def create_stock_level(
    session: AsyncSession,
    payload: StockLevelCreate,
    actor: User,
) -> StockLevelRead:
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
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Created stock batch",
        details={
            "stock_batch_id": str(batch.id),
            "location_id": str(batch.location_id) if batch.location_id else None,
            "quantity": payload.quantity_total,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="stock_level",
        entity_id=batch.id,
        summary=f"Created stock level for {asset.name}",
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
    values = payload.model_dump(exclude_unset=True)
    aggregate = await stock_batch_to_read(session, batch)
    if "quantity_total" in values:
        if values["quantity_total"] is None or values["quantity_total"] <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock batch quantity must be positive.",
            )
        checked_out_quantity = aggregate.quantity_checked_out
        available_quantity = values["quantity_total"] - checked_out_quantity
        if available_quantity <= 0:
            await session.delete(batch)
        else:
            batch.quantity = available_quantity
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
    await write_item_event(
        session,
        asset_id=batch.asset_id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Updated stock batch",
        details={"stock_batch_id": str(batch.id), "quantity": batch.quantity},
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="stock_level",
        entity_id=batch.id,
        summary="Updated stock level",
    )
    await session.commit()
    await session.refresh(batch)
    return await stock_batch_to_read(session, batch)


async def transfer_tracked_asset(
    session: AsyncSession,
    asset: Asset,
    payload: TrackedAssetTransfer,
    actor: User,
) -> Asset:
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
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.MOVED,
        actor=actor,
        notes=payload.notes,
        details={
            "tracked_unit_id": str(unit.id),
            "from_location_id": str(from_location_id) if from_location_id else None,
            "to_location_id": str(payload.to_location_id) if payload.to_location_id else None,
            "to_holder_user_id": str(payload.to_holder_user_id)
            if payload.to_holder_user_id
            else None,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="asset",
        entity_id=unit.id,
        summary=f"Transferred asset {asset.name}",
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

    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.MOVED,
        actor=actor,
        notes=payload.notes,
        details={
            "from_location_id": str(payload.from_location_id),
            "to_location_id": str(payload.to_location_id),
            "quantity": payload.quantity,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="stock_batch",
        entity_id=destination.id,
        summary=f"Transferred {payload.quantity} {asset.name}",
    )
    await session.commit()
    await session.refresh(destination)
    return source_read, await stock_batch_to_read(session, destination)


async def start_asset_maintenance(
    session: AsyncSession,
    asset: Asset,
    notes: str | None,
    actor: User,
) -> Asset:
    unit = await require_primary_tracked_unit(session, asset)
    if unit.status in (AssetStatus.CHECKED_OUT, AssetStatus.LOST, AssetStatus.RETIRED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tracked unit in status {unit.status.value} cannot enter maintenance.",
        )

    unit.status = AssetStatus.MAINTENANCE
    copy_unit_state_to_asset(asset, unit)
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.MAINTENANCE_STARTED,
        actor=actor,
        notes=notes,
        details={"tracked_unit_id": str(unit.id)},
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="tracked_unit",
        entity_id=unit.id,
        summary=f"Started maintenance for {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def complete_asset_maintenance(
    session: AsyncSession,
    asset: Asset,
    payload: MaintenanceComplete,
    actor: User,
) -> Asset:
    unit = await require_primary_tracked_unit(session, asset)
    if unit.status != AssetStatus.MAINTENANCE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only tracked units in maintenance can complete maintenance.",
        )

    unit.condition = payload.condition
    unit.status = (
        AssetStatus.DAMAGED
        if payload.condition in (AssetCondition.DAMAGED, AssetCondition.NEEDS_REPAIR)
        else AssetStatus.AVAILABLE
    )
    copy_unit_state_to_asset(asset, unit)
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.MAINTENANCE_COMPLETED,
        actor=actor,
        notes=payload.notes,
        details={
            "tracked_unit_id": str(unit.id),
            "condition": payload.condition.value,
            "status": unit.status.value,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="tracked_unit",
        entity_id=unit.id,
        summary=f"Completed maintenance for {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def change_asset_state(
    session: AsyncSession,
    asset: Asset,
    payload: AssetStateChange,
    actor: User,
) -> Asset:
    unit = await require_primary_tracked_unit(session, asset)
    if unit.status == AssetStatus.CHECKED_OUT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checked-out tracked units must be returned before state changes.",
        )
    if unit.status == AssetStatus.RETIRED and payload.status != AssetStatus.RETIRED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retired tracked units cannot be reactivated.",
        )
    if payload.status not in (
        AssetStatus.AVAILABLE,
        AssetStatus.DAMAGED,
        AssetStatus.LOST,
        AssetStatus.RETIRED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State change supports available, damaged, lost, or retired.",
        )

    unit.status = payload.status
    if payload.condition is not None:
        unit.condition = payload.condition
    if payload.status in (AssetStatus.LOST, AssetStatus.RETIRED):
        unit.current_holder_user_id = None
    copy_unit_state_to_asset(asset, unit)
    event_type = asset_state_event_type(payload.status)
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=event_type,
        actor=actor,
        notes=payload.notes,
        details={
            "tracked_unit_id": str(unit.id),
            "status": payload.status.value,
            "condition": unit.condition.value,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="tracked_unit",
        entity_id=unit.id,
        summary=f"Changed tracked unit state for {asset.name} to {unit.status.value}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


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
