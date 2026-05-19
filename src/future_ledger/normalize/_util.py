"""Shared normalization helpers for DataFrame cell parsing."""

from __future__ import annotations

from typing import Any

import pandas as pd  # type: ignore[import-untyped]

_PANDAS_SENTINELS = frozenset({"", "-", "--", "nan", "NaN", "None"})


def string_or_none(value: Any) -> str | None:
    """Coerce a DataFrame cell to str, returning None for missing/empty values."""
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if text in _PANDAS_SENTINELS:
        return None
    return text
