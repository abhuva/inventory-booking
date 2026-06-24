from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.locations.image_service import (
    delete_location_image,
    get_location_image,
    list_location_images,
    resolve_image_file,
    store_location_image,
)
from inventory_booking_api.locations.schemas import (
    LocationCreate,
    LocationImageRead,
    LocationRead,
    LocationUpdate,
)
from inventory_booking_api.locations.service import (
    create_location,
    delete_location,
    get_location,
    list_locations,
    update_location,
)
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_location_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LocationRead]:
    return await list_locations(session)


@router.post("", response_model=LocationRead)
async def create_location_endpoint(
    payload: LocationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LocationRead:
    return await create_location(session, payload, current_user)


@router.get("/images", response_model=list[LocationImageRead])
async def list_location_images_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[LocationImageRead]:
    return await list_location_images(session)


@router.get("/{location_id}", response_model=LocationRead)
async def get_location_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LocationRead:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    return location


@router.get("/{location_id}/image", response_model=LocationImageRead)
async def get_location_image_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LocationImageRead:
    image = await get_location_image(session, location_id)
    if image is None:
        raise_not_found("Location image")
    return image


@router.get("/{location_id}/image/content")
async def get_location_image_content_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    image = await get_location_image(session, location_id)
    if image is None:
        raise_not_found("Location image")
    return FileResponse(resolve_image_file(image), media_type=image.mime_type)


@router.post("/{location_id}/image", response_model=LocationImageRead)
async def upload_location_image_endpoint(
    location_id: UUID,
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LocationImageRead:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    return await store_location_image(session, location, file, current_user)


@router.delete("/{location_id}/image", status_code=204)
async def delete_location_image_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    await delete_location_image(session, location, current_user)
    return Response(status_code=204)


@router.patch(
    "/{location_id}",
    response_model=LocationRead,
)
async def update_location_endpoint(
    location_id: UUID,
    payload: LocationUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LocationRead:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    return await update_location(session, location, payload, current_user)


@router.delete("/{location_id}", status_code=204)
async def delete_location_endpoint(
    location_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    location = await get_location(session, location_id)
    if location is None:
        raise_not_found("Location")
    await delete_location(session, location, current_user)
    return Response(status_code=204)
