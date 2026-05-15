from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DATABASE_URL: str = Field(
        default="",
        description="Async SQLAlchemy database URL (asyncpg driver).",
    )
    BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public base URL used when constructing chart URLs.",
    )
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    EODHD_API_KEY: Optional[str] = None
    EODHD_TIMEOUT_MS: int = 30000

    IB_HOST: Optional[str] = None
    IB_PORT: Optional[int] = None
    IB_CLIENT_ID: Optional[int] = None
    IB_TIMEOUT_MS: int = 30000

    EXPORT_BROWSER_WS_ENDPOINT: Optional[str] = None
    EXPORT_TIMEOUT_MS: int = 15000

    PNG_MIN_WIDTH: int = 320
    PNG_MIN_HEIGHT: int = 200
    PNG_MAX_WIDTH: int = 2400
    PNG_MAX_HEIGHT: int = 1600

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
