from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user, require_admin
from inventory_booking_api.inventory.asset_commands import create_asset, delete_asset, update_asset
from inventory_booking_api.inventory.asset_image_service import (
    delete_asset_image,
    get_asset_image,
    list_asset_images,
    resolve_image_file,
    store_asset_image,
)
from inventory_booking_api.inventory.asset_schemas import (
    AssetCreate,
    AssetImageRead,
    AssetRead,
    AssetStateChange,
    AssetUpdate,
    MaintenanceComplete,
    MaintenanceStart,
    StockLevelCreate,
    StockLevelRead,
    StockLevelUpdate,
    StockTransfer,
    TrackedAssetTransfer,
)
from inventory_booking_api.inventory.enums import AssetStatus
from inventory_booking_api.inventory.movement_commands import transfer_stock, transfer_tracked_asset
from inventory_booking_api.inventory.queries import (
    get_asset,
    get_stock_level,
    list_assets,
    list_stock_levels,
)
from inventory_booking_api.inventory.stock_commands import create_stock_level, update_stock_level
from inventory_booking_api.inventory.tracked_unit_commands import (
    change_asset_state,
    complete_asset_maintenance,
    start_asset_maintenance,
)
from inventory_booking_api.qr.schemas import QrCodeRead
from inventory_booking_api.qr.service import ensure_qr_code_for_asset, get_qr_code_for_asset
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User

asset_router = APIRouter(prefix="/assets", tags=["assets"])
stock_router = APIRouter(prefix="/stock-levels", tags=["stock-levels"])


@asset_router.get("", response_model=list[AssetRead])
async def list_asset_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AssetRead]:
    return await list_assets(session)


@asset_router.post("", response_model=AssetRead)
async def create_asset_endpoint(
    payload: AssetCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    return await create_asset(session, payload, current_user)


@asset_router.get("/images", response_model=list[AssetImageRead])
async def list_asset_images_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AssetImageRead]:
    return await list_asset_images(session)


@asset_router.get("/{asset_id}", response_model=AssetRead)
async def get_asset_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return asset


@asset_router.get("/{asset_id}/image", response_model=AssetImageRead)
async def get_asset_image_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetImageRead:
    image = await get_asset_image(session, asset_id)
    if image is None:
        raise_not_found("Asset image")
    return image


@asset_router.get("/{asset_id}/qr", response_model=QrCodeRead)
async def get_asset_qr_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QrCodeRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    qr_code = await get_qr_code_for_asset(session, asset.id)
    if qr_code is None:
        raise_not_found("QR label")
    return qr_code


@asset_router.post("/{asset_id}/qr", response_model=QrCodeRead)
async def ensure_asset_qr_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QrCodeRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await ensure_qr_code_for_asset(session, asset, current_user)


@asset_router.get("/{asset_id}/image/content")
async def get_asset_image_content_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    image = await get_asset_image(session, asset_id)
    if image is None:
        raise_not_found("Asset image")
    return FileResponse(resolve_image_file(image), media_type=image.mime_type)


@asset_router.post("/{asset_id}/image", response_model=AssetImageRead)
async def upload_asset_image_endpoint(
    asset_id: UUID,
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetImageRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await store_asset_image(session, asset, file, current_user)


@asset_router.delete("/{asset_id}/image", status_code=204)
async def delete_asset_image_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    await delete_asset_image(session, asset, current_user)
    return Response(status_code=204)


@asset_router.patch(
    "/{asset_id}",
    response_model=AssetRead,
)
async def update_asset_endpoint(
    asset_id: UUID,
    payload: AssetUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await update_asset(session, asset, payload, current_user)


@asset_router.delete("/{asset_id}", status_code=204)
async def delete_asset_endpoint(
    asset_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_admin)],
) -> Response:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    await delete_asset(session, asset, current_user)
    return Response(status_code=204)


@asset_router.post("/{asset_id}/transfer", response_model=AssetRead)
async def transfer_tracked_asset_endpoint(
    asset_id: UUID,
    payload: TrackedAssetTransfer,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await transfer_tracked_asset(session, asset, payload, current_user)


@asset_router.post("/{asset_id}/maintenance/start", response_model=AssetRead)
async def start_asset_maintenance_endpoint(
    asset_id: UUID,
    payload: MaintenanceStart,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await start_asset_maintenance(session, asset, payload.notes, current_user)


@asset_router.post("/{asset_id}/maintenance/complete", response_model=AssetRead)
async def complete_asset_maintenance_endpoint(
    asset_id: UUID,
    payload: MaintenanceComplete,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    return await complete_asset_maintenance(session, asset, payload, current_user)


@asset_router.post("/{asset_id}/state", response_model=AssetRead)
async def change_asset_state_endpoint(
    asset_id: UUID,
    payload: AssetStateChange,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssetRead:
    asset = await get_asset(session, asset_id)
    if asset is None:
        raise_not_found("Asset")
    irreversible_status = payload.status in (AssetStatus.LOST, AssetStatus.RETIRED)
    if irreversible_status and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required.")
    return await change_asset_state(session, asset, payload, current_user)


@stock_router.get("", response_model=list[StockLevelRead])
async def list_stock_level_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[StockLevelRead]:
    return await list_stock_levels(session)


@stock_router.post(
    "",
    response_model=StockLevelRead,
)
async def create_stock_level_endpoint(
    payload: StockLevelCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockLevelRead:
    return await create_stock_level(session, payload, current_user)


@stock_router.post("/transfer", response_model=list[StockLevelRead])
async def transfer_stock_endpoint(
    payload: StockTransfer,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[StockLevelRead]:
    source, destination = await transfer_stock(session, payload, current_user)
    return [source, destination]


@stock_router.get("/{stock_level_id}", response_model=StockLevelRead)
async def get_stock_level_endpoint(
    stock_level_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockLevelRead:
    stock_level = await get_stock_level(session, stock_level_id)
    if stock_level is None:
        raise_not_found("Stock level")
    return stock_level


@stock_router.patch(
    "/{stock_level_id}",
    response_model=StockLevelRead,
)
async def update_stock_level_endpoint(
    stock_level_id: UUID,
    payload: StockLevelUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StockLevelRead:
    stock_level = await get_stock_level(session, stock_level_id)
    if stock_level is None:
        raise_not_found("Stock level")
    return await update_stock_level(session, stock_level, payload, current_user)
