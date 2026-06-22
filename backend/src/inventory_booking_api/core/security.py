from typing import Annotated

from fastapi import Header, HTTPException, status

from inventory_booking_api.settings import get_settings


async def require_internal_api_token(
    token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    """Require the temporary internal API token for mutating endpoints."""

    settings = get_settings()
    if token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token.",
        )
