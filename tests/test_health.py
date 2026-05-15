from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_ok(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "database": "connected", "version": "1.0.0"}
