# FutureLedger TODOs

## P2: Bank Deposit Rate Scanner for v2

Status: Deferred

FutureLedger v0 should focus on the reliable A-share dividend research report.
Bank fixed-deposit rate collection is deferred to v2 because public bank pages
change frequently, require source-specific parsers, and would add a separate
failure mode before the core dividend pipeline is proven.

Context:
- v0 scope: local Python CLI that generates a reproducible A-share dividend
  research workbook.
- v2 scope: collect public bank deposit rates from official pages with
  source-specific parsers, raw snapshots, parser status, and source_errors rows.
- Do not mix bank-rate scraping into the v0 dividend pipeline.

Suggested v2 acceptance criteria:
- Parse at least 5 official bank deposit-rate pages or report parser failures
  gracefully.
- Store source URL, fetched_at timestamp, parser_status, and raw snapshot path.
- One broken bank page must not fail the whole report.
- Tests must separate deterministic parser fixtures from live network checks.
