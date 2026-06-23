from secrets import token_urlsafe
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, TrackedUnit
from inventory_booking_api.qr.models import QrCode
from inventory_booking_api.qr.schemas import QrAssign, QrCodeCreate, QrResolvedAsset, QrResolveRead
from inventory_booking_api.users.models import User


async def list_qr_codes(session: AsyncSession) -> list[QrCode]:
    result = await session.execute(select(QrCode).order_by(QrCode.created_at.desc()))
    return list(result.scalars().all())


async def create_qr_code(session: AsyncSession, payload: QrCodeCreate, actor: User) -> QrCode:
    qr_code = QrCode(token=await generate_unique_token(session), **payload.model_dump())
    session.add(qr_code)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="qr_code",
        entity_id=qr_code.id,
        summary="Created QR label",
    )
    await session.commit()
    await session.refresh(qr_code)
    return qr_code


async def assign_qr_code(
    session: AsyncSession,
    token: str,
    payload: QrAssign,
    actor: User,
) -> QrCode:
    qr_code = await get_qr_code_by_token(session, token)
    if qr_code is None:
        raise_not_found_qr()
    asset = await session.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset does not exist.")
    if asset.asset_type != AssetType.TRACKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR labels can only be assigned to tracked assets.",
        )
    unit = await get_primary_tracked_unit(session, asset.id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracked asset has no physical unit.",
        )
    if unit.status in (AssetStatus.RETIRED, AssetStatus.LOST):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset in status {unit.status.value} cannot receive a QR label.",
        )
    existing_assignment = await get_qr_code_by_asset(session, asset.id)
    if existing_assignment is not None and existing_assignment.id != qr_code.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset already has a QR label.",
        )

    qr_code.asset_id = asset.id
    if payload.notes is not None:
        qr_code.notes = payload.notes
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.QR_ASSIGNED,
        actor=actor,
        notes=payload.notes,
        details={"qr_token": token},
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="qr_code",
        entity_id=qr_code.id,
        summary=f"Assigned QR label to {asset.name}",
    )
    await session.commit()
    await session.refresh(qr_code)
    return qr_code


async def resolve_qr_code(session: AsyncSession, token: str) -> QrResolveRead:
    qr_code = await get_qr_code_by_token(session, token)
    if qr_code is None:
        raise_not_found_qr()
    if qr_code.asset_id is None:
        return QrResolveRead(token=qr_code.token, assigned=False, asset=None)

    asset = await session.get(Asset, qr_code.asset_id)
    if asset is None:
        return QrResolveRead(token=qr_code.token, assigned=False, asset=None)
    unit = await get_primary_tracked_unit(session, asset.id)
    if unit is not None:
        asset.status = unit.status
        asset.condition = unit.condition
        asset.current_location_id = unit.current_location_id
        asset.current_holder_user_id = unit.current_holder_user_id
    return QrResolveRead(
        token=qr_code.token,
        assigned=True,
        asset=QrResolvedAsset.model_validate(asset),
    )


async def generate_unique_token(session: AsyncSession) -> str:
    for _ in range(5):
        candidate = token_urlsafe(24)
        if await get_qr_code_by_token(session, candidate) is None:
            return candidate
    raise RuntimeError("Unable to generate unique QR token.")


async def get_qr_code_by_token(session: AsyncSession, token: str) -> QrCode | None:
    result = await session.execute(select(QrCode).where(QrCode.token == token))
    return result.scalar_one_or_none()


async def get_qr_code_by_asset(session: AsyncSession, asset_id: UUID) -> QrCode | None:
    result = await session.execute(select(QrCode).where(QrCode.asset_id == asset_id))
    return result.scalar_one_or_none()


async def get_primary_tracked_unit(session: AsyncSession, asset_id: UUID) -> TrackedUnit | None:
    result = await session.execute(
        select(TrackedUnit).where(TrackedUnit.asset_id == asset_id).order_by(TrackedUnit.created_at)
    )
    return result.scalars().first()


def raise_not_found_qr() -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR label not found.")
