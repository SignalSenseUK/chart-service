from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, List, Optional, Protocol


@dataclass(slots=True)
class ProviderRequest:
    symbol: str
    asset_class: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    series_id: Optional[str] = None
    data_format: str = "ohlcv"
    provider_config: dict[str, Any] = field(default_factory=dict)
    inline_series: Optional[dict[str, Any]] = None


@dataclass(slots=True)
class ProviderSeriesResult:
    data: List[dict[str, Any]]
    data_format: str = "ohlcv"
    warnings: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ProviderHealth:
    healthy: bool
    message: str = ""


class MarketDataAdapter(Protocol):
    async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult: ...

    async def healthcheck(self) -> ProviderHealth: ...
