from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from inventory_booking_api.locations.enums import LocationType


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: LocationType
    address: str | None = None
    responsible_user_id: UUID | None = None
    notes: str | None = None
    is_active: bool = True


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: LocationType | None = None
    address: str | None = None
    responsible_user_id: UUID | None = None
    notes: str | None = None
    is_active: bool | None = None


class LocationRead(BaseModel):
    id: UUID
    name: str
    type: LocationType
    address: str | None
    responsible_user_id: UUID | None
    notes: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LocationImageRead(BaseModel):
    id: UUID
    location_id: UUID
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    created_by_user_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
