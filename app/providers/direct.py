from __future__ import annotations

from app.api.errors import ChartValidationError
from app.domain.services.normalization_service import normalize_series
from app.providers.base import (
    MarketDataAdapter,
    ProviderHealth,
    ProviderRequest,
    ProviderSeriesResult,
)


class DirectAdapter(MarketDataAdapter):
    async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult:
        if request.inline_series is None:
            raise ChartValidationError(
                f"direct series '{request.series_id}' is missing inline data",
                code="missing_inline_data",
            )
        data = normalize_series(
            request.inline_series.get("data", []),
            request.inline_series.get("data_format", request.data_format),
        )
        return ProviderSeriesResult(
            data=data,
            data_format=request.inline_series.get("data_format", request.data_format),
        )

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(healthy=True, message="direct adapter ready")
