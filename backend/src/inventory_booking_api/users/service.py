from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.audit.enums import AuditAction
from inventory_booking_api.audit.service import write_audit_log
from inventory_booking_api.core.security import hash_password
from inventory_booking_api.users.models import User
from inventory_booking_api.users.schemas import UserCreate, UserUpdate


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.display_name))
    return list(result.scalars().all())


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def create_user(session: AsyncSession, payload: UserCreate, actor: User) -> User:
    existing = await _get_user_by_email(session, str(payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    user = User(
        email=str(payload.email).lower(),
        display_name=payload.display_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    session.add(user)
    await session.flush()
    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"Created user {user.email}",
    )
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate, actor: User) -> User:
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"] is not None:
        email = str(updates["email"]).lower()
        existing = await _get_user_by_email(session, email)
        if existing is not None and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already exists."
            )
        user.email = email

    if "display_name" in updates:
        user.display_name = updates["display_name"]
    if "password" in updates and updates["password"] is not None:
        user.password_hash = hash_password(updates["password"])
    if "role" in updates:
        user.role = updates["role"]
    if "is_active" in updates:
        user.is_active = updates["is_active"]

    await write_audit_log(
        session,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="user",
        entity_id=user.id,
        summary=f"Updated user {user.email}",
    )
    await session.commit()
    await session.refresh(user)
    return user


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
