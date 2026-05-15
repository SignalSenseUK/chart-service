from __future__ import annotations

import pytest


def _sample_payload():
    return {
        "source": {"kind": "direct"},
        "instrument": {"symbol": "SPY", "asset_class": "equity", "label": "SPDR S&P 500 ETF"},
        "view": {"title": "SPY Daily", "theme": "dark"},
        "series": [
            {
                "id": "price",
                "type": "candlestick",
                "pane": 0,
                "data_format": "ohlcv",
                "data": [
                    {"time": f"2026-05-{i:02d}", "open": i, "high": i + 1, "low": i - 1, "close": i + 0.5, "volume": 100 + i}
                    for i in range(1, 11)
                ],
            },
            {
                "id": "ema5",
                "type": "line",
                "pane": 0,
                "indicator": {"name": "ema", "length": 5, "source_series": "price"},
            },
        ],
    }


@pytest.mark.asyncio
async def test_full_chart_lifecycle(client) -> None:
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "connected", "version": "1.0.0"}

    create = await client.post("/api/charts", json=_sample_payload())
    assert create.status_code == 201, create.text
    body = create.json()
    chart_id = body["id"]
    assert body["view_url"].endswith(f"/charts/{chart_id}")

    fetched = await client.get(f"/api/charts/{chart_id}")
    assert fetched.status_code == 200
    payload = fetched.json()["payload"]
    series_ids = {s["id"] for s in payload["series"]}
    assert "price" in series_ids
    assert "ema5" in series_ids
    assert any(sid.endswith("__volume") for sid in series_ids)

    updated = await client.put(
        f"/api/charts/{chart_id}",
        json={**_sample_payload(), "view": {"title": "SPY Daily (updated)", "theme": "dark"}},
    )
    assert updated.status_code == 200

    fetched_again = await client.get(f"/api/charts/{chart_id}")
    assert fetched_again.json()["title"] == "SPY Daily (updated)"

    listing = await client.get("/api/charts")
    assert listing.status_code == 200
    assert any(c["id"] == chart_id for c in listing.json()["charts"])

    deleted = await client.delete(f"/api/charts/{chart_id}")
    assert deleted.status_code == 204

    gone = await client.get(f"/api/charts/{chart_id}")
    assert gone.status_code == 410

    after_delete = await client.get("/api/charts")
    assert all(c["id"] != chart_id for c in after_delete.json()["charts"])
