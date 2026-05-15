from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.api.errors import ChartValidationError
from app.db.models import Chart
from app.domain.schemas.normalized_payload import (
    NormalizedChartPayload,
    PayloadMeta,
    PayloadSeries,
)
from app.domain.services.indicator_service import compute_indicator
from app.domain.services.normalization_service import extract_volume_series
from app.domain.services.range_resolver import resolve_range
from app.providers.base import ProviderRequest
from app.providers.registry import get_adapter


_OHLC_TYPES = {"candlestick", "bar"}


def _strip_none(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    out = {k: v for k, v in d.items() if v is not None}
    return out or None


async def _fetch_series_data(
    source_kind: str,
    series_def: Dict[str, Any],
    definition: Dict[str, Any],
    inline: Dict[str, Any],
) -> tuple[List[Dict[str, Any]], List[str]]:
    instrument = definition.get("instrument") or {}
    source = definition.get("source") or {}
    range_cfg = definition.get("range")

    start_date = None
    end_date = None
    if range_cfg:
        try:
            start_date, end_date = resolve_range(range_cfg)
        except ValueError as exc:
            raise ChartValidationError(str(exc), code="invalid_range") from exc

    sid = series_def["id"]
    request = ProviderRequest(
        symbol=instrument.get("symbol", ""),
        asset_class=instrument.get("asset_class", ""),
        start_date=start_date,
        end_date=end_date,
        series_id=sid,
        data_format=series_def.get("data_format") or "ohlcv",
        provider_config=source.get("provider_config") or {},
        inline_series=inline.get(sid),
    )
    adapter = get_adapter(source_kind)
    result = await adapter.fetch_series(request)
    return result.data, result.warnings


async def build_payload(chart: Chart) -> tuple[NormalizedChartPayload, list[str]]:
    definition = chart.chart_definition or {}
    view = definition.get("view") or {}
    layout = definition.get("layout") or {}
    series_defs: List[Dict[str, Any]] = list(definition.get("series") or [])
    inline = chart.inline_series or {}

    meta = PayloadMeta(
        title=view.get("title"),
        theme=view.get("theme", "dark"),
        timezone=view.get("timezone", "UTC"),
    )
    layout_options: Dict[str, Any] = {}
    if layout:
        layout_options = {
            "autosize": layout.get("autosize", True),
            "pane_mode": layout.get("pane_mode", "single"),
            "legend": layout.get("legend", True),
        }

    normalized: Dict[str, List[Dict[str, Any]]] = {}
    out_series: List[PayloadSeries] = []
    warnings: list[str] = []

    for sd in series_defs:
        sid = sd["id"]
        if sd.get("indicator"):
            continue
        data, series_warnings = await _fetch_series_data(
            chart.source_kind, sd, definition, inline
        )
        warnings.extend(series_warnings)
        normalized[sid] = data
        out_series.append(
            PayloadSeries(
                id=sid,
                type=sd["type"],
                pane=int(sd.get("pane", 0)),
                data=data,
                style=_strip_none(sd.get("style")),
                label=sd.get("label"),
            )
        )

    for sd in series_defs:
        if not sd.get("indicator"):
            continue
        cfg = sd["indicator"]
        source_id = cfg["source_series"]
        if source_id not in normalized:
            raise ChartValidationError(
                f"indicator series '{sd['id']}' references unknown source '{source_id}'",
                code="invalid_indicator_source",
            )
        bars = normalized[source_id]
        try:
            data = compute_indicator(cfg["name"], bars, cfg)
        except ValueError as exc:
            raise ChartValidationError(str(exc), code="invalid_indicator_config") from exc
        out_series.append(
            PayloadSeries(
                id=sd["id"],
                type=sd["type"],
                pane=int(sd.get("pane", 0)),
                data=data,
                style=_strip_none(sd.get("style")),
                label=sd.get("label"),
            )
        )

    for sd in series_defs:
        if sd["type"] in _OHLC_TYPES and sd["id"] in normalized:
            bars = normalized[sd["id"]]
            if bars and "volume" in bars[0]:
                vol = extract_volume_series(bars, sd["id"], pane=1)
                out_series.append(
                    PayloadSeries(
                        id=vol["id"],
                        type=vol["type"],
                        pane=vol["pane"],
                        data=vol["data"],
                        label=vol.get("label"),
                    )
                )
                break

    return NormalizedChartPayload(meta=meta, layout_options=layout_options, series=out_series), warnings
