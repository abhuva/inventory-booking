from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.checkouts.models import Checkout, CheckoutLine
from inventory_booking_api.checkouts.schemas import (
    CheckoutCreate,
    CheckoutLineRead,
    CheckoutRead,
    CheckoutSummaryRead,
)
from inventory_booking_api.checkouts.service import (
    create_checkout,
    get_checkout,
    list_checkout_lines,
    list_checkouts,
)
from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/checkouts", tags=["checkouts"])


@router.get("", response_model=list[CheckoutSummaryRead])
async def list_checkout_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CheckoutSummaryRead]:
    return await list_checkouts(session)


@router.post("", response_model=CheckoutRead)
async def create_checkout_endpoint(
    payload: CheckoutCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CheckoutRead:
    checkout, lines = await create_checkout(session, payload, current_user)
    return build_checkout_read(checkout, lines)


@router.get("/{checkout_id}", response_model=CheckoutRead)
async def get_checkout_endpoint(
    checkout_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CheckoutRead:
    checkout = await get_checkout(session, checkout_id)
    if checkout is None:
        raise_not_found("Checkout")
    lines = await list_checkout_lines(session, checkout.id)
    return build_checkout_read(checkout, lines)


def build_checkout_read(checkout: Checkout, lines: list[CheckoutLine]) -> CheckoutRead:
    return CheckoutRead(
        id=checkout.id,
        booking_id=checkout.booking_id,
        checked_out_by_user_id=checkout.checked_out_by_user_id,
        checked_out_to_user_id=checkout.checked_out_to_user_id,
        status=checkout.status,
        notes=checkout.notes,
        lines=[CheckoutLineRead.model_validate(line) for line in lines],
    )
