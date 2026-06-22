from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.checkouts.enums import CheckoutStatus
from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.checkouts.schemas import CheckoutCreate
from inventory_booking_api.inventory.enums import AssetStatus, AssetType
from inventory_booking_api.inventory.models import Asset, StockLevel
from inventory_booking_api.users.models import User


async def list_checkouts(session: AsyncSession) -> list[Checkout]:
    result = await session.execute(select(Checkout).order_by(Checkout.created_at.desc()))
    return list(result.scalars().all())


async def get_checkout(session: AsyncSession, checkout_id: UUID) -> Checkout | None:
    return await session.get(Checkout, checkout_id)


async def list_checkout_lines(session: AsyncSession, checkout_id: UUID) -> list[CheckoutLine]:
    result = await session.execute(
        select(CheckoutLine)
        .where(CheckoutLine.checkout_id == checkout_id)
        .order_by(CheckoutLine.created_at)
    )
    return list(result.scalars().all())


async def create_checkout(
    session: AsyncSession,
    payload: CheckoutCreate,
    actor: User,
) -> tuple[Checkout, list[CheckoutLine]]:
    booking = await session.get(Booking, payload.booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking does not exist.",
        )
    if booking.status != BookingStatus.RESERVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only reserved bookings can be checked out.",
        )

    existing_checkout = await get_checkout_by_booking(session, booking.id)
    if existing_checkout is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking already has a checkout.",
        )

    booking_lines = await get_booking_lines(session, booking.id)
    if not booking_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking has no lines to check out.",
        )

    checkout = Checkout(
        booking_id=booking.id,
        checked_out_by_user_id=actor.id,
        checked_out_to_user_id=payload.checked_out_to_user_id,
        status=CheckoutStatus.CHECKED_OUT,
        notes=payload.notes,
    )
    session.add(checkout)
    await session.flush()

    checkout_lines: list[CheckoutLine] = []
    for booking_line in booking_lines:
        asset = await session.get(Asset, booking_line.asset_id)
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking references a missing asset.",
            )
        checkout_line = await checkout_booking_line(
            session,
            checkout,
            booking_line,
            asset,
            payload,
            actor,
        )
        checkout_lines.append(checkout_line)

    booking.status = BookingStatus.CHECKED_OUT
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="checkout",
        entity_id=checkout.id,
        summary=f"Checked out booking {booking.title}",
    )
    await session.commit()
    await session.refresh(checkout)
    for line in checkout_lines:
        await session.refresh(line)
    return checkout, checkout_lines


async def checkout_booking_line(
    session: AsyncSession,
    checkout: Checkout,
    booking_line: BookingLine,
    asset: Asset,
    payload: CheckoutCreate,
    actor: User,
) -> CheckoutLine:
    if asset.asset_type == AssetType.TRACKED:
        if asset.status != AssetStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tracked asset {asset.name} is not available for checkout.",
            )
        asset.status = AssetStatus.CHECKED_OUT
        asset.condition = payload.condition_out
        asset.current_holder_user_id = payload.checked_out_to_user_id
    else:
        await increment_stock_checkout(session, booking_line)

    checkout_line = CheckoutLine(
        checkout_id=checkout.id,
        asset_id=booking_line.asset_id,
        location_id=booking_line.location_id,
        quantity=booking_line.quantity,
        condition_out=payload.condition_out,
        notes=booking_line.notes,
    )
    session.add(checkout_line)
    await write_item_event(
        session,
        asset_id=booking_line.asset_id,
        event_type=ItemEventType.CHECKED_OUT,
        actor=actor,
        notes="Checked out from booking",
        details={
            "checkout_id": str(checkout.id),
            "booking_id": str(checkout.booking_id),
            "location_id": str(booking_line.location_id) if booking_line.location_id else None,
            "quantity": booking_line.quantity,
        },
    )
    return checkout_line


async def increment_stock_checkout(session: AsyncSession, booking_line: BookingLine) -> None:
    if booking_line.location_id is None or booking_line.quantity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock checkout lines require a location and quantity.",
        )

    stock_level = await get_stock_level(session, booking_line.asset_id, booking_line.location_id)
    if stock_level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stock level exists for this asset/location.",
        )
    if stock_level.quantity_total - stock_level.quantity_checked_out < booking_line.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Not enough stock is available for checkout.",
        )
    stock_level.quantity_checked_out += booking_line.quantity


async def get_checkout_by_booking(session: AsyncSession, booking_id: UUID) -> Checkout | None:
    result = await session.execute(select(Checkout).where(Checkout.booking_id == booking_id))
    return result.scalar_one_or_none()


async def get_booking_lines(session: AsyncSession, booking_id: UUID) -> list[BookingLine]:
    result = await session.execute(select(BookingLine).where(BookingLine.booking_id == booking_id))
    return list(result.scalars().all())


async def get_stock_level(
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
