from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from inventory_booking_api.inventory.enums import AssetCondition, AssetStatus, AssetType


class QrCodeCreate(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class QrAssign(BaseModel):
    asset_id: UUID
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class QrCodeRead(BaseModel):
    id: UUID
    token: str
    asset_id: UUID | None
    label: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class QrResolvedAsset(BaseModel):
    id: UUID
    name: str
    asset_type: AssetType
    status: AssetStatus
    condition: AssetCondition
    current_location_id: UUID | None
    current_holder_user_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class QrResolveRead(BaseModel):
    token: str
    assigned: bool
    asset: QrResolvedAsset | None


class QrScanEventCreate(BaseModel):
    client_event_id: UUID

    model_config = ConfigDict(extra="forbid")


class QrScanEventRead(BaseModel):
    id: UUID
    asset_id: UUID
    asset_name: str
    created_at: datetime


class QrScanEventListRead(BaseModel):
    events: list[QrScanEventRead]
    cursor: datetime
