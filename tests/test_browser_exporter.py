from __future__ import annotations

import pytest

from app.exports.browser_exporter import BrowserExporter, ExportConnectionError


@pytest.mark.asyncio
async def test_capture_without_endpoint_raises() -> None:
    exporter = BrowserExporter(ws_endpoint=None, timeout_ms=1000)
    with pytest.raises(ExportConnectionError):
        await exporter.capture_png("http://localhost/charts/abc", 800, 600)
