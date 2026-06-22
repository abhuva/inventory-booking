from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.inventory.category_schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)
from inventory_booking_api.inventory.category_service import (
    create_category,
    get_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def list_category_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CategoryRead]:
    return await list_categories(session)


@router.post("", response_model=CategoryRead, dependencies=[Depends(get_current_user)])
async def create_category_endpoint(
    payload: CategoryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryRead:
    return await create_category(session, payload)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category_endpoint(
    category_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryRead:
    category = await get_category(session, category_id)
    if category is None:
        raise_not_found("Category")
    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    dependencies=[Depends(get_current_user)],
)
async def update_category_endpoint(
    category_id: UUID,
    payload: CategoryUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryRead:
    category = await get_category(session, category_id)
    if category is None:
        raise_not_found("Category")
    return await update_category(session, category, payload)

