from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.baskets.schemas import BasketCreate, BasketLineCreate, BasketUpdate
from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import BookingCreate, BookingLineCreate
from inventory_booking_api.bookings.service import create_booking, preview_availability
from inventory_booking_api.persons.models import Person
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User


def basket_expiry() -> datetime:
    """Return the next basket hold expiry timestamp."""

    return datetime.now(UTC) + timedelta(minutes=get_settings().basket_hold_minutes)


async def get_active_basket(session: AsyncSession, actor: User) -> Basket | None:
    """Return the current user's active basket, expiring stale holds first."""

    await expire_stale_baskets(session)
    result = await session.execute(
        select(Basket)
        .where(Basket.user_id == actor.id, Basket.status == BasketStatus.ACTIVE)
        .order_by(Basket.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_basket(session: AsyncSession, basket_id: UUID) -> Basket | None:
    """Return a basket by id."""

    return await session.get(Basket, basket_id)


async def list_basket_lines(session: AsyncSession, basket_id: UUID) -> list[BasketLine]:
    """Return basket lines ordered by creation time."""

    result = await session.execute(
        select(BasketLine)
        .where(BasketLine.basket_id == basket_id)
        .order_by(BasketLine.created_at)
    )
    return list(result.scalars().all())


async def create_or_update_active_basket(
    session: AsyncSession,
    payload: BasketCreate,
    actor: User,
) -> Basket:
    """Create a basket or update the user's current active basket shell."""

    await validate_basket_person(session, payload.person_id)
    basket = await get_active_basket(session, actor)
    if basket is None:
        basket = Basket(
            user_id=actor.id,
            person_id=payload.person_id,
            title=payload.title,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            notes=payload.notes,
            expires_at=basket_expiry(),
            status=BasketStatus.ACTIVE,
        )
        session.add(basket)
    else:
        basket.person_id = payload.person_id
        basket.title = payload.title
        basket.starts_at = payload.starts_at
        basket.ends_at = payload.ends_at
        basket.notes = payload.notes
        basket.expires_at = basket_expiry()
        await validate_basket_lines(session, basket)
    await session.commit()
    await session.refresh(basket)
    return basket


async def update_basket(
    session: AsyncSession,
    basket: Basket,
    payload: BasketUpdate,
    actor: User,
) -> Basket:
    """Update editable active basket metadata and revalidate its holds."""

    ensure_basket_owner(basket, actor)
    ensure_active_basket(basket)
    if payload.person_id is not None:
        await validate_basket_person(session, payload.person_id)
        basket.person_id = payload.person_id
    if payload.title is not None:
        basket.title = payload.title
    if payload.starts_at is not None:
        basket.starts_at = payload.starts_at
    if payload.ends_at is not None:
        basket.ends_at = payload.ends_at
    if basket.starts_at >= basket.ends_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Basket starts_at must be before ends_at.",
        )
    basket.notes = payload.notes
    basket.expires_at = basket_expiry()
    await validate_basket_lines(session, basket)
    await session.commit()
    await session.refresh(basket)
    return basket


async def add_or_update_basket_line(
    session: AsyncSession,
    basket: Basket,
    payload: BasketLineCreate,
    actor: User,
) -> BasketLine:
    """Add a line to an active basket or replace the same asset/location line."""

    ensure_basket_owner(basket, actor)
    ensure_active_basket(basket)
    existing = await find_basket_line(session, basket.id, payload.asset_id, payload.location_id)
    if existing is None:
        line = BasketLine(basket_id=basket.id, **payload.model_dump())
        session.add(line)
    else:
        line = existing
        line.quantity = payload.quantity
        line.notes = payload.notes

    basket.expires_at = basket_expiry()
    await session.flush()
    await validate_basket_lines(session, basket)
    await session.commit()
    await session.refresh(line)
    return line


async def remove_basket_line(
    session: AsyncSession,
    basket: Basket,
    line_id: UUID,
    actor: User,
) -> Basket:
    """Remove one line from an active basket."""

    ensure_basket_owner(basket, actor)
    ensure_active_basket(basket)
    line = await session.get(BasketLine, line_id)
    if line is None or line.basket_id != basket.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Basket line not found.")
    await session.delete(line)
    basket.expires_at = basket_expiry()
    await session.commit()
    await session.refresh(basket)
    return basket


async def cancel_basket(session: AsyncSession, basket: Basket, actor: User) -> Basket:
    """Cancel an active basket and release its holds."""

    ensure_basket_owner(basket, actor)
    ensure_active_basket(basket)
    basket.status = BasketStatus.CANCELLED
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="basket",
        entity_id=basket.id,
        summary=f"Cancelled basket {basket.title}",
    )
    await session.commit()
    await session.refresh(basket)
    return basket


