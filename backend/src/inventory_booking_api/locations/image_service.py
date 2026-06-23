from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.inventory.asset_image_service import (
    ALLOWED_IMAGE_MIME_TYPES,
    MIME_EXTENSIONS,
    detect_image_mime_type,
)
from inventory_booking_api.locations.models import Location, LocationImage
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User


async def list_location_images(session: AsyncSession) -> list[LocationImage]:
    """Return current primary image metadata for locations."""

    result = await session.execute(select(LocationImage).order_by(LocationImage.created_at.desc()))
    return list(result.scalars().all())


async def get_location_image(session: AsyncSession, location_id: UUID) -> LocationImage | None:
    """Return image metadata for a location, if present."""

    result = await session.execute(
        select(LocationImage).where(LocationImage.location_id == location_id)
    )
    return result.scalar_one_or_none()


async def store_location_image(
    session: AsyncSession,
    location: Location,
    file: UploadFile,
    actor: User,
) -> LocationImage:
    """Validate and store a primary image derivative for a location."""

    settings = get_settings()
    content = await file.read(settings.asset_image_max_bytes + 1)
    if len(content) > settings.asset_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Location image is too large.",
        )

    mime_type = detect_image_mime_type(content)
    if mime_type is None or file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only WebP, JPEG, and PNG location images are allowed.",
        )
    if file.content_type != mime_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image MIME type does not match file contents.",
        )

    existing = await get_location_image(session, location.id)
    storage_path = relative_storage_path(location.id, mime_type)
    absolute_path = resolve_storage_path(storage_path)
    if existing is not None:
        delete_stored_file(existing.storage_path)
        await session.delete(existing)
        await session.flush()

    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content)

    image = LocationImage(
        location_id=location.id,
        storage_path=storage_path,
        mime_type=mime_type,
        size_bytes=len(content),
        width=None,
        height=None,
        created_by_user_id=actor.id,
    )
    session.add(image)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="location_image",
        entity_id=image.id,
        summary=f"Updated image for location {location.name}",
        details={"location_id": str(location.id), "size_bytes": image.size_bytes},
    )
    await session.commit()
    await session.refresh(image)
    return image


async def delete_location_image(session: AsyncSession, location: Location, actor: User) -> None:
    """Delete the primary image for a location if it exists."""

    image = await get_location_image(session, location.id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location image not found."
        )

    delete_stored_file(image.storage_path)
    await session.delete(image)
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="location_image",
        entity_id=image.id,
        summary=f"Deleted image for location {location.name}",
        details={"location_id": str(location.id)},
    )
    await session.commit()


def resolve_image_file(image: LocationImage) -> Path:
    """Return the validated absolute file path for stored image content."""

    path = resolve_storage_path(image.storage_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Location image not found."
        )
    return path


def relative_storage_path(location_id: UUID, mime_type: str) -> str:
    extension = MIME_EXTENSIONS[mime_type]
    return f"{location_id}/primary{extension}"


def resolve_storage_path(storage_path: str) -> Path:
    root = Path(get_settings().location_upload_dir).resolve()
    path = (root / storage_path).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image path.")
    return path


def delete_stored_file(storage_path: str) -> None:
    path = resolve_storage_path(storage_path)
    if path.is_file():
        path.unlink()
