from __future__ import annotations

import pytest


def _direct_payload(title: str = "SPY Daily"):
    return {
        "source": {"kind": "direct"},
        "instrument": {"symbol": "SPY", "asset_class": "equity", "label": "SPDR S&P 500 ETF"},
        "view": {"title": title, "theme": "dark"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 1_000_000},
                    {"time": "2026-05-02", "open": 103.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 1_200_000},
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_create_chart_returns_urls(client) -> None:
    response = await client.post("/api/charts", json=_direct_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "view_url", "embed_url", "api_url"}
    assert body["view_url"].endswith(f"/charts/{body['id']}")
    assert body["embed_url"].endswith(f"/embed/{body['id']}")
    assert body["api_url"].endswith(f"/api/charts/{body['id']}")


@pytest.mark.asyncio
async def test_get_chart_returns_payload(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]

    response = await client.get(f"/api/charts/{chart_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == chart_id
    assert body["title"] == "SPY Daily"
    assert body["source_kind"] == "direct"
    assert body["instrument"]["symbol"] == "SPY"
    series = body["payload"]["series"]
    price = next(s for s in series if s["id"] == "price")
    assert price["type"] == "candlestick"
    assert len(price["data"]) == 2
    volume = next(s for s in series if s["id"].endswith("__volume"))
    assert volume["type"] == "histogram"
    assert volume["pane"] == 1


@pytest.mark.asyncio
async def test_get_missing_chart_returns_404(client) -> None:
    response = await client.get("/api/charts/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "chart_not_found"


@pytest.mark.asyncio
async def test_create_chart_rejects_invalid_payload(client) -> None:
    response = await client.post("/api/charts", json={"source": {"kind": "direct"}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.asyncio
async def test_update_chart_changes_definition(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload(title="Original"))
    chart_id = create.json()["id"]

    new_payload = _direct_payload(title="Updated")
    update = await client.put(f"/api/charts/{chart_id}", json=new_payload)
    assert update.status_code == 200, update.text

    fetched = await client.get(f"/api/charts/{chart_id}")
    body = fetched.json()
    assert body["title"] == "Updated"


@pytest.mark.asyncio
async def test_update_rejects_source_kind_change(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]

    provider_payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "relative", "lookback": "30d"},
        "series": [
            {"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}
        ],
    }
    response = await client.put(f"/api/charts/{chart_id}", json=provider_payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_source_kind_change"


@pytest.mark.asyncio
async def test_delete_chart_returns_410_on_subsequent_get(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]

    delete = await client.delete(f"/api/charts/{chart_id}")
    assert delete.status_code == 204
    assert delete.content == b""

    fetched = await client.get(f"/api/charts/{chart_id}")
    assert fetched.status_code == 410
    assert fetched.json()["error"]["code"] == "chart_deleted"


@pytest.mark.asyncio
async def test_delete_already_deleted_returns_410(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]

    await client.delete(f"/api/charts/{chart_id}")
    response = await client.delete(f"/api/charts/{chart_id}")
    assert response.status_code == 410


@pytest.mark.asyncio
async def test_list_charts_paginates(client) -> None:
    for i in range(3):
        await client.post("/api/charts", json=_direct_payload(title=f"Chart {i}"))

    response = await client.get("/api/charts?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["charts"]) == 2

    response2 = await client.get("/api/charts?limit=2&page=2")
    body2 = response2.json()
    assert body2["total"] == 3
    assert len(body2["charts"]) == 1

    all_titles = {c["title"] for c in body["charts"] + body2["charts"]}
    assert all_titles == {"Chart 0", "Chart 1", "Chart 2"}


@pytest.mark.asyncio
async def test_list_charts_excludes_deleted(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]
    await client.delete(f"/api/charts/{chart_id}")

    response = await client.get("/api/charts")
    body = response.json()
    assert all(c["id"] != chart_id for c in body["charts"])
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_charts_filters_by_source_kind(client) -> None:
    await client.post("/api/charts", json=_direct_payload())
    response = await client.get("/api/charts?source_kind=eodhd")
    body = response.json()
    assert body["total"] == 0
    assert body["charts"] == []


@pytest.mark.asyncio
async def test_eodhd_chart_create_uses_validation_fetch(monkeypatch, client) -> None:
    from datetime import date as _date

    from app.providers.base import ProviderHealth, ProviderRequest, ProviderSeriesResult

    calls: list[ProviderRequest] = []

    class _FakeAdapter:
        async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult:
            calls.append(request)
            return ProviderSeriesResult(
                data=[
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000},
                ],
                data_format="ohlcv",
                warnings=[],
            )

        async def healthcheck(self) -> ProviderHealth:
            return ProviderHealth(healthy=True)

    monkeypatch.setattr(
        "app.providers.registry.get_adapter",
        lambda kind: _FakeAdapter() if kind == "eodhd" else (_ for _ in ()).throw(ValueError(kind)),
    )
    monkeypatch.setattr(
        "app.domain.services.chart_service.get_adapter",
        lambda kind: _FakeAdapter() if kind == "eodhd" else (_ for _ in ()).throw(ValueError(kind)),
    )

    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "fixed", "start_date": "2026-04-30", "end_date": "2026-05-01"},
        "view": {"title": "EODHD chart"},
        "series": [{"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}],
    }
    response = await client.post("/api/charts", json=payload)
    assert response.status_code == 201, response.text
    assert calls, "EODHD adapter was not invoked for validation fetch"
    assert calls[0].start_date == _date(2026, 4, 30)


@pytest.mark.asyncio
async def test_eodhd_chart_create_rejects_when_provider_empty(monkeypatch, client) -> None:
    from app.providers.base import ProviderHealth, ProviderRequest, ProviderSeriesResult

    class _EmptyAdapter:
        async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult:
            return ProviderSeriesResult(data=[], data_format="ohlcv")

        async def healthcheck(self) -> ProviderHealth:
            return ProviderHealth(healthy=True)

    monkeypatch.setattr(
        "app.domain.services.chart_service.get_adapter",
        lambda kind: _EmptyAdapter(),
    )

    payload = {
        "source": {"kind": "eodhd"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "range": {"mode": "fixed", "start_date": "2026-04-30", "end_date": "2026-05-01"},
        "series": [{"id": "price", "type": "candlestick", "pane": 0, "data_format": "ohlcv"}],
    }
    response = await client.post("/api/charts", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "provider_empty"


@pytest.mark.asyncio
async def test_get_chart_with_indicator_series(client) -> None:
    payload = _direct_payload()
    payload["series"][0]["data"] = [
        {"time": f"2026-05-{i + 1:02d}", "open": i, "high": i + 1, "low": i - 1, "close": i, "volume": 1000}
        for i in range(1, 6)
    ]
    payload["series"].append(
        {
            "id": "sma3",
            "type": "line",
            "pane": 0,
            "indicator": {"name": "sma", "length": 3, "source_series": "price"},
        }
    )
    create = await client.post("/api/charts", json=payload)
    assert create.status_code == 201, create.text
    chart_id = create.json()["id"]

    response = await client.get(f"/api/charts/{chart_id}")
    body = response.json()
    series_by_id = {s["id"]: s for s in body["payload"]["series"]}
    assert "price" in series_by_id
    assert "sma3" in series_by_id
    assert len(series_by_id["sma3"]["data"]) == 3
    assert series_by_id["sma3"]["data"][0]["time"] == "2026-05-04"
