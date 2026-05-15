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
from app.domain.services.normalization_service import (
    extract_volume_series,
    normalize_series,
)


_OHLC_TYPES = {"candlestick", "bar"}


def _strip_none(d: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    out = {k: v for k, v in d.items() if v is not None}
    return out or None


def build_payload_from_definition(
    definition: Dict[str, Any],
    inline_series: Optional[Dict[str, Any]],
) -> NormalizedChartPayload:
    view = definition.get("view") or {}
    layout = definition.get("layout") or {}
    series_defs: List[Dict[str, Any]] = list(definition.get("series") or [])

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
    inline = inline_series or {}

    for sd in series_defs:
        sid = sd["id"]
        if sd.get("indicator"):
            continue
        raw = inline.get(sid)
        if raw is None:
            normalized[sid] = []
            data: List[Dict[str, Any]] = []
        else:
            data = normalize_series(raw["data"], raw["data_format"])
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

    volume_pane = 1
    for sd in series_defs:
        if sd["type"] in _OHLC_TYPES and sd["id"] in normalized:
            bars = normalized[sd["id"]]
            if bars and "volume" in bars[0]:
                vol = extract_volume_series(bars, sd["id"], pane=volume_pane)
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

    return NormalizedChartPayload(meta=meta, layout_options=layout_options, series=out_series)


async def build_payload(chart: Chart) -> NormalizedChartPayload:
    return build_payload_from_definition(chart.chart_definition, chart.inline_series)
