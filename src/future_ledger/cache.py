"""Raw data cache for upstream AKShare responses.

Stores per-symbol DataFrames as CSV with JSON metadata sidecar.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def cache_key(stage: str, symbol: str, ext: str = ".csv") -> str:
    """Return a deterministic filename for a cached item."""
    return f"{stage}/{symbol}{ext}"


def read_cache(cache_dir: Path, key: str) -> pd.DataFrame | None:
    """Read a cached DataFrame, or return None if absent."""
    raise NotImplementedError("cache.read_cache not yet implemented")


def write_cache(cache_dir: Path, key: str, df: pd.DataFrame) -> None:
    """Persist a DataFrame to the cache directory."""
    raise NotImplementedError("cache.write_cache not yet implemented")
