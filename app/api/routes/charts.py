from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session
from app.core.config import Settings, get_settings
from app.db.models import Chart
from app.domain.schemas.chart_request import ChartCreateRequest
from app.domain.schemas.chart_response import ChartCreateResponse
from app.domain.services import chart_service

router = APIRouter(prefix="/api/charts", tags=["charts"])


def _build_create_response(chart: Chart, settings: Settings) -> ChartCreateResponse:
    base = settings.BASE_URL.rstrip("/")
    return ChartCreateResponse(
        id=chart.id,
        view_url=f"{base}/charts/{chart.id}",
        embed_url=f"{base}/embed/{chart.id}",
        api_url=f"{base}/api/charts/{chart.id}",
    )


@router.post("", response_model=ChartCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(
    request: ChartCreateRequest,
    db: AsyncSession = Depends(db_session),
    settings: Settings = Depends(get_settings),
) -> ChartCreateResponse:
    chart = await chart_service.create_chart(db, request)
    return _build_create_response(chart, settings)


@router.get("/{chart_id}")
async def get_chart(
    chart_id: str,
    db: AsyncSession = Depends(db_session),
) -> dict:
    chart = await chart_service.get_chart(db, chart_id)
    return {
        "id": chart.id,
        "title": chart.title,
        "source_kind": chart.source_kind,
        "chart_definition": chart.chart_definition,
        "inline_series": chart.inline_series,
    }
