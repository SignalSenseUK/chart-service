from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_request_id_round_trip(client) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(client) -> None:
    response = await client.get("/health")
    assert "x-request-id" in {k.lower() for k in response.headers}


@pytest.mark.asyncio
async def test_body_size_limit_rejects_oversized_request(client) -> None:
    response = await client.post(
        "/api/charts",
        headers={"Content-Length": str(11 * 1024 * 1024), "Content-Type": "application/json"},
        content=b"{}",
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
