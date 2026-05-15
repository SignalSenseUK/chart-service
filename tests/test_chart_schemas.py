from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.schemas.chart_request import ChartCreateRequest


def _direct_payload(**overrides):
    payload = {
        "source": {"kind": "direct"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_direct_chart_minimum_valid() -> None:
    req = ChartCreateRequest.model_validate(_direct_payload())
    assert req.source.kind == "direct"
    assert req.series[0].data is not None
    assert req.view.theme == "dark"


def test_direct_chart_without_inline_data_rejected() -> None:
    payload = _direct_payload(
        series=[
            {"id": "price", "type": "candlestick", "pane": 0, "indicator": {"name": "sma", "length": 5, "source_series": "missing"}}
        ]
    )
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_provider_chart_requires_range() -> None:
    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "series": [
            {"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}
        ],
    }
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_provider_chart_rejects_inline_data() -> None:
    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "relative", "lookback": "30d"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
                ],
            }
        ],
    }
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_indicator_must_reference_existing_series() -> None:
    payload = _direct_payload(
        series=[
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
                ],
            },
            {
                "id": "sma5",
                "type": "line",
                "pane": 0,
                "indicator": {"name": "sma", "length": 5, "source_series": "nope"},
            },
        ]
    )
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_lookback_validation() -> None:
    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "relative", "lookback": "30x"},
        "series": [
            {"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}
        ],
    }
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_fixed_range_order_enforced() -> None:
    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "fixed", "start_date": "2026-05-02", "end_date": "2026-05-01"},
        "series": [
            {"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}
        ],
    }
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)


def test_duplicate_series_ids_rejected() -> None:
    payload = _direct_payload(
        series=[
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
                ],
            },
            {
                "id": "price",
                "type": "line",
                "pane": 0,
                "indicator": {"name": "sma", "length": 3, "source_series": "price"},
            },
        ]
    )
    with pytest.raises(ValidationError):
        ChartCreateRequest.model_validate(payload)
