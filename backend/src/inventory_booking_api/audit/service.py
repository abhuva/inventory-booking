from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.models import AuditLog, ItemEvent
from inventory_booking_api.users.models import User


async def write_audit_log(
    session: AsyncSession,
    *,
    actor: User | None,
    action: AuditAction,
    entity_type: str,
    entity_id: UUID | None,
    summary: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit log entry in the current transaction."""

    audit_log = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        details=details,
    )
    session.add(audit_log)
    return audit_log


async def write_item_event(
    session: AsyncSession,
    *,
    asset_id: UUID,
    event_type: ItemEventType,
    actor: User | None,
    notes: str | None = None,
    details: dict[str, Any] | None = None,
) -> ItemEvent:
    """Stage an item event in the current transaction."""

    item_event = ItemEvent(
        asset_id=asset_id,
        event_type=event_type,
        actor_user_id=actor.id if actor else None,
        notes=notes,
        details=details,
    )
    session.add(item_event)
    return item_event
