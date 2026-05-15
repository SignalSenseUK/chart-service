from __future__ import annotations

import pytest

from app.domain.services.normalization_service import (
    extract_volume_series,
    normalize_series,
)


def test_ohlcv_normalization_sorts_and_coerces() -> None:
    raw = [
        {"time": "2026-05-02", "open": "2", "high": "3", "low": "1", "close": "2.5", "volume": "10"},
        {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
    ]
    out = normalize_series(raw, "ohlcv")
    assert [r["time"] for r in out] == ["2026-05-01", "2026-05-02"]
    assert all(isinstance(r["open"], float) for r in out)


def test_duplicate_date_rejected() -> None:
    raw = [
        {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
    ]
    with pytest.raises(ValueError, match="duplicate date"):
        normalize_series(raw, "ohlcv")


def test_invalid_time_format_rejected() -> None:
    raw = [{"time": "2026-05-01T12:00:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1}]
    with pytest.raises(ValueError, match="invalid time"):
        normalize_series(raw, "ohlcv")


def test_value_format() -> None:
    raw = [{"time": "2026-05-01", "value": "1.5"}]
    out = normalize_series(raw, "value")
    assert out == [{"time": "2026-05-01", "value": 1.5}]


def test_ohlc_format_omits_volume() -> None:
    raw = [{"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5}]
    out = normalize_series(raw, "ohlc")
    assert "volume" not in out[0]


def test_volume_extraction_colors() -> None:
    bars = [
        {"time": "2026-05-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
        {"time": "2026-05-02", "open": 103, "high": 104, "low": 100, "close": 101, "volume": 800},
    ]
    series = extract_volume_series(bars, "price")
    assert series["type"] == "histogram"
    assert series["id"] == "price__volume"
    assert series["data"][0]["color"] == "#26a69a"
    assert series["data"][1]["color"] == "#ef5350"


def test_unsupported_format_raises() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        normalize_series([], "bogus")


def test_non_numeric_field_rejected() -> None:
    raw = [{"time": "2026-05-01", "open": "abc", "high": 2, "low": 0.5, "close": 1.5, "volume": 1}]
    with pytest.raises(ValueError, match="must be numeric"):
        normalize_series(raw, "ohlcv")
