from __future__ import annotations

import pytest


def _direct_payload():
    return {
        "source": {"kind": "direct"},
        "instrument": {"symbol": "SPY", "asset_class": "equity"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_png_export_requires_chart(client) -> None:
    response = await client.get("/api/charts/missing/png?width=800&height=600")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_png_export_validates_width(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()
    response = await client.get(
        f"/api/charts/{created['id']}/png?width=10&height=600"
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_width"


@pytest.mark.asyncio
async def test_png_export_502_when_no_endpoint(client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()
    response = await client.get(
        f"/api/charts/{created['id']}/png?width=800&height=600"
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "export_unavailable"


@pytest.mark.asyncio
async def test_png_export_uses_mocked_browser(monkeypatch, client) -> None:
    created = (await client.post("/api/charts", json=_direct_payload())).json()

    async def _fake_capture(self, render_url, width, height):
        return b"\x89PNG\r\n\x1a\nFAKEDATA"

    monkeypatch.setattr(
        "app.api.routes.exports.BrowserExporter.capture_png",
        _fake_capture,
    )

    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "EXPORT_BROWSER_WS_ENDPOINT", "ws://browser:3000")

    response = await client.get(
        f"/api/charts/{created['id']}/png?width=800&height=600"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"\x89PNG")
