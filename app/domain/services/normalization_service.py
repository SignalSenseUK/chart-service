from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ensure_date(value: Any) -> str:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValueError(f"invalid time value '{value}'; expected YYYY-MM-DD")
    return value


def _to_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"field '{field}' must be numeric, got {value!r}") from exc


def normalize_series(
    raw_data: Iterable[Dict[str, Any]], data_format: str
) -> List[Dict[str, Any]]:
    if data_format not in ("ohlcv", "ohlc", "value"):
        raise ValueError(f"unsupported data_format '{data_format}'")

    seen_dates: set[str] = set()
    canonical: List[Dict[str, Any]] = []

    for row in raw_data:
        if not isinstance(row, dict):
            raise ValueError("each data point must be a JSON object")
        time = _ensure_date(row.get("time"))
        if time in seen_dates:
            raise ValueError(f"duplicate date '{time}' within series")
        seen_dates.add(time)

        if data_format == "ohlcv":
            canonical.append(
                {
                    "time": time,
                    "open": _to_float(row.get("open"), "open"),
                    "high": _to_float(row.get("high"), "high"),
                    "low": _to_float(row.get("low"), "low"),
                    "close": _to_float(row.get("close"), "close"),
                    "volume": _to_float(row.get("volume"), "volume"),
                }
            )
        elif data_format == "ohlc":
            canonical.append(
                {
                    "time": time,
                    "open": _to_float(row.get("open"), "open"),
                    "high": _to_float(row.get("high"), "high"),
                    "low": _to_float(row.get("low"), "low"),
                    "close": _to_float(row.get("close"), "close"),
                }
            )
        else:
            canonical.append(
                {
                    "time": time,
                    "value": _to_float(row.get("value"), "value"),
                }
            )

    canonical.sort(key=lambda r: r["time"])
    return canonical


_VOL_UP_COLOR = "#26a69a"
_VOL_DOWN_COLOR = "#ef5350"


def extract_volume_series(
    ohlcv_data: List[Dict[str, Any]],
    source_series_id: str,
    *,
    pane: int = 1,
) -> Dict[str, Any]:
    points: List[Dict[str, Any]] = []
    for bar in ohlcv_data:
        if "volume" not in bar:
            continue
        is_up = bar["close"] >= bar["open"]
        points.append(
            {
                "time": bar["time"],
                "value": bar["volume"],
                "color": _VOL_UP_COLOR if is_up else _VOL_DOWN_COLOR,
            }
        )
    return {
        "id": f"{source_series_id}__volume",
        "type": "histogram",
        "pane": pane,
        "data": points,
        "label": "Volume",
    }
