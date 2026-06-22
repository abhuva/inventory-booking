from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
