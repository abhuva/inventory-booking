from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from inventory_booking_api.baskets.enums import BasketStatus


class BasketLineCreate(BaseModel):
    asset_id: UUID
    location_id: UUID | None = None
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class BasketCreate(BaseModel):
    title: str = Field(default="New basket", min_length=1, max_length=180)
    person_id: UUID | None = None
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_time_range(self) -> "BasketCreate":
        if self.starts_at >= self.ends_at:
            raise ValueError("Basket starts_at must be before ends_at.")
        return self


class BasketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    person_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class BasketLineRead(BaseModel):
    id: UUID
    basket_id: UUID
    asset_id: UUID
    location_id: UUID | None
    quantity: int | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class BasketRead(BaseModel):
    id: UUID
    user_id: UUID
    person_id: UUID | None
    title: str
    status: BasketStatus
    starts_at: datetime
    ends_at: datetime
    expires_at: datetime
    notes: str | None
    lines: list[BasketLineRead] = []

    model_config = ConfigDict(from_attributes=True)
