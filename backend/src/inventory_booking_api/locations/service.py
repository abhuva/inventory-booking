from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.models import ItemEvent
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.baskets.models import BasketLine
from inventory_booking_api.bookings.models import BookingLine
from inventory_booking_api.checkouts.models import CheckoutLine
from inventory_booking_api.inventory.models import Asset, StockBatch, TrackedUnit
from inventory_booking_api.locations.models import Location, LocationImage
from inventory_booking_api.locations.schemas import LocationCreate, LocationUpdate
from inventory_booking_api.returns.models import ReturnLine
from inventory_booking_api.users.models import User


async def list_locations(session: AsyncSession) -> list[Location]:
    result = await session.execute(select(Location).order_by(Location.name))
    return list(result.scalars().all())


async def get_location(session: AsyncSession, location_id: UUID) -> Location | None:
    return await session.get(Location, location_id)


async def create_location(session: AsyncSession, payload: LocationCreate, actor: User) -> Location:
    location = Location(**payload.model_dump())
    session.add(location)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="location",
        entity_id=location.id,
        summary=f"Created location {location.name}",
    )
    await session.commit()
    await session.refresh(location)
    return location


async def update_location(
    session: AsyncSession,
    location: Location,
    payload: LocationUpdate,
    actor: User,
) -> Location:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="location",
        entity_id=location.id,
        summary=f"Updated location {location.name}",
    )
    await session.commit()
    await session.refresh(location)
    return location


async def delete_location(session: AsyncSession, location: Location, actor: User) -> None:
    summary = await location_reference_counts(session, location.id)
    await session.execute(
        update(Asset)
        .where(Asset.home_location_id == location.id)
        .values(home_location_id=None)
    )
    await session.execute(
        update(Asset)
        .where(Asset.current_location_id == location.id)
        .values(current_location_id=None)
    )
    await session.execute(
        update(TrackedUnit)
        .where(TrackedUnit.current_location_id == location.id)
        .values(current_location_id=None)
    )
    await session.execute(
        update(StockBatch).where(StockBatch.location_id == location.id).values(location_id=None)
    )
    for model in (BookingLine, BasketLine, CheckoutLine, ReturnLine):
        await session.execute(
            update(model).where(model.location_id == location.id).values(location_id=None)
        )
    await session.execute(
        update(ItemEvent)
        .where(ItemEvent.from_location_id == location.id)
        .values(from_location_id=None)
    )
    await session.execute(
        update(ItemEvent).where(ItemEvent.to_location_id == location.id).values(to_location_id=None)
    )
    await session.execute(delete(LocationImage).where(LocationImage.location_id == location.id))
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="location",
        entity_id=location.id,
        summary=f"Deleted location {location.name}",
        details=summary,
    )
    await session.delete(location)
    await session.commit()


async def location_reference_counts(session: AsyncSession, location_id: UUID) -> dict[str, int]:
    counts: dict[str, int] = {}
    counts["assets"] = await count_where(
        session,
        select(func.count(Asset.id)).where(
            (Asset.home_location_id == location_id) | (Asset.current_location_id == location_id)
        ),
    )
    counts["tracked_units"] = await count_where(
        session,
        select(func.count(TrackedUnit.id)).where(TrackedUnit.current_location_id == location_id),
    )
    counts["stock_batches"] = await count_where(
        session,
        select(func.count(StockBatch.id)).where(StockBatch.location_id == location_id),
    )
    counts["booking_lines"] = await count_where(
        session,
        select(func.count(BookingLine.id)).where(BookingLine.location_id == location_id),
    )
    counts["basket_lines"] = await count_where(
        session,
        select(func.count(BasketLine.id)).where(BasketLine.location_id == location_id),
    )
    return counts


async def count_where(session: AsyncSession, statement) -> int:
    return int((await session.execute(statement)).scalar_one())
