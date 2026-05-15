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
async def test_get_chart_returns_definition(client) -> None:
    create = await client.post("/api/charts", json=_direct_payload())
    chart_id = create.json()["id"]

    response = await client.get(f"/api/charts/{chart_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == chart_id
    assert body["title"] == "SPY Daily"
    assert body["source_kind"] == "direct"
    assert body["inline_series"]["price"]["data_format"] == "ohlcv"
    assert len(body["inline_series"]["price"]["data"]) == 2
    # inline data should be stripped from chart_definition
    assert "data" not in body["chart_definition"]["series"][0]


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
