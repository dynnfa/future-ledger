"""Raw data cache for upstream AKShare responses.

Stores per-symbol DataFrames as CSV with JSON metadata sidecar.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from future_ledger.domain import SourceMetadata
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


def read_metadata(cache_dir: Path, key: str) -> dict[str, Any] | None:
    """Read a cache metadata sidecar, or return None if absent."""
    path = _metadata_path(cache_dir, key)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SourceError(
            f"failed to read cache metadata: {key}",
            stage="cache_read",
            raw_detail=f"{exc.__class__.__name__}: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise SourceError(
            f"cache metadata must be a JSON object: {key}",
            stage="cache_read",
            raw_detail=repr(type(payload)),
        )
    return payload


def write_metadata(
    cache_dir: Path,
    key: str,
    metadata: SourceMetadata,
    *,
    empty: bool | None = None,
) -> None:
    """Persist stable JSON metadata next to a cached DataFrame."""
    path = _metadata_path(cache_dir, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _metadata_payload(metadata, empty=empty)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def _metadata_path(cache_dir: Path, key: str) -> Path:
    return _cache_path(cache_dir, key).with_suffix(".metadata.json")


def _metadata_payload(metadata: SourceMetadata, *, empty: bool | None) -> dict[str, Any]:
    _validate_iso8601(metadata.fetched_at)
    payload = asdict(metadata)
    payload["empty"] = metadata.row_count == 0 if empty is None else empty
    return payload


def _validate_iso8601(value: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("fetched_at must be ISO 8601") from exc
