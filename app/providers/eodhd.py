from __future__ import annotations

from typing import Any, Optional

import httpx

from app.api.errors import ChartValidationError, ProviderError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import (
    MarketDataAdapter,
    ProviderHealth,
    ProviderRequest,
    ProviderSeriesResult,
)

logger = get_logger("app.providers.eodhd")

_BASE_URL = "https://eodhd.com/api"


def _normalize_bar(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "time": row["date"],
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row.get("volume") or 0.0),
    }


class EodhdAdapter(MarketDataAdapter):
    _instance: Optional["EodhdAdapter"] = None

    def __init__(self, api_key: str | None = None, timeout_ms: int | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.EODHD_API_KEY
        timeout_seconds = (timeout_ms or settings.EODHD_TIMEOUT_MS) / 1000.0
        self._timeout = httpx.Timeout(timeout_seconds)
        self._client_factory = lambda: httpx.AsyncClient(timeout=self._timeout)

    @classmethod
    def get_instance(cls) -> "EodhdAdapter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult:
        if not self._api_key:
            raise ChartValidationError(
                "EODHD_API_KEY is not configured",
                code="provider_not_configured",
            )
        if request.start_date is None or request.end_date is None:
            raise ChartValidationError(
                "EODHD provider requires a resolved date range",
                code="missing_range",
            )

        symbol = request.symbol
        url = f"{_BASE_URL}/eod/{symbol}"
        params = {
            "from": request.start_date.isoformat(),
            "to": request.end_date.isoformat(),
            "period": "d",
            "fmt": "json",
            "api_token": self._api_key,
        }

        try:
            async with self._client_factory() as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("eodhd.request_failed", error=str(exc), symbol=symbol)
            raise ProviderError(f"EODHD request failed: {exc}") from exc

        if response.status_code >= 500:
            logger.warning(
                "eodhd.provider_error",
                status=response.status_code,
                symbol=symbol,
            )
            raise ProviderError(
                f"EODHD returned status {response.status_code}",
            )
        if response.status_code >= 400:
            raise ChartValidationError(
                f"EODHD rejected request (status {response.status_code}): {response.text[:200]}",
                code="provider_rejected",
            )

        try:
            rows = response.json()
        except ValueError as exc:
            raise ProviderError(f"EODHD returned invalid JSON: {exc}") from exc

        if not isinstance(rows, list):
            raise ProviderError("EODHD returned unexpected payload shape")

        bars = [_normalize_bar(r) for r in rows]
        bars.sort(key=lambda r: r["time"])

        warnings: list[str] = []
        if bars and request.start_date and bars[0]["time"] > request.start_date.isoformat():
            warnings.append(
                f"Earliest available bar {bars[0]['time']} is later than requested start "
                f"{request.start_date.isoformat()}"
            )

        return ProviderSeriesResult(data=bars, data_format="ohlcv", warnings=warnings)

    async def healthcheck(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(healthy=False, message="EODHD_API_KEY not configured")
        try:
            async with self._client_factory() as client:
                response = await client.get(
                    f"{_BASE_URL}/exchanges-list/",
                    params={"api_token": self._api_key, "fmt": "json"},
                )
        except httpx.HTTPError as exc:
            return ProviderHealth(healthy=False, message=f"http error: {exc}")
        if response.status_code != 200:
            return ProviderHealth(
                healthy=False,
                message=f"EODHD healthcheck status {response.status_code}",
            )
        return ProviderHealth(healthy=True, message="ok")
