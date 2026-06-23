from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from inventory_booking_api.bookings.enums import BookingStatus


class BookingLineCreate(BaseModel):
    asset_id: UUID
    location_id: UUID | None = None
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class BookingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None
    lines: list[BookingLineCreate] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_time_range(self) -> "BookingCreate":
        if self.starts_at >= self.ends_at:
            raise ValueError("Booking starts_at must be before ends_at.")
        return self


class BookingLineRead(BaseModel):
    id: UUID
    booking_id: UUID
    asset_id: UUID
    location_id: UUID | None
    quantity: int | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class BookingRead(BaseModel):
    id: UUID
    requested_by_user_id: UUID
    title: str
    status: BookingStatus
    starts_at: datetime
    ends_at: datetime
    notes: str | None
    lines: list[BookingLineRead] = []

    model_config = ConfigDict(from_attributes=True)


class BookingSummaryRead(BaseModel):
    id: UUID
    requested_by_user_id: UUID
    title: str
    status: BookingStatus
    starts_at: datetime
    ends_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class AvailabilityLineRead(BaseModel):
    asset_id: UUID
    location_id: UUID | None
    requested_quantity: int | None
    available_quantity: int | None
    available: bool
    reason: str | None


class AvailabilityRead(BaseModel):
    available: bool
    lines: list[AvailabilityLineRead]


class AvailabilityDayRead(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    total_quantity: int
    reserved_quantity: int
    held_quantity: int
    available_quantity: int
    requested_quantity: int
    available: bool
    reason: str | None


class AvailabilityDaysRead(BaseModel):
    asset_id: UUID
    location_id: UUID | None
    quantity: int
    starts_at: datetime
    ends_at: datetime
    days: list[AvailabilityDayRead]


class HeatmapCellRead(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    total_quantity: int
    reserved_quantity: int
    held_quantity: int
    available_quantity: int


class HeatmapItemRead(BaseModel):
    asset_id: UUID
    name: str
    unit_name: str | None
    total_quantity: int
    cells: list[HeatmapCellRead]


class AvailabilityHeatmapRead(BaseModel):
    starts_at: datetime
    ends_at: datetime
    bucket: str
    location_id: UUID | None
    items: list[HeatmapItemRead]
