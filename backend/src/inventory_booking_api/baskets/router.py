from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.baskets.models import Basket, BasketLine
from inventory_booking_api.baskets.schemas import (
    BasketCreate,
    BasketLineCreate,
    BasketLineRead,
    BasketLineUpdate,
    BasketRead,
    BasketUpdate,
)
from inventory_booking_api.baskets.service import (
    add_or_update_basket_line,
    cancel_basket,
    confirm_basket,
    create_or_update_active_basket,
    get_active_basket,
    get_basket,
    list_basket_lines,
    remove_basket_line,
    update_basket,
    update_basket_line,
)
from inventory_booking_api.bookings.router import build_booking_read
from inventory_booking_api.bookings.schemas import BookingRead
from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/basket", tags=["basket"])


@router.get("/active", response_model=BasketRead | None)
async def get_active_basket_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead | None:
    basket = await get_active_basket(session, current_user)
    if basket is None:
        return None
    lines = await list_basket_lines(session, basket.id)
    return build_basket_read(basket, lines)


@router.post("", response_model=BasketRead)
async def create_or_update_basket_endpoint(
    payload: BasketCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead:
    basket = await create_or_update_active_basket(session, payload, current_user)
    lines = await list_basket_lines(session, basket.id)
    return build_basket_read(basket, lines)


@router.patch("/{basket_id}", response_model=BasketRead)
async def update_basket_endpoint(
    basket_id: UUID,
    payload: BasketUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead:
    basket = await get_owned_basket(session, basket_id, current_user)
    updated = await update_basket(session, basket, payload, current_user)
    lines = await list_basket_lines(session, updated.id)
    return build_basket_read(updated, lines)


@router.post("/{basket_id}/lines", response_model=BasketRead)
async def add_basket_line_endpoint(
    basket_id: UUID,
    payload: BasketLineCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead:
    basket = await get_owned_basket(session, basket_id, current_user)
    await add_or_update_basket_line(session, basket, payload, current_user)
    lines = await list_basket_lines(session, basket.id)
    return build_basket_read(basket, lines)


@router.delete("/{basket_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_basket_line_endpoint(
    basket_id: UUID,
    line_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    basket = await get_owned_basket(session, basket_id, current_user)
    await remove_basket_line(session, basket, line_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{basket_id}/lines/{line_id}", response_model=BasketRead)
async def update_basket_line_endpoint(
    basket_id: UUID,
    line_id: UUID,
    payload: BasketLineUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead:
    basket = await get_owned_basket(session, basket_id, current_user)
    await update_basket_line(session, basket, line_id, payload, current_user)
    lines = await list_basket_lines(session, basket.id)
    return build_basket_read(basket, lines)


@router.post("/{basket_id}/cancel", response_model=BasketRead)
async def cancel_basket_endpoint(
    basket_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BasketRead:
    basket = await get_owned_basket(session, basket_id, current_user)
    cancelled = await cancel_basket(session, basket, current_user)
    lines = await list_basket_lines(session, cancelled.id)
    return build_basket_read(cancelled, lines)


@router.post("/{basket_id}/confirm", response_model=BookingRead)
async def confirm_basket_endpoint(
    basket_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookingRead:
    basket = await get_owned_basket(session, basket_id, current_user)
    _, booking, lines = await confirm_basket(session, basket, current_user)
    return build_booking_read(booking, lines)


async def get_owned_basket(session: AsyncSession, basket_id: UUID, actor: User) -> Basket:
    basket = await get_basket(session, basket_id)
    if basket is None or basket.user_id != actor.id:
        raise_not_found("Basket")
    return basket


def build_basket_read(basket: Basket, lines: list[BasketLine]) -> BasketRead:
    return BasketRead(
        id=basket.id,
        user_id=basket.user_id,
        person_id=basket.person_id,
        title=basket.title,
        status=basket.status,
        starts_at=basket.starts_at,
        ends_at=basket.ends_at,
        expires_at=basket.expires_at,
        notes=basket.notes,
        lines=[BasketLineRead.model_validate(line) for line in lines],
    )
