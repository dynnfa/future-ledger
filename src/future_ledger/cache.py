"""Raw data cache for upstream AKShare responses.

Stores per-symbol DataFrames as CSV with JSON metadata sidecar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.errors import SourceError

CACHE_STAGES = frozenset({"spot", "dividend_detail", "price_history"})
_SYMBOL_RE = re.compile(r"^\d{6}$")
_DATE_RE = re.compile(r"^\d{8}$")


def cache_key(
    stage: str,
    symbol: str,
    ext: str = ".csv",
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Return a deterministic safe relative path for a cached item."""
    _validate_stage(stage)
    _validate_symbol(symbol)
    _validate_ext(ext)

    if stage == "price_history":
        if start_date is None or end_date is None:
            raise ValueError("price_history cache keys require start_date and end_date")
        _validate_date_range(start_date, end_date)
        cache_id = f"{symbol}_{start_date}_{end_date}"
    else:
        if start_date is not None or end_date is not None:
            raise ValueError(f"{stage} cache keys do not accept start_date or end_date")
        cache_id = symbol

    return f"{stage}/{cache_id}{ext}"


def read_cache(cache_dir: Path, key: str) -> pd.DataFrame | None:
    """Read a cached DataFrame, or return None if absent."""
    path = _cache_path(cache_dir, key)
    if not path.exists():
        return None

    try:
        return pd.read_csv(path, encoding="utf-8", dtype=str)
    except Exception as exc:
        raise SourceError(
            f"failed to read cache snapshot: {key}",
            stage="cache_read",
            raw_detail=f"{exc.__class__.__name__}: {exc}",
        ) from exc


def write_cache(cache_dir: Path, key: str, df: pd.DataFrame) -> None:
    """Persist a DataFrame to the cache directory."""
    path = _cache_path(cache_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def _validate_stage(stage: str) -> None:
    if stage not in CACHE_STAGES:
        raise ValueError(f"unsupported cache stage: {stage}")


def _validate_symbol(symbol: str) -> None:
    if symbol == "all_a":
        return
    if _SYMBOL_RE.fullmatch(symbol) is None:
        raise ValueError("symbol must be all_a or a six-digit stock code")


def _validate_ext(ext: str) -> None:
    if not ext.startswith(".") or "/" in ext or "\\" in ext or ".." in ext:
        raise ValueError("ext must be a safe file extension")


def _validate_date_range(start_date: str, end_date: str) -> None:
    if _DATE_RE.fullmatch(start_date) is None:
        raise ValueError("start_date must use YYYYMMDD")
    if _DATE_RE.fullmatch(end_date) is None:
        raise ValueError("end_date must use YYYYMMDD")
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")


def _cache_path(cache_dir: Path, key: str) -> Path:
    if "\\" in key:
        raise ValueError("cache key must be a relative path without traversal segments")

    key_path = Path(key)
    if key_path.is_absolute() or ".." in key_path.parts or "." in key_path.parts:
        raise ValueError("cache key must be a relative path without traversal segments")

    return cache_dir / key_path