async def confirm_basket(
    session: AsyncSession,
    basket: Basket,
    actor: User,
) -> tuple[Basket, Booking, list[BookingLine]]:
    """Convert an active basket into a confirmed booking."""

    ensure_basket_owner(basket, actor)
    ensure_active_basket(basket)
    lines = await list_basket_lines(session, basket.id)
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Basket must contain at least one item before confirmation.",
        )
    if basket.person_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a person before confirming the basket.",
        )

    booking_payload = basket_to_booking_payload(basket, lines)
    booking, booking_lines = await create_booking(
        session,
        booking_payload,
        actor,
        excluded_basket_id=basket.id,
        commit=False,
    )
    basket.status = BasketStatus.CONFIRMED
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="basket",
        entity_id=basket.id,
        summary=f"Confirmed basket {basket.title}",
    )
    await session.commit()
    await session.refresh(basket)
    await session.refresh(booking)
    for line in booking_lines:
        await session.refresh(line)
    return basket, booking, booking_lines


async def validate_basket_person(session: AsyncSession, person_id: UUID | None) -> None:
    """Reject a basket person reference that does not exist."""

    if person_id is None:
        return
    person = await session.get(Person, person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person does not exist.",
        )


async def validate_basket_lines(session: AsyncSession, basket: Basket) -> None:
    """Validate current basket lines against confirmed bookings and other baskets."""

    lines = await list_basket_lines(session, basket.id)
    if not lines:
        return
    availability = await preview_availability(
        session,
        basket_to_booking_payload(basket, lines),
        excluded_basket_id=basket.id,
    )
    if not availability.available:
        first_conflict = next((line for line in availability.lines if not line.available), None)
        detail = (
            first_conflict.reason if first_conflict else "Basket has availability conflicts."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


async def expire_stale_baskets(session: AsyncSession) -> None:
    """Mark expired active baskets so their holds no longer count."""

    result = await session.execute(
        select(Basket).where(
            Basket.status == BasketStatus.ACTIVE,
            Basket.expires_at <= datetime.now(UTC),
        )
    )
    stale_baskets = list(result.scalars().all())
    if not stale_baskets:
        return
    for basket in stale_baskets:
        basket.status = BasketStatus.EXPIRED
    await session.commit()


async def find_basket_line(
    session: AsyncSession,
    basket_id: UUID,
    asset_id: UUID,
    location_id: UUID | None,
) -> BasketLine | None:
    """Return an existing line for the same basket/asset/location scope."""

    result = await session.execute(
        select(BasketLine).where(
            BasketLine.basket_id == basket_id,
            BasketLine.asset_id == asset_id,
            BasketLine.location_id == location_id,
        )
    )
    return result.scalar_one_or_none()


def basket_to_booking_payload(basket: Basket, lines: list[BasketLine]) -> BookingCreate:
    """Build a booking payload from basket state."""

    return BookingCreate(
        title=basket.title,
        person_id=basket.person_id,
        starts_at=basket.starts_at,
        ends_at=basket.ends_at,
        notes=basket.notes,
        lines=[
            BookingLineCreate(
                asset_id=line.asset_id,
                location_id=line.location_id,
                quantity=line.quantity,
                notes=line.notes,
            )
            for line in lines
        ],
    )


def ensure_basket_owner(basket: Basket, actor: User) -> None:
    """Reject access to another user's basket."""

    if basket.user_id != actor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Basket not found.")


def ensure_active_basket(basket: Basket) -> None:
    """Reject edits to non-active or expired baskets."""

    if basket.status != BasketStatus.ACTIVE or is_expired(basket.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Basket is not active anymore.",
        )


def is_expired(expires_at: datetime) -> bool:
    """Return whether an expiry timestamp is stale, tolerating SQLite naive datetimes."""

    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    return expires_at <= now
