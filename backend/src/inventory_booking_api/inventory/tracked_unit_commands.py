from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audited_item_event
from inventory_booking_api.inventory.asset_schemas import AssetStateChange, MaintenanceComplete
from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus
from inventory_booking_api.inventory.models import Asset
from inventory_booking_api.inventory.state import (
    apply_primary_unit_state,
    asset_state_event_type,
    copy_unit_state_to_asset,
    require_primary_tracked_unit,
)
from inventory_booking_api.users.models import User


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
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.MAINTENANCE_STARTED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="tracked_unit",
        audit_entity_id=unit.id,
        audit_summary=f"Started maintenance for {asset.name}",
        item_notes=notes,
        item_details={"tracked_unit_id": str(unit.id)},
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
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.MAINTENANCE_COMPLETED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="tracked_unit",
        audit_entity_id=unit.id,
        audit_summary=f"Completed maintenance for {asset.name}",
        item_notes=payload.notes,
        item_details={
            "tracked_unit_id": str(unit.id),
            "condition": payload.condition.value,
            "status": unit.status.value,
        },
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
    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=event_type,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="tracked_unit",
        audit_entity_id=unit.id,
        audit_summary=f"Changed tracked unit state for {asset.name} to {unit.status.value}",
        item_notes=payload.notes,
        item_details={
            "tracked_unit_id": str(unit.id),
            "status": payload.status.value,
            "condition": unit.condition.value,
        },
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset
