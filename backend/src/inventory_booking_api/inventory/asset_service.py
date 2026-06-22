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
)
from inventory_booking_api.inventory.enums import AssetType
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
