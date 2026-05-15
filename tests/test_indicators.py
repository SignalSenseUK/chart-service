from __future__ import annotations

import pytest

from app.domain.services.indicator_service import (
    compute_bollinger,
    compute_ema,
    compute_indicator,
    compute_sma,
    compute_vwap,
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


def _ohlcv_bars(rows):
    out = []
    for i, (h, l, c, v) in enumerate(rows):
        out.append(
            {
                "time": f"2026-05-{i + 1:02d}",
                "open": c,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
            }
        )
    return out


def test_vwap_cumulative() -> None:
    bars = _ohlcv_bars(
        [
            (12, 10, 11, 100),
            (14, 12, 13, 200),
            (16, 14, 15, 300),
        ]
    )
    out = compute_vwap(bars)
    typicals = [(12 + 10 + 11) / 3, (14 + 12 + 13) / 3, (16 + 14 + 15) / 3]
    pv = [t * v for t, v in zip(typicals, [100, 200, 300])]
    expected = [
        pv[0] / 100,
        (pv[0] + pv[1]) / 300,
        (pv[0] + pv[1] + pv[2]) / 600,
    ]
    for got, want in zip(out, expected):
        assert got["value"] == pytest.approx(want)


def test_vwap_missing_volume_raises() -> None:
    bars = [{"time": "2026-05-01", "high": 12, "low": 10, "close": 11}]
    with pytest.raises(ValueError, match="VWAP requires"):
        compute_vwap(bars)


def test_bollinger_middle_matches_sma() -> None:
    bars = _bars([1, 2, 3, 4, 5])
    middle = compute_bollinger(bars, 3, band="middle")
    sma = compute_sma(bars, 3)
    assert middle == sma


def test_bollinger_upper_lower_known() -> None:
    bars = _bars([2, 4, 4, 4, 5, 5, 7, 9])
    upper = compute_bollinger(bars, 4, stddev=2.0, band="upper")
    lower = compute_bollinger(bars, 4, stddev=2.0, band="lower")
    # Last window = [5, 5, 7, 9]; mean = 6.5; variance = ((1.5^2+1.5^2+0.5^2+2.5^2)/4) = 2.75; sd = sqrt(2.75)
    import math as _m
    sd = _m.sqrt(2.75)
    assert upper[-1]["value"] == pytest.approx(6.5 + 2 * sd)
    assert lower[-1]["value"] == pytest.approx(6.5 - 2 * sd)


def test_compute_indicator_dispatches_vwap_and_bollinger() -> None:
    bars = _ohlcv_bars([(12, 10, 11, 100), (14, 12, 13, 200)])
    vwap = compute_indicator("vwap", bars, {})
    assert len(vwap) == 2

    boll = compute_indicator(
        "bollinger", _bars([1, 2, 3, 4, 5]), {"length": 3, "stddev": 1.0, "band": "middle"}
    )
    assert [round(p["value"], 4) for p in boll] == [2.0, 3.0, 4.0]
