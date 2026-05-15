from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger("app.exports.browser")


class ExportError(Exception):
    """Base class for export failures."""


class ExportConnectionError(ExportError):
    """Raised when the headless browser sidecar cannot be reached."""


class ExportTimeoutError(ExportError):
    """Raised when the chart-ready signal does not arrive in time."""


class ExportRenderError(ExportError):
    """Raised when the chart page reports a render failure."""


class BrowserExporter:
    def __init__(self, ws_endpoint: str | None, timeout_ms: int) -> None:
        self._ws_endpoint = ws_endpoint
        self._timeout_ms = timeout_ms

    async def capture_png(
        self,
        render_url: str,
        width: int,
        height: int,
    ) -> bytes:
        if not self._ws_endpoint:
            raise ExportConnectionError("EXPORT_BROWSER_WS_ENDPOINT is not configured")

        try:
            from playwright.async_api import (
                Error as PlaywrightError,
                TimeoutError as PlaywrightTimeout,
                async_playwright,
            )
        except ImportError as exc:  # pragma: no cover - import guard
            raise ExportConnectionError(f"playwright not installed: {exc}") from exc

        logger.info("export.start", url=render_url, width=width, height=height)

        try:
            async with async_playwright() as pw:
                try:
                    browser = await pw.chromium.connect_over_cdp(self._ws_endpoint)
                except PlaywrightError as exc:
                    raise ExportConnectionError(
                        f"failed to connect to browser sidecar: {exc}"
                    ) from exc

                try:
                    context = await browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                    )
                    page = await context.new_page()
                    try:
                        await page.goto(render_url, wait_until="domcontentloaded")
                        try:
                            await page.wait_for_selector(
                                'body[data-chart-ready="true"]',
                                timeout=self._timeout_ms,
                            )
                        except PlaywrightTimeout as exc:
                            raise ExportTimeoutError(
                                "chart-ready signal not received before timeout"
                            ) from exc

                        container = await page.query_selector("#chart-container")
                        if container is None:
                            png = await page.screenshot(type="png", full_page=False)
                        else:
                            png = await container.screenshot(type="png")
                        return png
                    finally:
                        await page.close()
                        await context.close()
                finally:
                    await browser.close()
        except (ExportError, ExportConnectionError, ExportTimeoutError):
            raise
        except PlaywrightError as exc:
            raise ExportRenderError(f"browser export failed: {exc}") from exc
