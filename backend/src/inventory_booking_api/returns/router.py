from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.returns.models import Return, ReturnLine
from inventory_booking_api.returns.schemas import (
    ReturnCreate,
    ReturnLineRead,
    ReturnRead,
    ReturnSummaryRead,
)
from inventory_booking_api.returns.service import (
    create_return,
    get_return,
    list_return_lines,
    list_returns,
)
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("", response_model=list[ReturnSummaryRead])
async def list_return_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ReturnSummaryRead]:
    return await list_returns(session)


@router.post("", response_model=ReturnRead)
async def create_return_endpoint(
    payload: ReturnCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReturnRead:
    return_record, lines = await create_return(session, payload, current_user)
    return build_return_read(return_record, lines)


@router.get("/{return_id}", response_model=ReturnRead)
async def get_return_endpoint(
    return_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReturnRead:
    return_record = await get_return(session, return_id)
    if return_record is None:
        raise_not_found("Return")
    lines = await list_return_lines(session, return_record.id)
    return build_return_read(return_record, lines)


def build_return_read(return_record: Return, lines: list[ReturnLine]) -> ReturnRead:
    return ReturnRead(
        id=return_record.id,
        checkout_id=return_record.checkout_id,
        returned_by_user_id=return_record.returned_by_user_id,
        notes=return_record.notes,
        lines=[ReturnLineRead.model_validate(line) for line in lines],
    )
