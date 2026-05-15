# thaifin v2 — CI/CD-built dataset & library design

## Context

The current `thaifin` library (v1.x) is a thin live-HTTP client over two third-party Thai financial-data APIs (Finnomena, Thai Securities Data). It serves ~35 aggregated metrics. **CapEx and every other balance-sheet / cash-flow line item is unreachable** from those sources.

Goal: build and publish a **research-grade redistributable dataset** of Thai listed-company financial statements (Tagged long-format), sourced directly from the primary regulator (Thai SEC IDISC). The library becomes one consumer; researchers in any language can pull the parquet directly from HuggingFace.

This document records the design decisions and the implementation outline. See `CONTEXT.md` for domain language and `docs/adr/0001-tagged-long-format.md` for the schema rationale.

## Locked decisions (from grill)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Primary motivation | (c) Research-grade redistributable dataset |
| 2 | Schema | Tagged long-format (one row per concept × period) |
| 3 | Concept dictionary | Hybrid: ~120 curated concepts + optional XBRL ref |
| 4 | Distribution | HuggingFace Datasets — `hf.co/datasets/thaifin/financials` |
| 5 | Library access | DuckDB streaming over HTTP + session lru_cache + opt-in `download_dataset()` |
| 6 | Existing API | Source toggle: `Stock(symbol, source="dataset"\|"live")`, default `"dataset"` |
| 7 | Cadence | Monthly cron (1st of month, 02:00 UTC) + `workflow_dispatch` |
| 8 | Parser | libreoffice headless → OOXML → openpyxl + python-docx |

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  GitHub Actions: data-build.yml  (monthly cron)                    │
│                                                                    │
│  1. Discover symbols                                               │
│     GET /public/idisc/th/company/listed/{0-9,A-Z}                  │
│     → set of ~800 symbols                                          │
│                                                                    │
│  2. Discover filings per symbol                                    │
│     GET /public/idisc/th/Viewmore/fs-norm?searchSymbol=<S>         │
│     → list of zip URLs (~50 per symbol, ~40K total)                │
│                                                                    │
│  3. Incremental fetch                                              │
│     Diff vs state file (filing_id → sha256) committed in repo      │
│     Download only new/changed zips                                 │
│                                                                    │
│  4. Normalize formats                                              │
│     libreoffice --headless --convert-to xlsx,docx on .XLS/.DOC     │
│                                                                    │
│  5. Parse                                                          │
│     parse_xlsx(financial_statements.xlsx) → tagged_long rows       │
│     parse_docx(auditor_report.docx)       → structured + raw_md    │
│     parse_docx(notes.docx)                → raw_md                 │
│                                                                    │
│  6. Apply concept dictionary                                       │
│     join raw_label_th → concept via concepts.parquet               │
│     unmapped rows stay tagged with concept=NULL                    │
│     CI fails if coverage % drops vs previous build                 │
│                                                                    │
│  7. Compose parquets                                               │
│     financial_lines.parquet  (~500 MB)                             │
│     notes_text.parquet       (~300 MB)                             │
│     auditor_reports.parquet  (~5 MB)                               │
│     concepts.parquet         (~50 KB)                              │
│     filings.parquet          (~2 MB, the index/state)              │
│                                                                    │
│  8. Push to HuggingFace                                            │
│     huggingface_hub upload to hf.co/datasets/thaifin/financials    │
│     git-tag revision: 2026.05, 2026.06, ...                        │
└────────────────────────────────────────────────────────────────────┘
```

## Schema spec

### `financial_lines.parquet`
| column | type | notes |
|---|---|---|
| `symbol` | str | Stock ticker, uppercase |
| `period` | str | `YYYYQq` or `YYYY` |
| `statement` | enum | `BS` / `IS` / `CF` / `EQ` |
| `concept` | str? | Curated ID (e.g., `capex`); null if unmapped |
| `raw_label_th` | str | Original Thai label, preserved verbatim |
| `value` | float64 | THB, raw scale (no thousands/millions abbreviation) |
| `audit_basis` | enum | `audited` / `reviewed` |
| `consolidation` | enum | `consolidated` / `company` |
| `filing_id` | str | Foreign key → `filings.parquet` |

### `concepts.parquet`
| column | type | notes |
|---|---|---|
| `concept` | str | Curated ID, e.g., `capex` |
| `statement` | enum | Which statement this lives in |
| `label_en` | str | Human English label |
| `label_th` | str | Canonical Thai label |
| `aliases_th` | list[str] | Other Thai labels that map to this concept |
| `xbrl_ref` | str? | IFRS/TFRS XBRL ID, nullable |

### `auditor_reports.parquet`
| column | type | notes |
|---|---|---|
| `filing_id` | str | PK |
| `symbol`, `period`, `audit_basis` | | denormalized for query convenience |
| `auditor_firm` | str | e.g., "EY", "KPMG", "PwC", "Deloitte" |
| `opinion_type` | enum | `unqualified` / `qualified` / `adverse` / `disclaimer` |
| `signing_date` | date | |
| `signing_partner` | str? | |
| `going_concern_emphasis` | bool | true if EOM paragraph mentions GC |
| `raw_text_md` | str | Full report as markdown |

### `notes_text.parquet`
| column | type | notes |
|---|---|---|
| `filing_id` | str | |
| `symbol`, `period` | | denormalized |
| `raw_text_md` | str | Full notes as markdown |

### `filings.parquet` (state + provenance)
| column | type | notes |
|---|---|---|
| `filing_id` | str | derived from FILEID, PK |
| `symbol`, `period`, `audit_basis` | | |
| `source_url` | str | Original SEC IDISC zip URL |
| `source_sha256` | str | Of the zip file |
| `fetched_at` | timestamp | |

## Files to create

```
thaifin/
├── CONTEXT.md                         ✓ written
├── docs/adr/
│   └── 0001-tagged-long-format.md     ✓ written
├── notes/
│   └── cicd-design.md                 ✓ this file
├── .github/workflows/
│   ├── pypi.yml                       (exists, unchanged)
│   └── data-build.yml                 NEW — monthly cron pipeline
├── scripts/                           NEW
│   ├── discover_symbols.py            walk /company/listed/{0-9,A-Z}
│   ├── discover_filings.py            per symbol → fs-norm URLs
│   ├── fetch_filings.py               incremental zip download
│   ├── normalize_formats.py           libreoffice headless conversion
│   ├── parse_xlsx.py                  XLSX → financial_lines rows
│   ├── parse_docx_auditor.py          DOCX → auditor_reports row
│   ├── parse_docx_notes.py            DOCX → notes_text row
│   ├── apply_concepts.py              join raw_label → concept
│   └── publish_hf.py                  push to HuggingFace
├── data/                              NEW (input-side, committed)
│   ├── concepts.csv                   the curated dictionary (CSV for PR review)
│   └── state.json                     filing_id → sha256 cache
├── thaifin/
│   ├── stock.py                       MODIFY — add source toggle
│   ├── stocks.py                      MODIFY — add source toggle
│   ├── data/                          NEW
│   │   ├── __init__.py
│   │   ├── client.py                  DuckDB-over-HTTP client + lru_cache
│   │   ├── download.py                thaifin.download_dataset()
│   │   └── revision.py                pin/override active revision
│   └── sources/                       (unchanged, still used when source="live")
└── tests/
    ├── test_data_client.py            NEW — DuckDB streaming tests
    ├── test_parsers.py                NEW — fixture-based XLSX/DOCX parser tests
    └── sample_data/
        ├── PTT_2025Q4.zip             NEW — sample filing for tests
        └── COM7_2025Q1.zip            NEW
