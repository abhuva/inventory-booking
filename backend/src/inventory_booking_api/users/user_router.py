from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import require_admin
from inventory_booking_api.users.models import User
from inventory_booking_api.users.schemas import UserCreate, UserRead, UserUpdate
from inventory_booking_api.users.service import create_user, get_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_user_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_admin)],
) -> list[UserRead]:
    return await list_users(session)


@router.post("", response_model=UserRead)
async def create_user_endpoint(
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UserRead:
    return await create_user(session, payload, current_user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user_endpoint(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[User, Depends(require_admin)],
) -> UserRead:
    user = await get_user(session, user_id)
    if user is None:
        raise_not_found("User")
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: UUID,
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_admin)],
) -> UserRead:
    user = await get_user(session, user_id)
    if user is None:
        raise_not_found("User")
    return await update_user(session, user, payload, current_user)
