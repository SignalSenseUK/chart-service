from __future__ import annotations

from app.providers.base import MarketDataAdapter
from app.providers.direct import DirectAdapter


def get_adapter(source_kind: str) -> MarketDataAdapter:
    if source_kind == "direct":
        return DirectAdapter()
    if source_kind == "eodhd":
        from app.providers.eodhd import EodhdAdapter  # noqa: PLC0415

        return EodhdAdapter.get_instance()
    if source_kind == "ib":
        from app.providers.ib import IbAdapter  # noqa: PLC0415

        return IbAdapter.get_instance()
    raise ValueError(f"unknown source_kind '{source_kind}'")
