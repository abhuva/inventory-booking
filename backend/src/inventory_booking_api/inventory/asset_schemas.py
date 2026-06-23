from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    asset_type: AssetType
    category_id: UUID | None = None
    status: AssetStatus = AssetStatus.AVAILABLE
    condition: AssetCondition = AssetCondition.UNKNOWN
    unit_name: str | None = Field(default=None, max_length=40)
    home_location_id: UUID | None = None
    current_location_id: UUID | None = None
    current_holder_user_id: UUID | None = None
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    asset_tag: str | None = Field(default=None, max_length=80)
    replacement_value: Decimal | None = None
    description: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_asset_mode(self) -> "AssetCreate":
        if self.asset_type == AssetType.TRACKED and self.unit_name is not None:
            raise ValueError("Tracked assets must not define unit_name.")
        if self.asset_type == AssetType.STOCK and not self.unit_name:
            raise ValueError("Stock assets must define unit_name.")
        return self


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category_id: UUID | None = None
    status: AssetStatus | None = None
    condition: AssetCondition | None = None
    home_location_id: UUID | None = None
    current_location_id: UUID | None = None
    current_holder_user_id: UUID | None = None
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    asset_tag: str | None = Field(default=None, max_length=80)
    replacement_value: Decimal | None = None
    description: str | None = None
    notes: str | None = None


class AssetRead(BaseModel):
    id: UUID
    name: str
    asset_type: AssetType
    category_id: UUID | None
    status: AssetStatus
    condition: AssetCondition
    unit_name: str | None
    home_location_id: UUID | None
    current_location_id: UUID | None
    current_holder_user_id: UUID | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    asset_tag: str | None
    replacement_value: Decimal | None
    description: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class AssetImageRead(BaseModel):
    id: UUID
    asset_id: UUID
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockLevelCreate(BaseModel):
    asset_id: UUID
    location_id: UUID
    quantity_total: int = Field(ge=0)
    quantity_reserved: int = Field(default=0, ge=0)
    quantity_checked_out: int = Field(default=0, ge=0)


class StockLevelUpdate(BaseModel):
    quantity_total: int | None = Field(default=None, ge=0)
    quantity_reserved: int | None = Field(default=None, ge=0)
    quantity_checked_out: int | None = Field(default=None, ge=0)


class StockLevelRead(BaseModel):
    id: UUID
    asset_id: UUID
    location_id: UUID
    quantity_total: int
    quantity_reserved: int
    quantity_checked_out: int

    model_config = ConfigDict(from_attributes=True)


class TrackedAssetTransfer(BaseModel):
    to_location_id: UUID | None = None
    to_holder_user_id: UUID | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class StockTransfer(BaseModel):
    asset_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: int = Field(gt=0)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class MaintenanceStart(BaseModel):
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class MaintenanceComplete(BaseModel):
    condition: AssetCondition = AssetCondition.GOOD
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class AssetStateChange(BaseModel):
    status: AssetStatus
    condition: AssetCondition | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")
