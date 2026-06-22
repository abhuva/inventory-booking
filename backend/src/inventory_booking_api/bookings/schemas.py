from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from inventory_booking_api.bookings.enums import BookingStatus


class BookingLineCreate(BaseModel):
    asset_id: UUID
    location_id: UUID | None = None
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None


class BookingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None
    lines: list[BookingLineCreate] = Field(min_length=1)

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
