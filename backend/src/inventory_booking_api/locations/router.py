from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import require_internal_api_token
from inventory_booking_api.locations.schemas import LocationCreate, LocationRead, LocationUpdate
from inventory_booking_api.locations.service import (
    create_location,
    get_location,
    list_locations,
    update_location,
)

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_location_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LocationRead]:
    return await list_locations(session)


@router.post("", response_model=LocationRead, dependencies=[Depends(require_internal_api_token)])
async def create_location_endpoint(
    payload: LocationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    return await create_location(session, payload)


@router.get("/{location_id}", response_model=LocationRead)
async def get_location_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    return location


@router.patch(
    "/{location_id}",
    response_model=LocationRead,
    dependencies=[Depends(require_internal_api_token)],
)
async def update_location_endpoint(
    location_id: UUID,
    payload: LocationUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    return await update_location(session, location, payload)
