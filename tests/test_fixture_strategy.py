from __future__ import annotations

import csv
import re
from pathlib import Path

FIXTURE_ROOT = Path("tests/fixtures")
AKSHARE_ROOT = FIXTURE_ROOT / "akshare"
PRICES_ROOT = FIXTURE_ROOT / "prices"
CACHE_ROOT = FIXTURE_ROOT / "cache"
WORKBOOKS_ROOT = FIXTURE_ROOT / "workbooks"

DIVIDEND_DETAIL_PATTERN = re.compile(r"dividend_detail_\d{6}\.csv")
PRICE_HISTORY_PATTERN = re.compile(r"\d{6}_daily_\d{8}_\d{8}\.csv")


def test_fixture_files_follow_naming_convention() -> None:
    assert (AKSHARE_ROOT / "spot_a_share.csv").is_file()

    for path in _csv_fixture_paths():
        relative = path.relative_to(FIXTURE_ROOT)
        if relative.parts[0] == "akshare":
            assert _is_valid_akshare_fixture(relative), f"Unexpected AKShare fixture: {path}"
        elif relative.parts[0] == "prices":
            assert PRICE_HISTORY_PATTERN.fullmatch(path.name), (
                f"Unexpected price fixture: {path}"
            )
        elif relative.parts[0] == "cache":
            assert len(relative.parts) == 3, f"Cache fixture must be stage/cache_id: {path}"
        elif relative.parts[0] == "workbooks":
            raise AssertionError(f"Workbook fixture must not be CSV: {path}")
        else:
            raise AssertionError(f"Unexpected fixture directory: {path}")


def test_fixture_files_are_utf8_csv() -> None:
    for path in _csv_fixture_paths():
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))

        assert rows, f"Fixture must contain at least a header row: {path}"


def test_fixture_files_stay_small() -> None:
    for path in _csv_fixture_paths():
        with path.open(encoding="utf-8", newline="") as handle:
            row_count = max(sum(1 for _row in csv.reader(handle)) - 1, 0)

        assert row_count < 100, f"Default fixture has {row_count} rows: {path}"


def _csv_fixture_paths() -> list[Path]:
    return sorted(FIXTURE_ROOT.rglob("*.csv"))


def _is_valid_akshare_fixture(relative_path: Path) -> bool:
    return relative_path.name == "spot_a_share.csv" or bool(
        DIVIDEND_DETAIL_PATTERN.fullmatch(relative_path.name)
    )
