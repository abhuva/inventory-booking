from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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
        UniqueConstraint(
            "booking_id",
            "asset_id",
            "location_id",
            "starts_at",
            "ends_at",
            name="uq_booking_lines_booking_id",
        ),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="booking_line_positive_quantity"),
        CheckConstraint("starts_at < ends_at", name="booking_line_valid_time_range"),
        CheckConstraint(
            "rental_unit_price_per_day IS NULL OR rental_unit_price_per_day >= 0",
            name="rental_unit_price_non_negative",
        ),
        CheckConstraint("rental_days IS NULL OR rental_days > 0", name="rental_days_positive"),
        CheckConstraint(
            "rental_total IS NULL OR rental_total >= 0",
            name="rental_total_non_negative",
        ),
    )

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    rental_unit_price_per_day: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 6), nullable=True
    )
    rental_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rental_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
