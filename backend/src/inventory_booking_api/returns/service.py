from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking
from inventory_booking_api.checkouts.enums import CheckoutStatus
from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.core.locks import (
    acquire_advisory_locks,
    asset_lock_key,
    checkout_lock_key,
)
from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.returns.models import Return, ReturnLine
from inventory_booking_api.returns.schemas import ReturnCreate, ReturnLineCreate
from inventory_booking_api.users.models import User


async def list_returns(session: AsyncSession) -> list[Return]:
    result = await session.execute(select(Return).order_by(Return.created_at.desc()))
    return list(result.scalars().all())


async def get_return(session: AsyncSession, return_id: UUID) -> Return | None:
    return await session.get(Return, return_id)


async def list_return_lines(session: AsyncSession, return_id: UUID) -> list[ReturnLine]:
    result = await session.execute(
        select(ReturnLine).where(ReturnLine.return_id == return_id).order_by(ReturnLine.created_at)
    )
    return list(result.scalars().all())


async def get_checkout_lines(session: AsyncSession, checkout_id: UUID) -> list[CheckoutLine]:
    result = await session.execute(
        select(CheckoutLine).where(CheckoutLine.checkout_id == checkout_id)
    )
    return list(result.scalars().all())


async def create_return(
    session: AsyncSession,
    payload: ReturnCreate,
    actor: User,
) -> tuple[Return, list[ReturnLine]]:
    checkout = await session.get(Checkout, payload.checkout_id)
    if checkout is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout does not exist.",
        )
    if checkout.status == CheckoutStatus.RETURNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout is already fully returned.",
        )
    checkout_lines = await get_checkout_lines(session, checkout.id)
    await acquire_advisory_locks(
        session,
        [
            checkout_lock_key(checkout.id),
            *(asset_lock_key(line.asset_id) for line in checkout_lines),
        ],
    )

    seen_lines: set[UUID] = set()
    return_record = Return(
        checkout_id=checkout.id,
        returned_by_user_id=actor.id,
        notes=payload.notes,
    )
    session.add(return_record)
    await session.flush()

    return_lines: list[ReturnLine] = []
    for line_payload in payload.lines:
        if line_payload.checkout_line_id in seen_lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate return line for the same checkout line.",
            )
        seen_lines.add(line_payload.checkout_line_id)
        return_line = await return_checkout_line(
            session,
            return_record,
            checkout,
            line_payload,
            actor,
        )
        return_lines.append(return_line)

    checkout.status = await resolve_checkout_status(session, checkout.id)
    booking = await session.get(Booking, checkout.booking_id)
    if booking is not None and checkout.status == CheckoutStatus.RETURNED:
        booking.status = BookingStatus.COMPLETED

    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="return",
        entity_id=return_record.id,
        summary="Returned checkout lines",
    )
    await session.commit()
    await session.refresh(return_record)
    for line in return_lines:
        await session.refresh(line)
    return return_record, return_lines


async def return_checkout_line(
    session: AsyncSession,
    return_record: Return,
    checkout: Checkout,
    line_payload: ReturnLineCreate,
    actor: User,
) -> ReturnLine:
    checkout_line = await session.get(CheckoutLine, line_payload.checkout_line_id)
    if checkout_line is None or checkout_line.checkout_id != checkout.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout line does not belong to this checkout.",
        )

    asset = await session.get(Asset, checkout_line.asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout line references a missing asset.",
        )

    quantity = resolve_return_quantity(checkout_line, line_payload.quantity, asset)
    if quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return quantity is required.",
        )
    remaining = line_remaining_quantity(checkout_line, asset)
    if quantity > remaining:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Return quantity exceeds checked-out quantity.",
        )

    if asset.asset_type == AssetType.TRACKED:
        await apply_tracked_unit_return(session, asset, line_payload.condition_in)
        checkout_line.quantity_returned = 1
    else:
        await apply_stock_return(session, checkout_line, quantity)

    return_line = ReturnLine(
        return_id=return_record.id,
        checkout_line_id=checkout_line.id,
        asset_id=checkout_line.asset_id,
        location_id=checkout_line.location_id,
        quantity=None if asset.asset_type == AssetType.TRACKED else quantity,
        condition_in=line_payload.condition_in,
        notes=line_payload.notes,
    )
    session.add(return_line)
    await write_item_event(
        session,
        asset_id=checkout_line.asset_id,
        event_type=ItemEventType.RETURNED,
        actor=actor,
        notes="Returned checkout line",
        details={
            "return_id": str(return_record.id),
            "checkout_id": str(checkout.id),
            "checkout_line_id": str(checkout_line.id),
            "quantity": quantity,
            "condition_in": line_payload.condition_in.value,
        },
    )
    return return_line


