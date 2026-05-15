from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session
from app.api.errors import ChartDeletedError, ChartNotFoundError
from app.core.config import Settings, get_settings
from app.domain.services import chart_service

router = APIRouter(tags=["pages"])

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "web" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _api_base(settings: Settings, request: Request) -> str:
    if settings.BASE_URL:
        return settings.BASE_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


async def _render_chart_page(
    request: Request,
    chart_id: str,
    template_name: str,
    body_class: str,
    db: AsyncSession,
    settings: Settings,
    extra_headers: dict[str, str] | None = None,
) -> HTMLResponse:
    try:
        chart = await chart_service.get_chart(db, chart_id)
    except ChartNotFoundError:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart not found", "message": "Chart not found."},
            status_code=404,
        )
    except ChartDeletedError:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"title": "Chart removed", "message": "This chart has been removed."},
            status_code=410,
        )

    context = {
        "title": chart.title or f"Chart {chart.id}",
        "initial_title": chart.title or "",
        "chart_id_json": json.dumps(chart.id),
        "api_base_json": json.dumps(_api_base(settings, request)),
        "body_class": body_class,
    }
    response = templates.TemplateResponse(request, template_name, context)
    if extra_headers:
        for k, v in extra_headers.items():
            response.headers[k] = v
    return response


@router.get("/charts/{chart_id}", response_class=HTMLResponse)
async def hosted_chart_page(
    chart_id: str,
    request: Request,
    db: AsyncSession = Depends(db_session),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    return await _render_chart_page(
        request,
        chart_id,
        "chart.html",
        body_class="hosted",
        db=db,
        settings=settings,
    )


@router.get("/embed/{chart_id}", response_class=HTMLResponse)
async def embed_chart_page(
    chart_id: str,
    request: Request,
    db: AsyncSession = Depends(db_session),
    settings: Settings = Depends(get_settings),
) -> HTMLResponse:
    return await _render_chart_page(
        request,
        chart_id,
        "embed.html",
        body_class="embed",
        db=db,
        settings=settings,
        extra_headers={"Content-Security-Policy": "frame-ancestors *"},
    )
