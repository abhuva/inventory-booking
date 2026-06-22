from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.inventory.asset_schemas import (
    AssetCreate,
    AssetUpdate,
    StockLevelCreate,
    StockLevelUpdate,
    StockTransfer,
    TrackedAssetTransfer,
)
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockLevel
from inventory_booking_api.users.models import User


async def list_assets(session: AsyncSession) -> list[Asset]:
    result = await session.execute(select(Asset).order_by(Asset.name))
    return list(result.scalars().all())


async def get_asset(session: AsyncSession, asset_id: UUID) -> Asset | None:
    return await session.get(Asset, asset_id)


async def create_asset(session: AsyncSession, payload: AssetCreate, actor: User) -> Asset:
    asset = Asset(**payload.model_dump())
    session.add(asset)
    await session.flush()
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
        entity_type="asset",
        entity_id=asset.id,
        summary=f"Created asset {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    return asset


async def update_asset(
    session: AsyncSession,
    asset: Asset,
    payload: AssetUpdate,
    actor: User,
) -> Asset:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
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
        entity_type="asset",
        entity_id=asset.id,
        summary=f"Updated asset {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    return asset


async def list_stock_levels(session: AsyncSession) -> list[StockLevel]:
    result = await session.execute(select(StockLevel).order_by(StockLevel.location_id))
    return list(result.scalars().all())


async def get_stock_level(session: AsyncSession, stock_level_id: UUID) -> StockLevel | None:
    return await session.get(StockLevel, stock_level_id)


async def create_stock_level(
    session: AsyncSession,
    payload: StockLevelCreate,
    actor: User,
) -> StockLevel:
    asset = await session.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset does not exist.")
    if asset.asset_type != AssetType.STOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock levels can only be created for stock assets.",
        )
    stock_level = StockLevel(**payload.model_dump())
    session.add(stock_level)
    await session.flush()
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Created stock level",
        details={
            "stock_level_id": str(stock_level.id),
            "location_id": str(stock_level.location_id),
            "quantity_total": stock_level.quantity_total,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="stock_level",
        entity_id=stock_level.id,
        summary=f"Created stock level for {asset.name}",
    )
    await session.commit()
    await session.refresh(stock_level)
    return stock_level


async def update_stock_level(
    session: AsyncSession,
    stock_level: StockLevel,
    payload: StockLevelUpdate,
    actor: User,
) -> StockLevel:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(stock_level, field, value)
    await write_item_event(
        session,
        asset_id=stock_level.asset_id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Updated stock level",
        details={
            "stock_level_id": str(stock_level.id),
            "location_id": str(stock_level.location_id),
            "quantity_total": stock_level.quantity_total,
            "quantity_reserved": stock_level.quantity_reserved,
            "quantity_checked_out": stock_level.quantity_checked_out,
        },
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="stock_level",
        entity_id=stock_level.id,
        summary="Updated stock level",
    )
    await session.commit()
    await session.refresh(stock_level)
    return stock_level


async def transfer_tracked_asset(
    session: AsyncSession,
    asset: Asset,
    payload: TrackedAssetTransfer,
    actor: User,
) -> Asset:
    if asset.asset_type != AssetType.TRACKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only tracked assets can use tracked transfer.",
        )
    if asset.status in (AssetStatus.CHECKED_OUT, AssetStatus.LOST, AssetStatus.RETIRED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset in status {asset.status.value} cannot be transferred.",
        )

    from_location_id = asset.current_location_id
    asset.current_location_id = payload.to_location_id
    asset.current_holder_user_id = payload.to_holder_user_id
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.MOVED,
        actor=actor,
        notes=payload.notes,
        details={
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
        entity_id=asset.id,
        summary=f"Transferred asset {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    return asset


async def transfer_stock(
    session: AsyncSession,
    payload: StockTransfer,
    actor: User,
) -> tuple[StockLevel, StockLevel]:
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
            detail="Only stock assets can use stock transfer.",
        )

    source = await get_stock_level_by_asset_location(
        session, payload.asset_id, payload.from_location_id
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source stock level does not exist.",
        )
    available_quantity = source.quantity_total - source.quantity_checked_out
    if available_quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough available stock to transfer.",
        )

    destination = await get_stock_level_by_asset_location(
        session, payload.asset_id, payload.to_location_id
    )
    if destination is None:
        destination = StockLevel(
            asset_id=payload.asset_id,
            location_id=payload.to_location_id,
            quantity_total=0,
        )
        session.add(destination)
        await session.flush()

    source.quantity_total -= payload.quantity
    destination.quantity_total += payload.quantity
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
        entity_type="stock_level",
        entity_id=source.id,
        summary=f"Transferred {payload.quantity} {asset.name}",
    )
    await session.commit()
    await session.refresh(source)
    await session.refresh(destination)
    return source, destination


async def get_stock_level_by_asset_location(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID,
) -> StockLevel | None:
    result = await session.execute(
        select(StockLevel).where(
            StockLevel.asset_id == asset_id,
            StockLevel.location_id == location_id,
        )
    )
    return result.scalar_one_or_none()
