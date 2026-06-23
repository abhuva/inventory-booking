from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.bookings.models import Booking, BookingLine
from inventory_booking_api.bookings.schemas import (
    AvailabilityDaysRead,
    AvailabilityHeatmapRead,
    AvailabilityRead,
    BookingCreate,
    BookingLineRead,
    BookingRead,
    BookingSummaryRead,
)
from inventory_booking_api.bookings.service import (
    build_asset_availability_days,
    build_stock_availability_heatmap,
    cancel_booking,
    create_booking,
    get_booking,
    list_booking_lines,
    list_bookings,
    preview_availability,
)
from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingSummaryRead])
async def list_booking_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[BookingSummaryRead]:
    return await list_bookings(session)


@router.post("", response_model=BookingRead)
async def create_booking_endpoint(
    payload: BookingCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookingRead:
    booking, lines = await create_booking(session, payload, current_user)
    return build_booking_read(booking, lines)


@router.post("/availability", response_model=AvailabilityRead)
async def preview_availability_endpoint(
    payload: BookingCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)],
) -> AvailabilityRead:
    return await preview_availability(session, payload)


@router.get("/availability/heatmap", response_model=AvailabilityHeatmapRead)
async def availability_heatmap_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(get_current_user)],
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
    bucket: Annotated[str, Query(pattern="^(day|week)$")] = "day",
    location_id: Annotated[UUID | None, Query()] = None,
) -> AvailabilityHeatmapRead:
    return await build_stock_availability_heatmap(
        session,
        starts_at=starts_at,
        ends_at=ends_at,
        bucket=bucket,
        location_id=location_id,
    )


@router.get("/availability/days", response_model=AvailabilityDaysRead)
async def availability_days_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    asset_id: Annotated[UUID, Query()],
    starts_at: Annotated[datetime, Query()],
    ends_at: Annotated[datetime, Query()],
    quantity: Annotated[int, Query(ge=1)] = 1,
    location_id: Annotated[UUID | None, Query()] = None,
) -> AvailabilityDaysRead:
    return await build_asset_availability_days(
        session,
        asset_id=asset_id,
        starts_at=starts_at,
        ends_at=ends_at,
        quantity=quantity,
        location_id=location_id,
        actor=current_user,
    )


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking_endpoint(
    booking_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BookingRead:
    booking = await get_booking(session, booking_id)
    if booking is None:
        raise_not_found("Booking")
    lines = await list_booking_lines(session, booking.id)
    return build_booking_read(booking, lines)


@router.post("/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking_endpoint(
    booking_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookingRead:
    booking = await get_booking(session, booking_id)
    if booking is None:
        raise_not_found("Booking")
    cancelled = await cancel_booking(session, booking, current_user)
    lines = await list_booking_lines(session, cancelled.id)
    return build_booking_read(cancelled, lines)


def build_booking_read(booking: Booking, lines: list[BookingLine]) -> BookingRead:
    return BookingRead(
        id=booking.id,
        requested_by_user_id=booking.requested_by_user_id,
        title=booking.title,
        status=booking.status,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        notes=booking.notes,
        lines=[BookingLineRead.model_validate(line) for line in lines],
    )
