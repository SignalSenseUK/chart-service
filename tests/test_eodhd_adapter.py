from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.api.errors import ChartValidationError, ProviderError
from app.providers.base import ProviderRequest
from app.providers.eodhd import EodhdAdapter


def _make_adapter(handler):
    adapter = EodhdAdapter(api_key="test-key", timeout_ms=1000)
    transport = httpx.MockTransport(handler)
    adapter._client_factory = lambda: httpx.AsyncClient(transport=transport)
    return adapter


@pytest.mark.asyncio
async def test_fetch_series_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/eod/SPY" in str(request.url)
        return httpx.Response(
            200,
            json=[
                {"date": "2026-05-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
                {"date": "2026-04-30", "open": 98, "high": 101, "low": 97, "close": 100, "volume": 900},
            ],
        )

    adapter = _make_adapter(handler)
    result = await adapter.fetch_series(
        ProviderRequest(
            symbol="SPY",
            asset_class="equity",
            start_date=date(2026, 4, 30),
            end_date=date(2026, 5, 1),
        )
    )
    assert len(result.data) == 2
    assert result.data[0]["time"] == "2026-04-30"
    assert result.data[1]["close"] == 103.0


@pytest.mark.asyncio
async def test_fetch_series_warns_on_short_range() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"date": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1}],
        )

    adapter = _make_adapter(handler)
    result = await adapter.fetch_series(
        ProviderRequest(
            symbol="SPY",
            asset_class="equity",
            start_date=date(2026, 4, 30),
            end_date=date(2026, 5, 1),
        )
    )
    assert any("Earliest available" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_fetch_series_4xx_raises_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    adapter = _make_adapter(handler)
    with pytest.raises(ChartValidationError):
        await adapter.fetch_series(
            ProviderRequest(
                symbol="MISSING",
                asset_class="equity",
                start_date=date(2026, 4, 30),
                end_date=date(2026, 5, 1),
            )
        )


@pytest.mark.asyncio
async def test_fetch_series_5xx_raises_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    adapter = _make_adapter(handler)
    with pytest.raises(ProviderError):
        await adapter.fetch_series(
            ProviderRequest(
                symbol="SPY",
                asset_class="equity",
                start_date=date(2026, 4, 30),
                end_date=date(2026, 5, 1),
            )
        )


@pytest.mark.asyncio
async def test_fetch_requires_api_key() -> None:
    adapter = EodhdAdapter(api_key=None)
    with pytest.raises(ChartValidationError):
        await adapter.fetch_series(
            ProviderRequest(symbol="SPY", asset_class="equity", start_date=date(2026, 4, 30), end_date=date(2026, 5, 1))
        )


@pytest.mark.asyncio
async def test_fetch_requires_range() -> None:
    adapter = EodhdAdapter(api_key="test-key")
    with pytest.raises(ChartValidationError):
        await adapter.fetch_series(ProviderRequest(symbol="SPY", asset_class="equity"))
