from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.inventory.enums import AssetCondition


class Return(IdMixin, TimestampMixin, Base):
    """Operational return against a checkout."""

    __tablename__ = "returns"

    checkout_id: Mapped[UUID] = mapped_column(ForeignKey("checkouts.id"), nullable=False)
    returned_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReturnLine(IdMixin, TimestampMixin, Base):
    """One returned checkout line."""

    __tablename__ = "return_lines"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity > 0", name="return_line_positive_quantity"),
    )

    return_id: Mapped[UUID] = mapped_column(ForeignKey("returns.id"), nullable=False)
    checkout_line_id: Mapped[UUID] = mapped_column(ForeignKey("checkout_lines.id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    quantity: Mapped[int | None] = mapped_column(nullable=True)
    condition_in: Mapped[AssetCondition] = mapped_column(
        Enum(
            AssetCondition,
            name="asset_condition",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=AssetCondition.UNKNOWN,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
