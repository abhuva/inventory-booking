from secrets import token_urlsafe
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import get_current_user, verify_password
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User
from inventory_booking_api.users.schemas import CurrentUserUpdate, LoginRequest, UserRead
from inventory_booking_api.users.service import update_current_user
from inventory_booking_api.users.session_service import (
    create_user_session,
    get_user_by_email,
    revoke_session_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_failed_login_attempts: dict[tuple[str, str], list[float]] = {}


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host


def _is_login_rate_limited(request: Request, email: str) -> bool:
    settings = get_settings()
    now = monotonic()
    key = (_client_ip(request), email.lower())
    window_start = now - settings.login_rate_limit_window_seconds
    attempts = [
        attempt for attempt in _failed_login_attempts.get(key, []) if attempt >= window_start
    ]
    _failed_login_attempts[key] = attempts
    return len(attempts) >= settings.login_rate_limit_attempts


def _record_failed_login(request: Request, email: str) -> None:
    key = (_client_ip(request), email.lower())
    _failed_login_attempts.setdefault(key, []).append(monotonic())


def _clear_failed_logins(request: Request, email: str) -> None:
    _failed_login_attempts.pop((_client_ip(request), email.lower()), None)


@router.post("/login", response_model=UserRead)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    """Authenticate a user and set HTTP-only session plus CSRF cookies."""

    settings = get_settings()
    normalized_email = str(payload.email).lower()
    if _is_login_rate_limited(request, normalized_email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )

    user = await get_user_by_email(session, str(payload.email))
    invalid_credentials = (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    )
    if invalid_credentials:
        _record_failed_login(request, normalized_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _clear_failed_logins(request, normalized_email)
    _, raw_token = await create_user_session(session, user)
    csrf_token = token_urlsafe(32)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.session_max_age_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Revoke the current session cookie if present."""

    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token is not None:
        await revoke_session_token(session, raw_token)
    response.delete_cookie(key=settings.session_cookie_name, samesite="lax")
    response.delete_cookie(key=settings.csrf_cookie_name, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Return the authenticated user."""

    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: CurrentUserUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Update the authenticated user's editable account fields."""

    settings = get_settings()
    current_session_token = request.cookies.get(settings.session_cookie_name)
    return await update_current_user(session, current_user, payload, current_session_token)
