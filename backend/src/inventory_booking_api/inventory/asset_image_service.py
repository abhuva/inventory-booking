from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.audit.service import write_audit_log, write_item_event
from inventory_booking_api.inventory.models import Asset, AssetImage
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User

ALLOWED_IMAGE_MIME_TYPES = {"image/webp", "image/jpeg", "image/png"}
MIME_EXTENSIONS = {"image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png"}
PIL_FORMATS = {"image/webp": "WEBP", "image/jpeg": "JPEG", "image/png": "PNG"}


async def list_asset_images(session: AsyncSession) -> list[AssetImage]:
    """Return current primary image metadata for assets."""

    result = await session.execute(select(AssetImage).order_by(AssetImage.created_at.desc()))
    return list(result.scalars().all())


async def get_asset_image(session: AsyncSession, asset_id: UUID) -> AssetImage | None:
    """Return image metadata for an asset, if present."""

    result = await session.execute(select(AssetImage).where(AssetImage.asset_id == asset_id))
    return result.scalar_one_or_none()


async def store_asset_image(
    session: AsyncSession,
    asset: Asset,
    file: UploadFile,
    actor: User,
) -> AssetImage:
    """Validate and store a primary image derivative for an asset."""

    settings = get_settings()
    content = await file.read(settings.asset_image_max_bytes + 1)
    if len(content) > settings.asset_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Asset image is too large.",
        )

    mime_type = detect_image_mime_type(content)
    if mime_type is None or file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only WebP, JPEG, and PNG asset images are allowed.",
        )
    if file.content_type != mime_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image MIME type does not match file contents.",
        )
    normalized = normalize_image(content, mime_type)
    if len(normalized.content) > settings.asset_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Asset image is too large after processing.",
        )

    existing = await get_asset_image(session, asset.id)
    storage_path = relative_storage_path(asset.id, mime_type)
    absolute_path = resolve_storage_path(storage_path)
    if existing is not None:
        delete_stored_file(existing.storage_path)
        await session.delete(existing)
        await session.flush()

    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(normalized.content)

    image = AssetImage(
        asset_id=asset.id,
        storage_path=storage_path,
        mime_type=mime_type,
        size_bytes=len(normalized.content),
        width=normalized.width,
        height=normalized.height,
        created_by_user_id=actor.id,
    )
    session.add(image)
    await session.flush()
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Asset image updated",
        details={"asset_image_id": str(image.id), "mime_type": image.mime_type},
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="asset_image",
        entity_id=image.id,
        summary=f"Updated image for asset {asset.name}",
        details={"asset_id": str(asset.id), "size_bytes": image.size_bytes},
    )
    await session.commit()
    await session.refresh(image)
    return image


async def delete_asset_image(session: AsyncSession, asset: Asset, actor: User) -> None:
    """Delete the primary image for an asset if it exists."""

    image = await get_asset_image(session, asset.id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset image not found.")

    delete_stored_file(image.storage_path)
    await session.delete(image)
    await write_item_event(
        session,
        asset_id=asset.id,
        event_type=ItemEventType.UPDATED,
        actor=actor,
        notes="Asset image deleted",
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="asset_image",
        entity_id=image.id,
        summary=f"Deleted image for asset {asset.name}",
        details={"asset_id": str(asset.id)},
    )
    await session.commit()


def resolve_image_file(image: AssetImage) -> Path:
    """Return the validated absolute file path for stored image content."""

    path = resolve_storage_path(image.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset image not found.")
    return path


def detect_image_mime_type(content: bytes) -> str | None:
    """Sniff a small set of allowed image formats from file signatures."""

    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


class NormalizedImage:
    def __init__(self, content: bytes, width: int, height: int) -> None:
        self.content = content
        self.width = width
        self.height = height


def normalize_image(content: bytes, mime_type: str) -> NormalizedImage:
    """Decode and re-encode image bytes to strip unsafe/polyglot payloads."""

    try:
        with Image.open(BytesIO(content)) as image:
            image.load()
            width, height = image.size
            output = BytesIO()
            if mime_type == "image/jpeg":
                image = image.convert("RGB")
                image.save(output, format=PIL_FORMATS[mime_type], quality=85, optimize=True)
            elif mime_type == "image/png":
                image.save(output, format=PIL_FORMATS[mime_type], optimize=True)
            else:
                image.save(output, format=PIL_FORMATS[mime_type], quality=85, method=6)
    except (OSError, UnidentifiedImageError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image could not be decoded.",
        ) from None

    return NormalizedImage(output.getvalue(), width, height)


def relative_storage_path(asset_id: UUID, mime_type: str) -> str:
    extension = MIME_EXTENSIONS[mime_type]
    return f"{asset_id}/primary{extension}"


def resolve_storage_path(storage_path: str) -> Path:
    root = Path(get_settings().asset_upload_dir).resolve()
    path = (root / storage_path).resolve()
    if root != path and root not in path.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image path.")
    return path


def delete_stored_file(storage_path: str) -> None:
    path = resolve_storage_path(storage_path)
    if path.is_file():
        path.unlink()
