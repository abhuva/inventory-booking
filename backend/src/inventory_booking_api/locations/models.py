from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.locations.enums import LocationType


class Location(IdMixin, TimestampMixin, Base):
    """Physical or operational place where assets can be stored or used."""

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    type: Mapped[LocationType] = mapped_column(
        Enum(
            LocationType,
            name="location_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LocationImage(IdMixin, TimestampMixin, Base):
    """Stored primary image metadata for one location."""

    __tablename__ = "location_images"

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
