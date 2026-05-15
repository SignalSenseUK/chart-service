from __future__ import annotations

import pytest


def _direct_payload(title: str = "SPY Daily"):
    return {
        "source": {"kind": "direct"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "view": {"title": title, "theme": "dark"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000},
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_hosted_chart_page_renders(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()

    response = await client.get(f"/charts/{created['id']}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "/static/charts.js" in body
    assert "/static/charts.css" in body
    assert created["id"] in body


@pytest.mark.asyncio
async def test_hosted_chart_404(client) -> None:
    response = await client.get("/charts/missing")
    assert response.status_code == 404
    assert "Chart not found" in response.text


@pytest.mark.asyncio
async def test_hosted_chart_410(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()
    await client.delete(f"/api/charts/{created['id']}")
    response = await client.get(f"/charts/{created['id']}")
    assert response.status_code == 410
    assert "removed" in response.text.lower()


@pytest.mark.asyncio
async def test_embed_chart_page_has_frame_ancestors(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()

    response = await client.get(f"/embed/{created['id']}")
    assert response.status_code == 200
    assert response.headers.get("content-security-policy") == "frame-ancestors *"
    assert "chart-title" not in response.text


@pytest.mark.asyncio
async def test_api_routes_have_cors_header(client) -> None:
    response = await client.get("/api/charts")
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"


@pytest.mark.asyncio
async def test_api_options_preflight(client) -> None:
    response = await client.options(
        "/api/charts",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 204
    assert response.headers.get("access-control-allow-origin") == "*"


@pytest.mark.asyncio
async def test_hosted_chart_page_has_no_cors_header(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()
    response = await client.get(f"/charts/{created['id']}")
    assert "access-control-allow-origin" not in (k.lower() for k in response.headers)
