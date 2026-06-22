from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.checkouts.enums import CheckoutStatus
from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.inventory.enums import AssetCondition


class Checkout(IdMixin, TimestampMixin, Base):
    """Operational checkout created from a reserved booking."""

    __tablename__ = "checkouts"

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), unique=True, nullable=False)
    checked_out_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    checked_out_to_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    status: Mapped[CheckoutStatus] = mapped_column(
        Enum(
            CheckoutStatus,
            name="checkout_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=CheckoutStatus.CHECKED_OUT,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CheckoutLine(IdMixin, TimestampMixin, Base):
    """One checked-out booking line."""

    __tablename__ = "checkout_lines"
    __table_args__ = (
        UniqueConstraint("checkout_id", "asset_id", "location_id", name="uq_checkout_line_scope"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="checkout_line_positive_quantity"),
        CheckConstraint("quantity_returned >= 0", name="checkout_line_returned_non_negative"),
    )

    checkout_id: Mapped[UUID] = mapped_column(ForeignKey("checkouts.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    quantity_returned: Mapped[int] = mapped_column(nullable=False, default=0)
    condition_out: Mapped[AssetCondition] = mapped_column(
        Enum(
            AssetCondition,
            name="asset_condition",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=AssetCondition.UNKNOWN,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
