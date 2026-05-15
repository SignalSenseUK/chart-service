from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any, Optional

from app.api.errors import ChartValidationError, ProviderError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import (
    MarketDataAdapter,
    ProviderHealth,
    ProviderRequest,
    ProviderSeriesResult,
)

logger = get_logger("app.providers.ib")

_PACING_INTERVAL_S = 1.0  # IB historical request minimum spacing


def _date_str(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    s = str(value)
    if "T" in s:
        s = s.split("T", 1)[0]
    if " " in s:
        s = s.split(" ", 1)[0]
    return s


def _normalize_bar(bar: Any) -> dict[str, Any]:
    return {
        "time": _date_str(getattr(bar, "date", None) or bar["date"]),
        "open": float(getattr(bar, "open", None) or bar["open"]),
        "high": float(getattr(bar, "high", None) or bar["high"]),
        "low": float(getattr(bar, "low", None) or bar["low"]),
        "close": float(getattr(bar, "close", None) or bar["close"]),
        "volume": float(getattr(bar, "volume", 0) or 0),
    }


def _build_contract(cfg: dict[str, Any], asset_class: str, symbol: str):
    """Build an ib_async Contract from provider_config + instrument metadata."""
    from ib_async import Contract  # local import to keep cold-start light

    sec_type = cfg.get("secType") or _default_sec_type(asset_class)
    contract = Contract()
    contract.symbol = cfg.get("symbol") or symbol
    contract.secType = sec_type
    contract.exchange = cfg.get("exchange") or "SMART"
    contract.currency = cfg.get("currency") or "USD"
    if cfg.get("primaryExchange"):
        contract.primaryExchange = cfg["primaryExchange"]
    if cfg.get("localSymbol"):
        contract.localSymbol = cfg["localSymbol"]
    if cfg.get("lastTradeDateOrContractMonth"):
        contract.lastTradeDateOrContractMonth = cfg["lastTradeDateOrContractMonth"]
    return contract


def _default_sec_type(asset_class: str) -> str:
    mapping = {
        "equity": "STK",
        "forex": "CASH",
        "futures": "FUT",
        "crypto": "CRYPTO",
        "index": "IND",
    }
    return mapping.get(asset_class, "STK")


def _duration_string(start: date, end: date) -> str:
    days = (end - start).days + 1
    if days <= 0:
        days = 1
    if days <= 365:
        return f"{days} D"
    years = max(1, days // 365)
    return f"{years} Y"


class IbAdapter(MarketDataAdapter):
    _instance: Optional["IbAdapter"] = None

    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.IB_HOST
        self._port = settings.IB_PORT
        self._client_id = settings.IB_CLIENT_ID
        self._timeout_s = settings.IB_TIMEOUT_MS / 1000.0
        self._ib = None
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0
        self._connect_backoff_s = 1.0
        self._max_backoff_s = 30.0

    @classmethod
    def get_instance(cls) -> "IbAdapter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def _missing_config(self) -> bool:
        return not (self._host and self._port and self._client_id is not None)

    async def _ensure_connected(self) -> None:
        if self._missing_config():
            raise ChartValidationError(
                "IB provider is not configured (IB_HOST / IB_PORT / IB_CLIENT_ID required)",
                code="provider_not_configured",
            )

        from ib_async import IB  # local import

        if self._ib is None:
            self._ib = IB()

        if self._ib.isConnected():
            return

        delay = self._connect_backoff_s
        last_error: Exception | None = None
        for _ in range(5):
            try:
                await self._ib.connectAsync(self._host, self._port, clientId=self._client_id)
                self._connect_backoff_s = 1.0
                logger.info("ib.connected", host=self._host, port=self._port)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("ib.connect_failed", error=str(exc), backoff_s=delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_backoff_s)

        raise ProviderError(f"IB connection failed: {last_error}")

    async def _respect_pacing(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _PACING_INTERVAL_S:
            await asyncio.sleep(_PACING_INTERVAL_S - elapsed)

    async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult:
        if request.start_date is None or request.end_date is None:
            raise ChartValidationError(
                "IB provider requires a resolved date range",
                code="missing_range",
            )

        await self._ensure_connected()
        assert self._ib is not None

        contract = _build_contract(
            request.provider_config or {},
            request.asset_class,
            request.symbol,
        )

        duration = _duration_string(request.start_date, request.end_date)
        end_datetime = f"{request.end_date.strftime('%Y%m%d')} 23:59:59 UTC"

        async with self._lock:
            await self._respect_pacing()
            try:
                bars = await asyncio.wait_for(
                    self._ib.reqHistoricalDataAsync(
                        contract,
                        endDateTime=end_datetime,
                        durationStr=duration,
                        barSizeSetting="1 day",
                        whatToShow="TRADES",
                        useRTH=True,
                        formatDate=1,
                    ),
                    timeout=self._timeout_s,
                )
            except asyncio.TimeoutError as exc:
                raise ProviderError("IB request timed out") from exc
            except Exception as exc:  # noqa: BLE001
                raise ProviderError(f"IB request failed: {exc}") from exc
            finally:
                self._last_request_at = time.monotonic()

        if bars is None:
            raise ProviderError("IB returned no result")

        start_iso = request.start_date.isoformat()
        data: list[dict[str, Any]] = []
        for raw in bars:
            row = _normalize_bar(raw)
            if row["time"] < start_iso:
                continue
            data.append(row)
        data.sort(key=lambda r: r["time"])

        warnings: list[str] = []
        if data and data[0]["time"] > start_iso:
            warnings.append(
                f"Earliest IB bar {data[0]['time']} is later than requested start {start_iso}"
            )
        return ProviderSeriesResult(data=data, data_format="ohlcv", warnings=warnings)

    async def healthcheck(self) -> ProviderHealth:
        if self._missing_config():
            return ProviderHealth(healthy=False, message="IB not configured")
        try:
            await self._ensure_connected()
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(healthy=False, message=str(exc))
        return ProviderHealth(healthy=True, message="ok")

    async def disconnect(self) -> None:
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()

    async def connect(self) -> None:
        await self._ensure_connected()
