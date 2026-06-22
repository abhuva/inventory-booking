from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "Inventory Booking API"
    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://inventory:inventory@127.0.0.1:5432/inventory_booking"
    internal_api_token: str = "local-dev-token"
    cors_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        description="Comma-separated list of allowed browser origins.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a normalized list."""

        return [
            origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings."""

    return Settings()
