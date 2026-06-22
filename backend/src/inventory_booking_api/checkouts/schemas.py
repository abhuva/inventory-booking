from uuid import UUID

from pydantic import BaseModel, ConfigDict

from inventory_booking_api.checkouts.enums import CheckoutStatus
from inventory_booking_api.inventory.enums import AssetCondition


class CheckoutCreate(BaseModel):
    booking_id: UUID
    checked_out_to_user_id: UUID | None = None
    condition_out: AssetCondition = AssetCondition.UNKNOWN
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class CheckoutLineRead(BaseModel):
    id: UUID
    checkout_id: UUID
    asset_id: UUID
    location_id: UUID | None
    quantity: int | None
    quantity_returned: int
    condition_out: AssetCondition
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class CheckoutRead(BaseModel):
    id: UUID
    booking_id: UUID
    checked_out_by_user_id: UUID
    checked_out_to_user_id: UUID | None
    status: CheckoutStatus
    notes: str | None
    lines: list[CheckoutLineRead] = []

    model_config = ConfigDict(from_attributes=True)


class CheckoutSummaryRead(BaseModel):
    id: UUID
    booking_id: UUID
    checked_out_by_user_id: UUID
    checked_out_to_user_id: UUID | None
    status: CheckoutStatus
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
