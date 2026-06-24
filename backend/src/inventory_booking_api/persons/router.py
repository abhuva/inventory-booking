from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.errors import raise_not_found
from inventory_booking_api.core.security import get_current_user
from inventory_booking_api.persons.schemas import PersonCreate, PersonRead, PersonUpdate
from inventory_booking_api.persons.service import (
    create_person,
    delete_person,
    get_person,
    list_persons,
    update_person,
)
from inventory_booking_api.users.models import User

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonRead])
async def list_person_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PersonRead]:
    return await list_persons(session)


@router.post("", response_model=PersonRead)
async def create_person_endpoint(
    payload: PersonCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PersonRead:
    return await create_person(session, payload, current_user)


@router.get("/{person_id}", response_model=PersonRead)
async def get_person_endpoint(
    person_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PersonRead:
    person = await get_person(session, person_id)
    if person is None:
        raise_not_found("Person")
    return person


@router.patch("/{person_id}", response_model=PersonRead)
async def update_person_endpoint(
    person_id: UUID,
    payload: PersonUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PersonRead:
    person = await get_person(session, person_id)
    if person is None:
        raise_not_found("Person")
    return await update_person(session, person, payload, current_user)


@router.delete("/{person_id}", status_code=204)
async def delete_person_endpoint(
    person_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    person = await get_person(session, person_id)
    if person is None:
        raise_not_found("Person")
    await delete_person(session, person, current_user)
    return Response(status_code=204)
