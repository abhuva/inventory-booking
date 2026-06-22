from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_booking_api.core.database import get_session
from inventory_booking_api.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return service health for local checks and container probes."""

    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@app.get("/health/database", tags=["system"])
async def database_health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Return database connectivity health."""

    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