def resolve_return_quantity(
    checkout_line: CheckoutLine,
    requested_quantity: int | None,
    asset: Asset,
) -> int | None:
    if asset.asset_type == AssetType.TRACKED:
        if requested_quantity not in (None, 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tracked returns must not request a quantity above 1.",
            )
        return 1
    if requested_quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock returns require a quantity.",
        )
    return requested_quantity


def line_remaining_quantity(checkout_line: CheckoutLine, asset: Asset) -> int:
    checked_out_quantity = 1 if asset.asset_type == AssetType.TRACKED else checkout_line.quantity
    if checked_out_quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Checkout line has no checked-out quantity.",
        )
    return checked_out_quantity - checkout_line.quantity_returned


async def apply_tracked_unit_return(
    session: AsyncSession,
    asset: Asset,
    condition_in: AssetCondition,
) -> None:
    unit = await get_primary_tracked_unit(session, asset.id)
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracked unit missing.",
        )
    unit.condition = condition_in
    unit.current_holder_user_id = None
    if condition_in in (AssetCondition.DAMAGED, AssetCondition.NEEDS_REPAIR):
        unit.status = AssetStatus.DAMAGED
    else:
        unit.status = AssetStatus.AVAILABLE


async def apply_stock_return(
    session: AsyncSession,
    checkout_line: CheckoutLine,
    quantity: int,
) -> None:
    checked_out_batch = await get_checked_out_stock_batch(session, checkout_line.id)
    if checked_out_batch is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No checked-out stock batch exists for this checkout line.",
        )
    if checked_out_batch.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Return quantity exceeds checked-out batch quantity.",
        )
    batch_condition = checked_out_batch.condition
    if checked_out_batch.quantity == quantity:
        await session.delete(checked_out_batch)
    else:
        checked_out_batch.quantity -= quantity
    available_batch = await get_available_stock_batch(
        session,
        checkout_line.asset_id,
        checkout_line.location_id,
        batch_condition,
    )
    if available_batch is None:
        available_batch = StockBatch(
            asset_id=checkout_line.asset_id,
            location_id=checkout_line.location_id,
            holder_user_id=None,
            checkout_line_id=None,
            status=AssetStatus.AVAILABLE,
            condition=batch_condition,
            quantity=quantity,
        )
        session.add(available_batch)
    else:
        available_batch.quantity += quantity
    checkout_line.quantity_returned += quantity


async def resolve_checkout_status(session: AsyncSession, checkout_id: UUID) -> CheckoutStatus:
    result = await session.execute(
        select(CheckoutLine).where(CheckoutLine.checkout_id == checkout_id)
    )
    lines = list(result.scalars().all())
    all_returned = True
    any_returned = False
    for line in lines:
        target_quantity = 1 if line.quantity is None else line.quantity
        if line.quantity_returned > 0:
            any_returned = True
        if line.quantity_returned < target_quantity:
            all_returned = False
    if all_returned:
        return CheckoutStatus.RETURNED
    if any_returned:
        return CheckoutStatus.PARTIALLY_RETURNED
    return CheckoutStatus.CHECKED_OUT


async def get_checked_out_stock_batch(
    session: AsyncSession,
    checkout_line_id: UUID,
) -> StockBatch | None:
    result = await session.execute(
        select(StockBatch).where(
            StockBatch.checkout_line_id == checkout_line_id,
            StockBatch.status == AssetStatus.CHECKED_OUT,
        )
    )
    return result.scalar_one_or_none()


async def get_available_stock_batch(
    session: AsyncSession,
    asset_id: UUID,
    location_id: UUID | None,
    condition: AssetCondition,
) -> StockBatch | None:
    result = await session.execute(
        select(StockBatch).where(
            StockBatch.asset_id == asset_id,
            StockBatch.location_id == location_id,
            StockBatch.holder_user_id.is_(None),
            StockBatch.status == AssetStatus.AVAILABLE,
            StockBatch.condition == condition,
        )
    )
    return result.scalar_one_or_none()


async def get_primary_tracked_unit(session: AsyncSession, asset_id: UUID) -> TrackedUnit | None:
    result = await session.execute(
        select(TrackedUnit).where(TrackedUnit.asset_id == asset_id).order_by(TrackedUnit.created_at)
    )
    return result.scalars().first()
