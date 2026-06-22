from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.schemas import AuditLogRead, ItemEventRead
from inventory_booking_api.audit.service import list_audit_logs, list_item_events
from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import require_admin
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_log_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditLogRead]:
    return await list_audit_logs(session, limit)


@router.get("/item-events", response_model=list[ItemEventRead])
async def list_item_event_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_admin)],
    asset_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ItemEventRead]:
    return await list_item_events(session, asset_id=asset_id, limit=limit)
