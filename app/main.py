from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.routes import health as health_routes
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger = get_logger("app.lifespan")
    logger.info("application.startup", app_env=settings.APP_ENV)
    if settings.DATABASE_URL:
        await init_db()
    try:
        yield
    finally:
        if settings.DATABASE_URL:
            await close_db()
        logger.info("application.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Chart Service",
        version="1.0.0",
        description="Self-hosted chart rendering service.",
        lifespan=lifespan,
    )

    app.include_router(health_routes.router)

    return app
