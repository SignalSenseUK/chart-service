from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Mapping

_LOOKBACK_RE = re.compile(r"^(\d+)([dwmy])$", re.IGNORECASE)


def _today() -> date:
    return date.today()


def _subtract_months(reference: date, months: int) -> date:
    year = reference.year
    month = reference.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = reference.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1


def _subtract_years(reference: date, years: int) -> date:
    try:
        return reference.replace(year=reference.year - years)
    except ValueError:
        return reference.replace(year=reference.year - years, day=reference.day - 1)


def resolve_range(range_config: Mapping[str, object]) -> tuple[date, date]:
    mode = range_config.get("mode")
    if mode == "fixed":
        start_raw = range_config.get("start_date")
        end_raw = range_config.get("end_date")
        if not isinstance(start_raw, str) or not isinstance(end_raw, str):
            raise ValueError("fixed range requires start_date and end_date as YYYY-MM-DD strings")
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
        if start > end:
            raise ValueError("start_date must be on or before end_date")
        return start, end

    if mode == "relative":
        lookback_raw = range_config.get("lookback")
        if not isinstance(lookback_raw, str):
            raise ValueError("relative range requires 'lookback' string")
        match = _LOOKBACK_RE.match(lookback_raw)
        if not match:
            raise ValueError(
                "lookback must match <integer><unit>, where unit is d, w, m, or y"
            )
        amount = int(match.group(1))
        unit = match.group(2).lower()
        end = _today()
        if unit == "d":
            start = end - timedelta(days=amount)
        elif unit == "w":
            start = end - timedelta(weeks=amount)
        elif unit == "m":
            start = _subtract_months(end, amount)
        else:
            start = _subtract_years(end, amount)
        return start, end

    raise ValueError(f"unsupported range mode '{mode}'")
