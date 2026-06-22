from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inventory_booking_api.core.models import Base, IdMixin, TimestampMixin
from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType


class Category(IdMixin, TimestampMixin, Base):
    """Inventory grouping such as aerial, juggling, balance, or storage."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Asset(IdMixin, TimestampMixin, Base):
    """Tracked or stock inventory asset."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "(asset_type = 'tracked' AND unit_name IS NULL) OR "
            "(asset_type = 'stock' AND unit_name IS NOT NULL)",
            name="asset_type_unit_name_consistency",
        ),
    )

    name: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType, name="asset_type", values_callable=lambda enum: [item.value for item in enum]
        ),
        nullable=False,
    )
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(
            AssetStatus,
            name="asset_status",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=AssetStatus.AVAILABLE,
    )
    condition: Mapped[AssetCondition] = mapped_column(
        Enum(
            AssetCondition,
            name="asset_condition",
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=AssetCondition.UNKNOWN,
    )
    unit_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    home_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    current_location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True
    )
    current_holder_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_tag: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    replacement_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockLevel(IdMixin, TimestampMixin, Base):
    """Quantity of a stock asset at a location."""

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("asset_id", "location_id", name="uq_stock_levels_asset_location"),
        CheckConstraint("quantity_total >= 0", name="stock_level_quantity_total_non_negative"),
        CheckConstraint(
            "quantity_reserved >= 0", name="stock_level_quantity_reserved_non_negative"
        ),
        CheckConstraint(
            "quantity_checked_out >= 0",
            name="stock_level_quantity_checked_out_non_negative",
        ),
    )

    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("locations.id"), nullable=False)
    quantity_total: Mapped[int] = mapped_column(nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(nullable=False, default=0)
    quantity_checked_out: Mapped[int] = mapped_column(nullable=False, default=0)
