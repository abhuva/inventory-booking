from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from inventory_booking_api.audit.enums import AuditAction, ItemEventType


class AuditLogRead(BaseModel):
    id: UUID
    created_at: datetime
    actor_user_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: UUID | None
    summary: str
    details: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


class ItemEventRead(BaseModel):
    id: UUID
    created_at: datetime
    asset_id: UUID
    event_type: ItemEventType
    actor_user_id: UUID | None
    from_location_id: UUID | None
    to_location_id: UUID | None
    notes: str | None
    details: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)
