from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import (
    ChartDeletedError,
    ChartNotFoundError,
    ChartValidationError,
    ProviderError,
)
from app.core.ids import generate_chart_id
from app.db.models import Chart
from app.domain.schemas.chart_request import ChartCreateRequest
from app.domain.services.range_resolver import resolve_range
from app.providers.base import ProviderRequest
from app.providers.registry import get_adapter


def _split_definition(
    request: ChartCreateRequest,
) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
    """Split a chart create request into the durable definition and inline series.

    Inline data is removed from each series entry in the definition copy so the
    persisted definition stays compact; the data is stored in ``inline_series``
    keyed by series id.
    """
    payload = request.model_dump(mode="json")
    inline_series: dict[str, Any] = {}
    for series in payload["series"]:
        if series.get("data") is not None:
            inline_series[series["id"]] = {
                "data_format": series.get("data_format"),
                "data": series.pop("data"),
            }
    return payload, (inline_series or None)


async def _validate_provider_fetch(request: ChartCreateRequest) -> None:
    if request.source.kind == "direct":
        return
    if request.range is None:
        raise ChartValidationError(
            "provider-backed charts require a 'range'",
            code="missing_range",
        )
    range_cfg = request.range.model_dump(mode="json")
    try:
        start_date, end_date = resolve_range(range_cfg)
    except ValueError as exc:
        raise ChartValidationError(str(exc), code="invalid_range") from exc

    adapter = get_adapter(request.source.kind)
    provider_request = ProviderRequest(
        symbol=request.instrument.symbol,
        asset_class=request.instrument.asset_class,
        start_date=start_date,
        end_date=end_date,
        series_id="__validation__",
        data_format="ohlcv",
        provider_config=(request.source.provider_config or {}),
    )
    try:
        result = await adapter.fetch_series(provider_request)
    except (ChartValidationError, ProviderError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"provider validation failed: {exc}") from exc

    if not result.data:
        raise ChartValidationError(
            "provider returned no data for the requested symbol and range",
            code="provider_empty",
        )


async def create_chart(db: AsyncSession, request: ChartCreateRequest) -> Chart:
    await _validate_provider_fetch(request)
    definition, inline_series = _split_definition(request)
    chart = Chart(
        id=generate_chart_id(),
        source_kind=request.source.kind,
        title=request.view.title,
        chart_definition=definition,
        inline_series=inline_series,
    )
    db.add(chart)
    await db.commit()
    await db.refresh(chart)
    return chart


async def get_chart(
    db: AsyncSession, chart_id: str, *, include_deleted: bool = False
) -> Chart:
    chart = await db.get(Chart, chart_id)
    if chart is None:
        raise ChartNotFoundError(f"Chart '{chart_id}' not found")
    if not include_deleted and chart.deleted_at is not None:
        raise ChartDeletedError(f"Chart '{chart_id}' has been deleted")
    return chart


async def update_chart(
    db: AsyncSession, chart_id: str, request: ChartCreateRequest
) -> Chart:
    chart = await get_chart(db, chart_id)
    if request.source.kind != chart.source_kind:
        from app.api.errors import ChartValidationError

        raise ChartValidationError(
            f"source_kind cannot be changed from '{chart.source_kind}' to "
            f"'{request.source.kind}'",
            code="invalid_source_kind_change",
        )
    definition, inline_series = _split_definition(request)
    chart.chart_definition = definition
    chart.inline_series = inline_series
    chart.title = request.view.title
    chart.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(chart)
    return chart


async def delete_chart(db: AsyncSession, chart_id: str) -> None:
    chart = await get_chart(db, chart_id, include_deleted=True)
    if chart.deleted_at is not None:
        raise ChartDeletedError(f"Chart '{chart_id}' is already deleted")
    chart.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_charts(
    db: AsyncSession,
    *,
    page: int = 1,
    limit: int = 20,
    source_kind: Optional[str] = None,
) -> tuple[Sequence[Chart], int]:
    stmt = select(Chart).where(Chart.deleted_at.is_(None))
    count_stmt = select(func.count(Chart.id)).where(Chart.deleted_at.is_(None))
    if source_kind is not None:
        stmt = stmt.where(Chart.source_kind == source_kind)
        count_stmt = count_stmt.where(Chart.source_kind == source_kind)
    stmt = stmt.order_by(Chart.created_at.desc()).offset((page - 1) * limit).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return items, total


async def touch_rendered(db: AsyncSession, chart: Chart) -> None:
    chart.last_rendered_at = datetime.now(timezone.utc)
    await db.commit()
