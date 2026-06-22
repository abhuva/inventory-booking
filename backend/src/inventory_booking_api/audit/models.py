from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.audit.enums import AuditAction, ItemEventType
from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin


class ItemEvent(IdMixin, TimestampMixin, Base):
    """Append-only operational history for an asset."""

    __tablename__ = "item_events"

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), index=True, nullable=False)
    event_type: Mapped[ItemEventType] = mapped_column(
        Enum(
            ItemEventType,
            name="item_event_type",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    to_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class AuditLog(IdMixin, TimestampMixin, Base):
    """Security-relevant mutation log."""

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction,
            name="audit_action",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
