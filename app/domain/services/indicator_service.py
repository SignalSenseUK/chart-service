from __future__ import annotations

import math
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


def compute_vwap(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    required = ("high", "low", "close", "volume")
    output: List[Dict[str, Any]] = []
    cum_pv = 0.0
    cum_vol = 0.0
    for bar in bars:
        missing = [f for f in required if f not in bar]
        if missing:
            raise ValueError(
                f"VWAP requires fields {required}; missing {missing} at {bar.get('time')!r}"
            )
        typical = (float(bar["high"]) + float(bar["low"]) + float(bar["close"])) / 3.0
        volume = float(bar["volume"])
        cum_pv += typical * volume
        cum_vol += volume
        value = cum_pv / cum_vol if cum_vol > 0 else typical
        output.append({"time": bar["time"], "value": value})
    return output


def compute_bollinger(
    bars: List[Dict[str, Any]],
    length: int,
    stddev: float = 2.0,
    band: str = "middle",
    field: str = "close",
) -> List[Dict[str, Any]]:
    if length < 1:
        raise ValueError("length must be >= 1")
    if band not in ("upper", "middle", "lower"):
        raise ValueError(f"unknown band '{band}'")
    if len(bars) < length:
        return []

    values = [_series_value(b, field) for b in bars]
    output: List[Dict[str, Any]] = []
    for i in range(length - 1, len(values)):
        window = values[i - length + 1 : i + 1]
        mean = sum(window) / length
        if band == "middle":
            output.append({"time": bars[i]["time"], "value": mean})
            continue
        variance = sum((v - mean) ** 2 for v in window) / length
        sd = math.sqrt(variance)
        if band == "upper":
            output.append({"time": bars[i]["time"], "value": mean + stddev * sd})
        else:
            output.append({"time": bars[i]["time"], "value": mean - stddev * sd})
    return output


def compute_indicator(
    name: str, bars: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    field = config.get("field", "close")
    if name == "sma":
        return compute_sma(bars, int(config["length"]), field=field)
    if name == "ema":
        return compute_ema(bars, int(config["length"]), field=field)
    if name == "vwap":
        return compute_vwap(bars)
    if name == "bollinger":
        return compute_bollinger(
            bars,
            int(config["length"]),
            stddev=float(config.get("stddev", 2.0)),
            band=config.get("band", "middle"),
            field=field,
        )
    raise ValueError(f"unknown indicator '{name}'")