```

## Library API changes

### v2.0 — Stock class

```python
class Stock:
    def __init__(
        self,
        symbol: str,
        language: str = "en",
        source: Literal["dataset", "live"] = "dataset",  # NEW
        revision: str | None = None,                     # NEW, only for source="dataset"
    ): ...

    # Existing methods — dispatch by source
    quarter_dataframe: pd.DataFrame          # source="dataset" → DuckDB; source="live" → Finnomena
    yearly_dataframe: pd.DataFrame           # same

    # NEW — only available when source="dataset"
    @property
    def capex(self) -> pd.Series: ...        # convenience: concept="capex"
    @property
    def cash_flow_statement(self) -> pd.DataFrame: ...
    @property
    def balance_sheet(self) -> pd.DataFrame: ...
    @property
    def income_statement(self) -> pd.DataFrame: ...
    @property
    def notes(self) -> pd.DataFrame: ...     # markdown text per period
    @property
    def auditor_report(self) -> pd.DataFrame: ...
```

### Module-level

```python
import thaifin

thaifin.set_data_revision("2026.05")             # pin
thaifin.download_dataset()                       # opt-in offline
thaifin.financial_lines()                        # pl.LazyFrame against streaming source
thaifin.concepts()                               # read concept dictionary
```

## Migration / breaking changes

- **v1.x users** with `Stock("PTT").quarter_dataframe` keep working if they pin `source="live"` — but the default flips to `"dataset"`. The dataset's column names align with the new tagged schema and will *not* be byte-identical to Finnomena's output. **Document this in CHANGELOG with a 1-line migration tip.**
- The `Finnomena` and `ThaiSecuritiesData` source modules stay in `thaifin/sources/` indefinitely (used when `source="live"`). They can be removed in v3 if usage tails off.

## Verification

End-to-end smoke test, runnable locally:

```bash
# 1. Run a single-symbol pipeline end-to-end on PTT
uv run python scripts/discover_filings.py --symbol PTT --limit 3 --out /tmp/test
uv run python scripts/fetch_filings.py --in /tmp/test/filings.json --out /tmp/test/zips/
uv run python scripts/normalize_formats.py --in /tmp/test/zips/ --out /tmp/test/normalized/
uv run python scripts/parse_xlsx.py --in /tmp/test/normalized/ --out /tmp/test/lines.parquet
uv run python scripts/apply_concepts.py --lines /tmp/test/lines.parquet --concepts data/concepts.csv --out /tmp/test/tagged.parquet

