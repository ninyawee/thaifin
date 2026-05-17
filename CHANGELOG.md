# Changelog

All notable changes to `thaifin` are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] / v2.0.0

This is the v2 line: a research-grade redistributable dataset assembled
from primary Thai SEC IDISC filings, plus a new library surface that
streams parquet over HTTP via DuckDB. The v1 live-HTTP path
(Finnomena + Thai Securities Data) stays available for one major version.

### Added

- **Dataset source toggle** on `Stock(...)`. Pass `source="dataset"` to
  read from the HuggingFace-hosted `ninyawee/thaifin-financials` parquet,
  or `source="live"` to keep v1 behavior. Dataset is the new default.
- **New properties** on `Stock(..., source="dataset")` (Tagged long-format
  → wide DataFrames per period):
  - `.income_statement`, `.balance_sheet`, `.cash_flow_statement`
  - `.notes` (markdown text per period)
  - `.auditor_report` (one row per filing: opinion, signing date, etc.)
  - `.capex` (already in v1.x.99 tracer)
- **DuckDB streaming** with session-level `lru_cache` (size 128, key
  `(sql, revision)`). Repeat queries in the same process do not re-hit
  the network. Clear with `DatasetClient.clear_cache()`.
- **Offline mode**: `thaifin.download_dataset(revision=...)` mirrors a
  revision into `~/.cache/thaifin/<revision>/` (overridable via
  `THAIFIN_CACHE_DIR`). After download, `DatasetClient` and the
  Polars-LazyFrame helpers route through the local cache automatically.
- **Revision pinning**: `thaifin.set_data_revision("2026.05")` /
  `thaifin.get_data_revision()`. Per-instance overrides via
  `Stock(..., revision=...)` still win.
- **Power-user accessors** returning `pl.LazyFrame` against the active
  revision: `thaifin.financial_lines()`, `thaifin.concepts()`,
  `thaifin.auditor_reports()`, `thaifin.notes_text()`.
- **`polars`** added as a dependency for the LazyFrame surface.

### Changed

- `Stock(symbol)` (no `source=` argument) now uses the dataset path and
  emits a `DeprecationWarning`. Pass `source="live"` or
  `source="dataset"` explicitly to silence. The default-flip is locked
  for v3.0; for v2 the old behavior is one keyword away.

### Deprecated

- Implicit `source` on `Stock()`. The default will become *explicit only*
  in v3.0 — code that relies on the v1 implicit `"live"` should pin
  `source="live"` now.

### Migration

#### v1.x → v2.0 (live → dataset)

The fastest path is to keep your existing code:

```python
# v1.x behavior, unchanged in v2.0
df = Stock("PTT", source="live").quarter_dataframe
```

To opt in to the dataset path:

```python
# v2.0
df = Stock("PTT", source="dataset").quarter_dataframe
```

#### Column-name rename map

The dataset uses the Tagged long-format with curated `concept` IDs.
Common Finnomena → thaifin-v2 concept names:

| v1.x (Finnomena column) | v2.x (concept) | Notes |
|---|---|---|
| `Cash` | `cash` | |
| `DA` | `depreciation_amortization` | |
| `EbitDATTM` | `ebitda` | Derived in v2 (EBIT + D&A); v1 was a vendor TTM aggregate. |
| `EarningPerShare` | `eps_basic` | |
| `Revenue` | `revenue` | |
| `NetProfit` | `net_profit` | |
| `OperatingActivities` | `ocf` | Operating cash flow. |
| `InvestingActivities` | `investing_activities` | |
| `FinancingActivities` | `financing_activities` | |
| `Asset` | `total_assets` | |
| `Equity` | `equity` | |
| `TotalDebt` | `total_liabilities` | **Conceptual difference**: v1 `TotalDebt` was a vendor-defined "interest-bearing debt" rollup; v2 `total_liabilities` is the audited Balance-Sheet liabilities total. The two are not the same. Compute interest-bearing debt explicitly via `short_term_debt + long_term_debt` in v2 if you need the v1 semantic. |

#### Migration tip

> `Stock("PTT", source="live").quarter_dataframe` keeps the v1.x DataFrame
> shape and column names intact while you migrate consumers one by one.

