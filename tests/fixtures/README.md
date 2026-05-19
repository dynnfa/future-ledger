# FutureLedger Test Fixtures

Default fixtures are deterministic UTF-8 CSV files used by `uv run pytest`.
They must not require live AKShare access.

## Naming

- `akshare/spot_a_share.csv`
- `akshare/dividend_detail_<symbol>.csv`
- `prices/<symbol>_daily_<start_date>_<end_date>.csv`
- `cache/<stage>/<cache_id>.csv`
- `workbooks/` is reserved for intentionally small golden `.xlsx` files.

Use six-digit A-share symbols and `YYYYMMDD` date ranges in filenames.

## Size

Default CSV fixtures should stay below 100 data rows. If a test needs a larger
fixture to validate large-frame behavior, document the reason in the test that
uses it.

## Live Data

Tests that call AKShare directly live under `tests/live/`, use the
`live_akshare` marker, and are skipped by default. Run them explicitly with:

```bash
uv run pytest tests/live -m live_akshare
```

## Workbook Goldens

Golden workbook fixtures should compare stable workbook structure: sheet names,
headers, cell types, number formats, and representative values. Do not compare
volatile generated timestamps unless the test supplies a fixed workbook timestamp.
