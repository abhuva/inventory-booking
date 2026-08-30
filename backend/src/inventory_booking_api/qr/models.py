from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin


class QrCode(IdMixin, TimestampMixin, Base):
    """Opaque QR label that may be assigned to one asset."""

    __tablename__ = "qr_codes"

    token: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id"), unique=True, nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class QrScanEvent(IdMixin, TimestampMixin, Base):
    """Short-lived notification that a user scanned an assigned QR label."""

    __tablename__ = "qr_scan_events"
    __table_args__ = (
        UniqueConstraint("user_id", "client_event_id", name="uq_qr_scan_events_user_client_event"),
        Index("ix_qr_scan_events_user_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    qr_code_id: Mapped[UUID] = mapped_column(
        ForeignKey("qr_codes.id", ondelete="CASCADE"), nullable=False
    )
    client_event_id: Mapped[UUID] = mapped_column(nullable=False)
