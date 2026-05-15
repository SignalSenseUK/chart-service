from __future__ import annotations

import pytest

from app.domain.services.indicator_service import (
    compute_ema,
    compute_indicator,
    compute_sma,
)


def _bars(closes):
    return [{"time": f"2026-05-{i + 1:02d}", "close": c} for i, c in enumerate(closes)]


def test_sma_known_values() -> None:
    bars = _bars([1, 2, 3, 4, 5])
    out = compute_sma(bars, 3)
    assert [round(p["value"], 4) for p in out] == [2.0, 3.0, 4.0]
    assert [p["time"] for p in out] == ["2026-05-03", "2026-05-04", "2026-05-05"]


def test_ema_known_values() -> None:
    bars = _bars([1, 2, 3, 4, 5])
    out = compute_ema(bars, 3)
    # SMA seed = 2.0; multiplier = 2/4 = 0.5
    # i=3: (4-2)*0.5 + 2 = 3.0
    # i=4: (5-3)*0.5 + 3 = 4.0
    assert [round(p["value"], 4) for p in out] == [2.0, 3.0, 4.0]


def test_sma_too_short_returns_empty() -> None:
    bars = _bars([1, 2])
    assert compute_sma(bars, 3) == []


def test_ema_too_short_returns_empty() -> None:
    bars = _bars([1, 2])
    assert compute_ema(bars, 3) == []


def test_sma_with_value_field() -> None:
    bars = [{"time": f"2026-05-0{i+1}", "value": v} for i, v in enumerate([10, 20, 30])]
    out = compute_sma(bars, 2, field="close")
    assert [p["value"] for p in out] == [15.0, 25.0]


def test_compute_indicator_dispatch_sma() -> None:
    bars = _bars([1, 2, 3])
    out = compute_indicator("sma", bars, {"length": 2})
    assert out == [
        {"time": "2026-05-02", "value": 1.5},
        {"time": "2026-05-03", "value": 2.5},
    ]


def test_compute_indicator_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown indicator"):
        compute_indicator("magic", _bars([1, 2, 3]), {"length": 2})
