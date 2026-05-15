from __future__ import annotations

import secrets

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def generate_chart_id(length: int = 16) -> str:
    if length < 1:
        raise ValueError("length must be >= 1")
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
