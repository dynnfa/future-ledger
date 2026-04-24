"""Pipeline orchestration for the dividend scan.

Builds the stock universe, fetches dividends and prices per stock,
computes metrics, and produces ReportTables.
"""

from __future__ import annotations

from future_ledger.domain import ReportTables, RunConfig


def run_scan(config: RunConfig) -> ReportTables:
    """Execute the full dividend scan pipeline.

    Returns populated ReportTables even when individual stocks fail;
    per-stock failures are recorded in source_errors.
    """
    raise NotImplementedError("pipeline.run_scan not yet implemented")
