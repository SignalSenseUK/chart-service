from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import db_session
from app.core.config import Settings, get_settings
from app.db.models import Chart
from app.domain.schemas.chart_request import ChartCreateRequest, SourceKind
from app.domain.schemas.chart_response import (
    ChartCreateResponse,
    ChartListResponse,
    ChartSummary,
)
from app.domain.schemas.normalized_payload import ChartGetResponse
from app.domain.services import chart_service, render_payload_service

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


@router.get("", response_model=ChartListResponse)
async def list_charts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source_kind: Optional[SourceKind] = Query(None),
    db: AsyncSession = Depends(db_session),
) -> ChartListResponse:
    items, total = await chart_service.list_charts(
        db, page=page, limit=limit, source_kind=source_kind
    )
    return ChartListResponse(
        charts=[
            ChartSummary(
                id=c.id,
                title=c.title,
                source_kind=c.source_kind,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{chart_id}", response_model=ChartGetResponse)
async def get_chart(
    chart_id: str,
    db: AsyncSession = Depends(db_session),
) -> ChartGetResponse:
    chart = await chart_service.get_chart(db, chart_id)
    payload = await render_payload_service.build_payload(chart)
    await chart_service.touch_rendered(db, chart)
    instrument = (chart.chart_definition or {}).get("instrument", {}) or {}
    return ChartGetResponse(
        id=chart.id,
        title=chart.title,
        source_kind=chart.source_kind,
        instrument=instrument,
        payload=payload,
    )


@router.put("/{chart_id}", response_model=ChartCreateResponse)
async def update_chart(
    chart_id: str,
    request: ChartCreateRequest,
    db: AsyncSession = Depends(db_session),
    settings: Settings = Depends(get_settings),
) -> ChartCreateResponse:
    chart = await chart_service.update_chart(db, chart_id, request)
    return _build_create_response(chart, settings)


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(
    chart_id: str,
    db: AsyncSession = Depends(db_session),
) -> Response:
    await chart_service.delete_chart(db, chart_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
