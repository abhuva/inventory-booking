from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.qr.schemas import (
    QrAssign,
    QrCodeCreate,
    QrCodeRead,
    QrResolveRead,
    QrScanEventCreate,
    QrScanEventListRead,
    QrScanEventRead,
)
from inventory_booking_api.qr.service import (
    assign_qr_code,
    create_qr_code,
    create_scan_event,
    list_qr_codes,
    list_scan_events,
    resolve_qr_code,
)
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/qr-codes", tags=["qr-codes"])


@router.get("", response_model=list[QrCodeRead])
async def list_qr_code_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[QrCodeRead]:
    return await list_qr_codes(session)


@router.post("", response_model=QrCodeRead)
async def create_qr_code_endpoint(
    payload: QrCodeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QrCodeRead:
    return await create_qr_code(session, payload, current_user)


@router.get("/{token}/resolve", response_model=QrResolveRead)
async def resolve_qr_code_endpoint(
    token: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> QrResolveRead:
    return await resolve_qr_code(session, token)


@router.get("/scan-events", response_model=QrScanEventListRead)
async def list_scan_events_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    after: datetime | None = None,
) -> QrScanEventListRead:
    return await list_scan_events(session, current_user, after)


@router.post("/{token}/scan-events", response_model=QrScanEventRead)
async def create_scan_event_endpoint(
    token: str,
    payload: QrScanEventCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QrScanEventRead:
    return await create_scan_event(session, token, payload, current_user)


@router.post("/{token}/assign", response_model=QrCodeRead)
async def assign_qr_code_endpoint(
    token: str,
    payload: QrAssign,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QrCodeRead:
    return await assign_qr_code(session, token, payload, current_user)
