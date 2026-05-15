from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.domain.services import range_resolver
from app.domain.services.range_resolver import resolve_range


def test_fixed_range_parses_iso_dates() -> None:
    start, end = resolve_range({"mode": "fixed", "start_date": "2025-01-01", "end_date": "2026-01-01"})
    assert start == date(2025, 1, 1)
    assert end == date(2026, 1, 1)


def test_fixed_range_rejects_inverted() -> None:
    with pytest.raises(ValueError):
        resolve_range({"mode": "fixed", "start_date": "2026-01-02", "end_date": "2026-01-01"})


def test_relative_days(monkeypatch) -> None:
    monkeypatch.setattr(range_resolver, "_today", lambda: date(2026, 5, 15))
    start, end = resolve_range({"mode": "relative", "lookback": "30d", "anchor": "now"})
    assert end == date(2026, 5, 15)
    assert start == date(2026, 4, 15)


def test_relative_weeks(monkeypatch) -> None:
    monkeypatch.setattr(range_resolver, "_today", lambda: date(2026, 5, 15))
    start, end = resolve_range({"mode": "relative", "lookback": "2w"})
    assert end - start == timedelta(weeks=2)


def test_relative_months(monkeypatch) -> None:
    monkeypatch.setattr(range_resolver, "_today", lambda: date(2026, 3, 31))
    start, _ = resolve_range({"mode": "relative", "lookback": "1m"})
    # Feb 31 → clamp to Feb 28 (2026 is not a leap year)
    assert start == date(2026, 2, 28)


def test_relative_years(monkeypatch) -> None:
    monkeypatch.setattr(range_resolver, "_today", lambda: date(2026, 5, 15))
    start, _ = resolve_range({"mode": "relative", "lookback": "25y"})
    assert start == date(2001, 5, 15)


def test_unsupported_mode() -> None:
    with pytest.raises(ValueError, match="unsupported range"):
        resolve_range({"mode": "calendar"})


def test_invalid_lookback() -> None:
    with pytest.raises(ValueError, match="lookback must match"):
        resolve_range({"mode": "relative", "lookback": "30x"})
