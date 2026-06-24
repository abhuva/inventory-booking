from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.baskets.models import Basket
from inventory_booking_api.bookings.models import Booking
from inventory_booking_api.locations.models import Location
from inventory_booking_api.persons.models import Person
from inventory_booking_api.persons.schemas import PersonCreate, PersonUpdate
from inventory_booking_api.users.models import User


async def list_persons(session: AsyncSession) -> list[Person]:
    result = await session.execute(select(Person).order_by(Person.display_name))
    return list(result.scalars().all())


async def get_person(session: AsyncSession, person_id: UUID) -> Person | None:
    return await session.get(Person, person_id)


async def create_person(session: AsyncSession, payload: PersonCreate, actor: User) -> Person:
    await validate_user_link(session, payload.user_id)
    person = Person(**normalized_payload(payload.model_dump()))
    session.add(person)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="person",
        entity_id=person.id,
        summary=f"Created person {person.display_name}",
    )
    await session.commit()
    await session.refresh(person)
    return person


async def update_person(
    session: AsyncSession,
    person: Person,
    payload: PersonUpdate,
    actor: User,
) -> Person:
    updates = normalized_payload(payload.model_dump(exclude_unset=True))
    if "user_id" in updates:
        await validate_user_link(session, updates["user_id"], current_person_id=person.id)
    for field, value in updates.items():
        setattr(person, field, value)
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="person",
        entity_id=person.id,
        summary=f"Updated person {person.display_name}",
    )
    await session.commit()
    await session.refresh(person)
    return person


async def delete_person(session: AsyncSession, person: Person, actor: User) -> None:
    summary = await person_reference_counts(session, person.id)
    await session.execute(
        update(Location)
        .where(Location.responsible_person_id == person.id)
        .values(responsible_person_id=None)
    )
    await session.execute(
        update(Booking).where(Booking.person_id == person.id).values(person_id=None)
    )
    await session.execute(
        update(Basket).where(Basket.person_id == person.id).values(person_id=None)
    )
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="person",
        entity_id=person.id,
        summary=f"Deleted person {person.display_name}",
        details=summary,
    )
    await session.delete(person)
    await session.commit()


async def person_reference_counts(session: AsyncSession, person_id: UUID) -> dict[str, int]:
    return {
        "bookings": await count_where(
            session, select(func.count(Booking.id)).where(Booking.person_id == person_id)
        ),
        "baskets": await count_where(
            session, select(func.count(Basket.id)).where(Basket.person_id == person_id)
        ),
        "locations": await count_where(
            session,
            select(func.count(Location.id)).where(Location.responsible_person_id == person_id),
        ),
    }


async def validate_user_link(
    session: AsyncSession,
    user_id: UUID | None,
    current_person_id: UUID | None = None,
) -> None:
    if user_id is None:
        return
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not exist.")
    result = await session.execute(select(Person).where(Person.user_id == user_id))
    existing = result.scalar_one_or_none()
    if existing is not None and existing.id != current_person_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already linked to another person.",
        )


def normalized_payload(values: dict) -> dict:
    if "email" in values and values["email"] is not None:
        values["email"] = str(values["email"]).lower()
    for key in ("phone", "notes"):
        if key in values and values[key] == "":
            values[key] = None
    return values


async def count_where(session: AsyncSession, statement) -> int:
    return int((await session.execute(statement)).scalar_one())
