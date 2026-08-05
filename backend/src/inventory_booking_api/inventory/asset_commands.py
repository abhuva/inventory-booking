from fastapi import HTTPException, status
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.models import ItemEvent
from inventory_booking_api.audit.service import write_audit_log, write_audited_item_event
from inventory_booking_api.baskets.models import BasketLine
from inventory_booking_api.inventory.asset_schemas import AssetCreate, AssetUpdate
from inventory_booking_api.inventory.enums import AssetType
from inventory_booking_api.inventory.fields import DEFINITION_FIELDS, TRACKED_UNIT_FIELDS
from inventory_booking_api.inventory.models import Asset, AssetImage, StockBatch, TrackedUnit
from inventory_booking_api.inventory.queries import asset_reference_counts
from inventory_booking_api.inventory.state import (
    apply_primary_unit_state,
    copy_unit_state_to_asset,
    get_primary_tracked_unit,
)
from inventory_booking_api.qr.models import QrCode
from inventory_booking_api.users.models import User


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

    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.CREATED,
        audit_action=AuditAction.CREATE,
        audit_entity_type="asset_definition",
        audit_entity_id=asset.id,
        audit_summary=f"Created asset definition {asset.name}",
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

    await write_audited_item_event(
        session,
        actor=actor,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        audit_action=AuditAction.UPDATE,
        audit_entity_type="asset_definition",
        audit_entity_id=asset.id,
        audit_summary=f"Updated asset definition {asset.name}",
    )
    await session.commit()
    await session.refresh(asset)
    await apply_primary_unit_state(session, asset)
    return asset


async def delete_asset(session: AsyncSession, asset: Asset, actor: User) -> None:
    counts = await asset_reference_counts(session, asset.id)
    blocking = {
        key: value
        for key, value in counts.items()
        if key in ("booking_lines", "checkout_lines", "return_lines") and value > 0
    }
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Asset has historical references and cannot be deleted.",
                "references": counts,
            },
        )
    await session.execute(delete(BasketLine).where(BasketLine.asset_id == asset.id))
    await session.execute(update(QrCode).where(QrCode.asset_id == asset.id).values(asset_id=None))
    await session.execute(delete(AssetImage).where(AssetImage.asset_id == asset.id))
    await session.execute(delete(StockBatch).where(StockBatch.asset_id == asset.id))
    await session.execute(delete(TrackedUnit).where(TrackedUnit.asset_id == asset.id))
    await session.execute(delete(ItemEvent).where(ItemEvent.asset_id == asset.id))
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="asset_definition",
        entity_id=asset.id,
        summary=f"Deleted asset definition {asset.name}",
        details=counts,
    )
    await session.delete(asset)
    await session.commit()


