from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChartCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    view_url: str
    embed_url: str
    api_url: str


class ChartSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: Optional[str] = None
    source_kind: str
    created_at: datetime
    updated_at: datetime


class ChartListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    charts: List[ChartSummary] = Field(default_factory=list)
    total: int
    page: int
    limit: int


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
