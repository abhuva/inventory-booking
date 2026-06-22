from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.locations.models import Location
from inventory_booking_api.locations.schemas import LocationCreate, LocationUpdate


async def list_locations(session: AsyncSession) -> list[Location]:
    result = await session.execute(select(Location).order_by(Location.name))
    return list(result.scalars().all())


async def get_location(session: AsyncSession, location_id: UUID) -> Location | None:
    return await session.get(Location, location_id)


async def create_location(session: AsyncSession, payload: LocationCreate) -> Location:
    location = Location(**payload.model_dump())
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location


async def update_location(
    session: AsyncSession,
    location: Location,
    payload: LocationUpdate,
) -> Location:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await session.commit()
    await session.refresh(location)
    return location
