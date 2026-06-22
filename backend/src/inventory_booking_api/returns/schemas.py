from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from inventory_booking_api.inventory.enums import AssetCondition


class ReturnLineCreate(BaseModel):
    checkout_line_id: UUID
    quantity: int | None = Field(default=None, gt=0)
    condition_in: AssetCondition = AssetCondition.UNKNOWN
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class ReturnCreate(BaseModel):
    checkout_id: UUID
    notes: str | None = None
    lines: list[ReturnLineCreate] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class ReturnLineRead(BaseModel):
    id: UUID
    return_id: UUID
    checkout_line_id: UUID
    asset_id: UUID
    location_id: UUID | None
    quantity: int | None
    condition_in: AssetCondition
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class ReturnRead(BaseModel):
    id: UUID
    checkout_id: UUID
    returned_by_user_id: UUID
    notes: str | None
    lines: list[ReturnLineRead] = []

    model_config = ConfigDict(from_attributes=True)


class ReturnSummaryRead(BaseModel):
    id: UUID
    checkout_id: UUID
    returned_by_user_id: UUID
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
