from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import inventory_booking_api.models  # noqa: F401
from inventory_booking_api.audit.router import router as audit_router
from inventory_booking_api.bookings.router import router as booking_router
from inventory_booking_api.checkouts.router import router as checkout_router
from inventory_booking_api.core.csrf import CsrfProtectionMiddleware
from inventory_booking_api.core.database import get_session
from inventory_booking_api.inventory.asset_router import asset_router, stock_router
from inventory_booking_api.inventory.category_router import router as category_router
from inventory_booking_api.locations.router import router as location_router
from inventory_booking_api.returns.router import router as return_router
from inventory_booking_api.settings import get_settings
from inventory_booking_api.users.router import router as auth_router
from inventory_booking_api.users.user_router import router as user_router

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(CsrfProtectionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(audit_router)
app.include_router(category_router)
app.include_router(location_router)
app.include_router(asset_router)
app.include_router(stock_router)
app.include_router(booking_router)
app.include_router(checkout_router)
app.include_router(return_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return service health for local checks and container probes."""

    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@app.get("/health/database", tags=["system"])
async def database_health(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Return database connectivity health."""

    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
