from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.api.errors import ChartValidationError
from app.providers.base import ProviderRequest
from app.providers.ib import (
    IbAdapter,
    _build_contract,
    _date_str,
    _default_sec_type,
    _duration_string,
    _normalize_bar,
)


def test_default_sec_type_mapping() -> None:
    assert _default_sec_type("equity") == "STK"
    assert _default_sec_type("forex") == "CASH"
    assert _default_sec_type("futures") == "FUT"
    assert _default_sec_type("crypto") == "CRYPTO"
    assert _default_sec_type("index") == "IND"
    assert _default_sec_type("unknown") == "STK"


def test_duration_string() -> None:
    assert _duration_string(date(2026, 5, 1), date(2026, 5, 1)) == "1 D"
    assert _duration_string(date(2026, 5, 1), date(2026, 5, 10)) == "10 D"
    assert _duration_string(date(2024, 5, 1), date(2026, 5, 1)).endswith("Y")


def test_date_str_strips_time_component() -> None:
    assert _date_str("2026-05-01 23:59:59") == "2026-05-01"
    assert _date_str("2026-05-01T23:59:59Z") == "2026-05-01"
    assert _date_str(date(2026, 5, 1)) == "2026-05-01"


def test_normalize_bar_from_object() -> None:
    bar = SimpleNamespace(date=date(2026, 5, 1), open=1, high=2, low=0.5, close=1.5, volume=1000)
    assert _normalize_bar(bar) == {
        "time": "2026-05-01",
        "open": 1.0,
        "high": 2.0,
        "low": 0.5,
        "close": 1.5,
        "volume": 1000.0,
    }


def test_build_contract_uses_provider_config() -> None:
    contract = _build_contract(
        {"secType": "FUT", "exchange": "GLOBEX", "currency": "USD", "lastTradeDateOrContractMonth": "202612"},
        "futures",
        "ES",
    )
    assert contract.secType == "FUT"
    assert contract.exchange == "GLOBEX"
    assert contract.lastTradeDateOrContractMonth == "202612"


@pytest.mark.asyncio
async def test_missing_config_rejects_with_validation_error() -> None:
    IbAdapter.reset_instance()
    adapter = IbAdapter()
    adapter._host = None  # simulate missing config
    with pytest.raises(ChartValidationError):
        await adapter.fetch_series(
            ProviderRequest(
                symbol="ES",
                asset_class="futures",
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 5),
            )
        )


@pytest.mark.asyncio
async def test_fetch_uses_mocked_ib(monkeypatch) -> None:
    IbAdapter.reset_instance()
    adapter = IbAdapter()
    adapter._host = "localhost"
    adapter._port = 7497
    adapter._client_id = 1

    class _FakeIB:
        def __init__(self) -> None:
            self._connected = False

        def isConnected(self) -> bool:
            return self._connected

        async def connectAsync(self, host, port, clientId):
            self._connected = True

        async def reqHistoricalDataAsync(self, *args, **kwargs):
            return [
                SimpleNamespace(date=date(2026, 4, 30), open=1, high=2, low=0.5, close=1.5, volume=100),
                SimpleNamespace(date=date(2026, 5, 1), open=1.5, high=2.5, low=1.0, close=2.0, volume=120),
                SimpleNamespace(date=date(2026, 4, 28), open=0.5, high=1.0, low=0.25, close=0.75, volume=50),
            ]

        def disconnect(self) -> None:
            self._connected = False

    adapter._ib = _FakeIB()

    result = await adapter.fetch_series(
        ProviderRequest(
            symbol="SPY",
            asset_class="equity",
            start_date=date(2026, 4, 30),
            end_date=date(2026, 5, 1),
            provider_config={"exchange": "ARCA"},
        )
    )
    assert [b["time"] for b in result.data] == ["2026-04-30", "2026-05-01"]
    assert result.data[1]["close"] == 2.0
