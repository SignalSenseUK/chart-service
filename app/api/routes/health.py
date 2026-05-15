from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db

router = APIRouter(tags=["health"])
logger = get_logger("app.health")

_VERSION = "1.0.0"


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    except Exception as exc:
        logger.warning("health.db_unreachable", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "disconnected",
                "version": _VERSION,
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "database": "connected",
            "version": _VERSION,
        },
    )
