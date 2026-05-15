from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session
from app.api.errors import ChartValidationError
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.services import chart_service
from app.exports.browser_exporter import (
    BrowserExporter,
    ExportConnectionError,
    ExportTimeoutError,
)

router = APIRouter(prefix="/api/charts", tags=["exports"])
logger = get_logger("app.api.exports")


def _internal_render_url(settings: Settings, chart_id: str) -> str:
    base = settings.BASE_URL.rstrip("/")
    return f"{base}/charts/{chart_id}?export=true"


@router.get("/{chart_id}/png")
async def export_png(
    chart_id: str,
    width: int = Query(..., ge=1),
    height: int = Query(..., ge=1),
    db: AsyncSession = Depends(db_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    if not (settings.PNG_MIN_WIDTH <= width <= settings.PNG_MAX_WIDTH):
        raise ChartValidationError(
            f"width must be between {settings.PNG_MIN_WIDTH} and {settings.PNG_MAX_WIDTH}",
            code="invalid_width",
        )
    if not (settings.PNG_MIN_HEIGHT <= height <= settings.PNG_MAX_HEIGHT):
        raise ChartValidationError(
            f"height must be between {settings.PNG_MIN_HEIGHT} and {settings.PNG_MAX_HEIGHT}",
            code="invalid_height",
        )

    chart = await chart_service.get_chart(db, chart_id)

    exporter = BrowserExporter(
        ws_endpoint=settings.EXPORT_BROWSER_WS_ENDPOINT,
        timeout_ms=settings.EXPORT_TIMEOUT_MS,
    )

    started = time.monotonic()
    try:
        png_bytes = await exporter.capture_png(
            _internal_render_url(settings, chart.id),
            width=width,
            height=height,
        )
    except ExportTimeoutError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "export.timeout",
            chart_id=chart.id,
            width=width,
            height=height,
            duration_ms=duration_ms,
        )
        return Response(
            status_code=504,
            content=f'{{"error":{{"code":"export_timeout","message":"{exc}"}}}}',
            media_type="application/json",
        )
    except ExportConnectionError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "export.connection_failed",
            chart_id=chart.id,
            error=str(exc),
            duration_ms=duration_ms,
        )
        return Response(
            status_code=502,
            content=f'{{"error":{{"code":"export_unavailable","message":"{exc}"}}}}',
            media_type="application/json",
        )

    duration_ms = int((time.monotonic() - started) * 1000)
    chart.last_exported_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        "export.success",
        chart_id=chart.id,
        width=width,
        height=height,
        duration_ms=duration_ms,
        bytes=len(png_bytes),
    )

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
