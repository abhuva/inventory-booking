from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin


class QrCode(IdMixin, TimestampMixin, Base):
    """Opaque QR label that may be assigned to one tracked asset."""

    __tablename__ = "qr_codes"

    token: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id"), unique=True, nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
