from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User
from inventory_booking_api.users.session_models import UserSession


def hash_session_token(token: str) -> str:
    """Hash a raw session token for storage and lookup."""

    return sha256(token.encode("utf-8")).hexdigest()


async def create_user_session(session: AsyncSession, user: User) -> tuple[UserSession, str]:
    """Create a server-side session and return it with the raw cookie token."""

    settings = get_settings()
    raw_token = token_urlsafe(48)
    user_session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_max_age_seconds),
    )
    session.add(user_session)
    await session.commit()
    await session.refresh(user_session)
    return user_session, raw_token


async def get_user_by_session_token(session: AsyncSession, raw_token: str) -> User | None:
    """Resolve an active session token to a user."""

    result = await session.execute(
        select(UserSession).where(UserSession.token_hash == hash_session_token(raw_token))
    )
    user_session = result.scalar_one_or_none()
    if user_session is None or not user_session.is_active:
        return None

    user = await session.get(User, user_session.user_id)
    if user is None or not user.is_active:
        return None
    return user


async def revoke_session_token(session: AsyncSession, raw_token: str) -> None:
    """Revoke a session token if it exists."""

    result = await session.execute(
        select(UserSession).where(UserSession.token_hash == hash_session_token(raw_token))
    )
    user_session = result.scalar_one_or_none()
    if user_session is None:
        return

    user_session.revoked_at = datetime.now(UTC)
    await session.commit()


async def revoke_user_sessions(
    session: AsyncSession,
    user_id: UUID,
    except_raw_token: str | None = None,
) -> None:
    """Revoke active sessions for a user, optionally keeping the current browser session."""

    except_token_hash = hash_session_token(except_raw_token) if except_raw_token else None
    result = await session.execute(select(UserSession).where(UserSession.user_id == user_id))
    now = datetime.now(UTC)
    for user_session in result.scalars().all():
        if not user_session.is_active or user_session.token_hash == except_token_hash:
            continue
        user_session.revoked_at = now


async def delete_inactive_user_sessions(session: AsyncSession) -> int:
    """Delete revoked or expired sessions and return the number of removed rows."""

    result = await session.execute(
        delete(UserSession).where(
            (UserSession.revoked_at.is_not(None)) | (UserSession.expires_at <= datetime.now(UTC))
        )
    )
    await session.commit()
    return int(result.rowcount or 0)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Find a user by normalized email."""

    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    """Find a user by id."""

    return await session.get(User, user_id)
