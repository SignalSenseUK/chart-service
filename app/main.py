from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.errors import register_error_handlers
from app.api.routes import charts as charts_routes
from app.api.routes import health as health_routes
from app.api.routes import pages as page_routes
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

    ib_adapter = None
    if settings.IB_HOST and settings.IB_PORT and settings.IB_CLIENT_ID is not None:
        try:
            from app.providers.ib import IbAdapter  # noqa: PLC0415

            ib_adapter = IbAdapter.get_instance()
            await ib_adapter.connect()
            logger.info("application.ib_connected")
        except Exception as exc:  # noqa: BLE001
            logger.warning("application.ib_connect_failed", error=str(exc))

    try:
        yield
    finally:
        if ib_adapter is not None:
            try:
                await ib_adapter.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("application.ib_disconnect_failed", error=str(exc))
        if settings.DATABASE_URL:
            await close_db()
        logger.info("application.shutdown")


class ApiCORSMiddleware(BaseHTTPMiddleware):
    """Add CORS headers for /api/* routes only."""

    async def dispatch(self, request: Request, call_next):
        is_api = request.url.path.startswith("/api/")
        if is_api and request.method == "OPTIONS":
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": request.headers.get(
                        "access-control-request-headers", "*"
                    ),
                    "Access-Control-Max-Age": "600",
                },
            )
        response = await call_next(request)
        if is_api:
            response.headers.setdefault("Access-Control-Allow-Origin", "*")
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title="Chart Service",
        version="1.0.0",
        description="Self-hosted chart rendering service.",
        lifespan=lifespan,
    )

    app.add_middleware(ApiCORSMiddleware)

    register_error_handlers(app)
    app.include_router(health_routes.router)
    app.include_router(charts_routes.router)
    app.include_router(page_routes.router)

    static_dir = Path(__file__).resolve().parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
