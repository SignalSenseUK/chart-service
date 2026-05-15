from __future__ import annotations

import re

import pytest

from app.core.ids import generate_chart_id

_URL_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")


def test_default_length_is_16() -> None:
    assert len(generate_chart_id()) == 16


def test_custom_length() -> None:
    assert len(generate_chart_id(21)) == 21


def test_alphabet_is_url_safe() -> None:
    for _ in range(50):
        chart_id = generate_chart_id()
        assert _URL_SAFE.match(chart_id), chart_id


def test_ids_are_unique_across_1000() -> None:
    ids = {generate_chart_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_zero_length_rejected() -> None:
    with pytest.raises(ValueError):
        generate_chart_id(0)