# 2. Verify CapEx is present and matches the PTT 2025 Cash flow XLS row 79
duckdb -c "SELECT period, value FROM '/tmp/test/tagged.parquet' WHERE symbol='PTT' AND concept='capex' ORDER BY period"
# Expect: 2025Q4 row with value -159512958954

# 3. Library round-trip after publishing to HF
uv run python -c "
from thaifin import Stock
s = Stock('PTT', source='dataset', revision='2026.05')
print(s.capex.tail())
print(s.auditor_report)
print(s.notes.head())
"

# 4. Diff dataset vs live for validation
uv run python -c "
from thaifin import Stock
ds = Stock('PTT', source='dataset').quarter_dataframe
live = Stock('PTT', source='live').quarter_dataframe
# Compare overlapping columns; tolerance ~0.01% for rounding
"
```

CI integration tests:
- `tests/test_parsers.py` — fixture filings in `tests/sample_data/*.zip` → parse → assert known CapEx values
- `tests/test_data_client.py` — mock HF endpoint → verify DuckDB queries route correctly, lru_cache works
- `tests/public_internet_tests/test_hf_live.py` — slow test that hits real HF dataset

## Known unknowns to revisit

- **Industry-specific concept variants** — banks (no COGS, has interest_income), REITs (no revenue, has property_income), insurers — concept dictionary needs `applicable_industries: list[str]` column or `industry` filter. Defer to v2.1 after first concept dictionary is built and we see the actual variance.
- **Restatements** — when a company refiles a prior period, do we keep both versions or replace? Probably keep both, partition by `filing_id`, mark `superseded_by` in `filings.parquet`. Defer until first observed restatement in production data.
- **Auditor opinion classification** — extracting `opinion_type` from Thai prose is non-trivial; v1 can use simple regex on the auditor report's opening paragraph, with manual override list for misclassifications. LLM extraction is a v2.1 candidate.
- **CI runtime** — first run is ~17h estimated; GitHub Actions free tier has a 6-hour job limit. Either split into 4-letter-bucket parallel jobs, or do a one-time backfill on a beefier machine and let CI handle incremental from there.
