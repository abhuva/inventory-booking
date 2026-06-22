from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.enums import UserRole
from inventory_booking_api.users.models import User
from inventory_booking_api.users.session_service import get_user_by_session_token

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password for storage."""

    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password against a stored hash."""

    if not password_hash:
        return False
    return _password_hash.verify(password, password_hash)


async def require_internal_api_token(
    token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    """Require the legacy internal API token for bootstrap-only endpoints."""

    settings = get_settings()
    if token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token.",
        )


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    request: Request,
) -> User:
    """Resolve the current user from the session cookie."""

    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    user = await get_user_by_session_token(session, raw_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")
    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require an active admin user."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return current_user
