from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.bookings.enums import BookingStatus
from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin


class Booking(IdMixin, TimestampMixin, Base):
    """Planned reservation of tracked assets or stock quantities."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="booking_valid_time_range"),
    )

    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    person_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=BookingStatus.RESERVED,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BookingLine(IdMixin, TimestampMixin, Base):
    """One asset reservation within a booking."""

    __tablename__ = "booking_lines"
    __table_args__ = (
        UniqueConstraint("booking_id", "asset_id", "location_id", name="uq_booking_line_scope"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="booking_line_positive_quantity"),
    )

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
