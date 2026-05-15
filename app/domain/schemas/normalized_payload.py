from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PayloadMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    theme: str = "dark"
    timezone: str = "UTC"


class PayloadSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    pane: int
    data: List[Dict[str, Any]] = Field(default_factory=list)
    style: Optional[Dict[str, Any]] = None
    label: Optional[str] = None


class NormalizedChartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: PayloadMeta
    layout_options: Dict[str, Any] = Field(default_factory=dict)
    series: List[PayloadSeries] = Field(default_factory=list)


class ChartGetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: Optional[str] = None
    source_kind: str
    instrument: Dict[str, Any]
    payload: NormalizedChartPayload
    warnings: List[str] = Field(default_factory=list)
