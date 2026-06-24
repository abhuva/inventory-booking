from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.baskets.enums import BasketStatus
from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin


class Basket(IdMixin, TimestampMixin, Base):
    """Temporary user-held reservation basket before it becomes a booking."""

    __tablename__ = "baskets"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="basket_valid_time_range"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    person_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[BasketStatus] = mapped_column(
        Enum(
            BasketStatus,
            name="basket_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=BasketStatus.ACTIVE,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class BasketLine(IdMixin, TimestampMixin, Base):
    """One temporary held asset reservation inside a basket."""

    __tablename__ = "basket_lines"
    __table_args__ = (
        UniqueConstraint("basket_id", "asset_id", "location_id", name="uq_basket_line_scope"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="basket_line_positive_quantity"),
    )

    basket_id: Mapped[UUID] = mapped_column(ForeignKey("baskets.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
