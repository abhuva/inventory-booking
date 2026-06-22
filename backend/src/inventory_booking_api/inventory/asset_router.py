from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.inventory.asset_schemas import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    StockLevelCreate,
    StockLevelRead,
    StockLevelUpdate,
)
from inventory_booking_api.inventory.asset_service import (
    create_asset,
    create_stock_level,
    get_asset,
    get_stock_level,
    list_assets,
    list_stock_levels,
    update_asset,
    update_stock_level,
)

asset_router = APIRouter(prefix="/assets", tags=["assets"])
stock_router = APIRouter(prefix="/stock-levels", tags=["stock-levels"])


@asset_router.get("", response_model=list[AssetRead])
async def list_asset_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AssetRead]:
    return await list_assets(session)


@asset_router.post("", response_model=AssetRead, dependencies=[Depends(get_current_user)])
async def create_asset_endpoint(
    payload: AssetCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetRead:
    return await create_asset(session, payload)


@asset_router.get("/{asset_id}", response_model=AssetRead)
async def get_asset_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return asset


@asset_router.patch(
    "/{asset_id}",
    response_model=AssetRead,
    dependencies=[Depends(get_current_user)],
)
async def update_asset_endpoint(
    asset_id: UUID,
    payload: AssetUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await update_asset(session, asset, payload)


@stock_router.get("", response_model=list[StockLevelRead])
async def list_stock_level_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[StockLevelRead]:
    return await list_stock_levels(session)


@stock_router.post(
    "",
    response_model=StockLevelRead,
    dependencies=[Depends(get_current_user)],
)
async def create_stock_level_endpoint(
    payload: StockLevelCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StockLevelRead:
    return await create_stock_level(session, payload)


@stock_router.get("/{stock_level_id}", response_model=StockLevelRead)
async def get_stock_level_endpoint(
    stock_level_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StockLevelRead:
    stock_level = await get_stock_level(session, stock_level_id)
    if stock_level is None:
        raise_not_found("Stock level")
    return stock_level


@stock_router.patch(
    "/{stock_level_id}",
    response_model=StockLevelRead,
    dependencies=[Depends(get_current_user)],
)
async def update_stock_level_endpoint(
    stock_level_id: UUID,
    payload: StockLevelUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StockLevelRead:
    stock_level = await get_stock_level(session, stock_level_id)
    if stock_level is None:
        raise_not_found("Stock level")
    return await update_stock_level(session, stock_level, payload)

