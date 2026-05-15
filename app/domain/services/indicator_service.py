from __future__ import annotations

from typing import Any, Dict, List


def _series_value(bar: Dict[str, Any], field: str) -> float:
    if field in bar:
        return float(bar[field])
    if "value" in bar:
        return float(bar["value"])
    raise ValueError(
        f"bar at {bar.get('time')!r} is missing required field '{field}'"
    )


def compute_sma(bars: List[Dict[str, Any]], length: int, field: str = "close") -> List[Dict[str, Any]]:
    if length < 1:
        raise ValueError("length must be >= 1")
    if len(bars) < length:
        return []

    values = [_series_value(b, field) for b in bars]
    window_sum = sum(values[:length])
    output: List[Dict[str, Any]] = [
        {"time": bars[length - 1]["time"], "value": window_sum / length}
    ]
    for i in range(length, len(values)):
        window_sum += values[i] - values[i - length]
        output.append({"time": bars[i]["time"], "value": window_sum / length})
    return output


def compute_ema(bars: List[Dict[str, Any]], length: int, field: str = "close") -> List[Dict[str, Any]]:
    if length < 1:
        raise ValueError("length must be >= 1")
    if len(bars) < length:
        return []

    values = [_series_value(b, field) for b in bars]
    multiplier = 2 / (length + 1)

    seed = sum(values[:length]) / length
    output: List[Dict[str, Any]] = [
        {"time": bars[length - 1]["time"], "value": seed}
    ]
    ema_prev = seed
    for i in range(length, len(values)):
        ema_prev = (values[i] - ema_prev) * multiplier + ema_prev
        output.append({"time": bars[i]["time"], "value": ema_prev})
    return output


def compute_indicator(
    name: str, bars: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    field = config.get("field", "close")
    if name == "sma":
        length = config["length"]
        return compute_sma(bars, int(length), field=field)
    if name == "ema":
        length = config["length"]
        return compute_ema(bars, int(length), field=field)
    raise ValueError(f"unknown indicator '{name}'")
