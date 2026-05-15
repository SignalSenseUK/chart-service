from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOOKBACK_RE = re.compile(r"^\d+[dwmy]$", re.IGNORECASE)

AssetClass = Literal["equity", "forex", "futures", "crypto", "index"]
SourceKind = Literal["direct", "eodhd", "ib"]
SeriesType = Literal["candlestick", "line", "area", "histogram", "bar"]
DataFormat = Literal["ohlcv", "ohlc", "value"]
IndicatorName = Literal["sma", "ema", "vwap", "bollinger"]
BandKind = Literal["upper", "middle", "lower"]
PaneMode = Literal["single", "multi"]
Theme = Literal["light", "dark"]

MAX_DATA_POINTS_PER_SERIES = 50_000


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SourceKind
    provider: Optional[str] = None
    provider_config: Optional[dict[str, Any]] = None


class InstrumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=64)
    asset_class: AssetClass
    label: Optional[str] = Field(default=None, max_length=256)


def _validate_iso_date(value: str) -> str:
    if not _DATE_RE.match(value):
        raise ValueError("date must be ISO YYYY-MM-DD (no time component)")
    date.fromisoformat(value)
    return value


class FixedRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["fixed"]
    start_date: str
    end_date: str

    @field_validator("start_date", "end_date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        return _validate_iso_date(v)

    @model_validator(mode="after")
    def _check_order(self) -> "FixedRange":
        if date.fromisoformat(self.start_date) > date.fromisoformat(self.end_date):
            raise ValueError("start_date must be on or before end_date")
        return self


class RelativeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["relative"]
    lookback: str
    anchor: Literal["now"] = "now"

    @field_validator("lookback")
    @classmethod
    def _check_lookback(cls, v: str) -> str:
        if not _LOOKBACK_RE.match(v):
            raise ValueError(
                "lookback must match <integer><unit> where unit is d, w, m, or y"
            )
        return v.lower()


RangeInput = Annotated[Union[FixedRange, RelativeRange], Field(discriminator="mode")]


class ViewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=256)
    theme: Theme = "dark"
    mobile_responsive: bool = True
    timezone: str = "UTC"
    locale: str = "en-GB"


class LayoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pane_mode: PaneMode = "single"
    legend: bool = True
    autosize: bool = True


class SeriesStyleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: Optional[str] = None
    line_width: Optional[int] = Field(default=None, ge=1, le=4)
    opacity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    up_color: Optional[str] = None
    down_color: Optional[str] = None


class IndicatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: IndicatorName
    length: Optional[int] = Field(default=None, ge=1, le=10_000)
    stddev: Optional[float] = Field(default=None, gt=0.0)
    source_series: str = Field(min_length=1)
    band: Optional[BandKind] = None

    @model_validator(mode="after")
    def _validate_required(self) -> "IndicatorInput":
        if self.name in ("sma", "ema") and self.length is None:
            raise ValueError(f"{self.name} requires 'length'")
        if self.name == "bollinger":
            if self.length is None:
                raise ValueError("bollinger requires 'length'")
            if self.band is None:
                raise ValueError("bollinger requires 'band'")
        return self


class SeriesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    type: SeriesType
    pane: int = Field(ge=0, le=8)
    data_format: Optional[DataFormat] = None
    data: Optional[List[dict[str, Any]]] = None
    indicator: Optional[IndicatorInput] = None
    style: Optional[SeriesStyleInput] = None
    label: Optional[str] = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def _check_role(self) -> "SeriesInput":
        if self.data is not None and self.indicator is not None:
            raise ValueError(
                "series cannot include both inline 'data' and 'indicator'"
            )
        if self.data is not None:
            if len(self.data) > MAX_DATA_POINTS_PER_SERIES:
                raise ValueError(
                    f"series exceeds {MAX_DATA_POINTS_PER_SERIES} data points"
                )
            if self.data_format is None:
                raise ValueError("series with inline 'data' must declare 'data_format'")
        return self


class ChartCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    source: SourceInput
    instrument: InstrumentInput
    range: Optional[RangeInput] = None
    view: ViewInput = Field(default_factory=ViewInput)
    layout: LayoutInput = Field(default_factory=LayoutInput)
    series: List[SeriesInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_source_data_rules(self) -> "ChartCreateRequest":
        ids = [s.id for s in self.series]
        if len(ids) != len(set(ids)):
            raise ValueError("series ids must be unique within a chart")

        if self.source.kind == "direct":
            non_indicator = [s for s in self.series if s.indicator is None]
            if not non_indicator or not any(s.data for s in non_indicator):
                raise ValueError(
                    "direct charts require at least one non-indicator series with inline data"
                )
            for s in non_indicator:
                if s.data is None:
                    raise ValueError(
                        f"non-indicator series '{s.id}' in a direct chart must include inline data"
                    )
        else:
            if any(s.data is not None for s in self.series):
                raise ValueError(
                    "provider-backed charts must not include inline series data"
                )
            if self.range is None:
                raise ValueError("provider-backed charts require a 'range'")

        for s in self.series:
            if s.indicator and s.indicator.source_series not in ids:
                raise ValueError(
                    f"indicator series '{s.id}' references unknown source_series "
                    f"'{s.indicator.source_series}'"
                )
            if s.indicator and s.indicator.source_series == s.id:
                raise ValueError(
                    f"indicator series '{s.id}' cannot reference itself as source"
                )

        return self
