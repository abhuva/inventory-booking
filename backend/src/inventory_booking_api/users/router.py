from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.core.security import get_current_user, verify_password
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.models import User
from inventory_booking_api.users.schemas import LoginRequest, UserRead
from inventory_booking_api.users.session_service import (
    create_user_session,
    get_user_by_email,
    revoke_session_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserRead)
async def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    """Authenticate a user and set an HTTP-only session cookie."""

    settings = get_settings()
    user = await get_user_by_email(session, str(payload.email))
    invalid_credentials = (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    )
    if invalid_credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _, raw_token = await create_user_session(session, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
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
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Return the authenticated user."""

    return current_user
