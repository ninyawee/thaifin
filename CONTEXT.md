# thaifin

`thaifin` is a Python library and a companion research dataset for Thai listed-company fundamentals. The library exposes a small Python API; the dataset is a versioned, redistributable artifact built from primary regulatory filings (Thai SEC IDISC).

This file is the project's shared language. When you change a term here, change it everywhere.

## Language

### Sources & filings

**Filing** (งบการเงิน):
A single regulatory submission a Thai listed company makes to the SEC. Realized on disk as one zip containing three documents: `FINANCIAL_STATEMENTS.XLS`, `NOTES.DOC`, `AUDITOR_REPORT.DOC`.
_Avoid_: "report", "release", "submission" (overloaded).

**Statement type**:
Which of the four primary financial statements a numeric line belongs to. One of `BS` (Balance Sheet, งบฐานะการเงิน), `IS` (Income Statement, งบกำไรขาดทุน), `CF` (Cash Flow, งบกระแสเงินสด), `EQ` (Changes in Equity, งบการเปลี่ยนแปลงส่วนของผู้ถือหุ้น).
_Avoid_: "sheet" (XLS-implementation term).

**Audit basis**:
Confidence level of a filing. `audited` (ตรวจสอบ, annual filings) or `reviewed` (สอบทาน, quarterly filings). Different filings of the same period can exist with different bases.

**Consolidation**:
Reporting scope. `consolidated` (รวม, parent + subsidiaries) or `company` (เดี่ยว, parent only). A filing typically contains both columns side-by-side.

**Period**:
The fiscal period a filing reports. Quarterly → `YYYYQq` (e.g. `2025Q4`). Annual → `YYYY`. Fiscal-year-end is per company.

### Artifact & schema

**Dataset / Artifact** (interchangeable):
The published, versioned bundle of parquet files (plus raw mirrors) derived from filings. Hosted on HuggingFace Datasets at `hf.co/datasets/ninyawee/thaifin-financials` (canonical) with revisions tagged per build (e.g., `2026.05`). Distributed independently of the Python library.
_Avoid_: "database", "snapshot" (reserved for a specific point-in-time copy of one company's history).

**Revision** (HF terminology, reused here):
A specific published version of the dataset on HuggingFace, addressed by a git ref (tag or commit). The library pins a default revision per library release; users can override with `thaifin.set_data_revision(...)`.

**Streaming access**:
The library's default read pattern. DuckDB executes parquet queries over HTTP range requests directly against the HF-hosted file, with no local cache by default. Each session memoizes repeated queries in memory. `thaifin.download_dataset()` is the opt-in offline path.

**Snapshot**:
One company's complete known filing history at a specific point in time. The dataset is a set of snapshots assembled at the same build time.

**Concept**:
A canonical line-item identifier in the tagged long-format. Example: `capex`, `revenue`, `total_debt`. Concepts are stable English identifiers curated by the project (~80–150 high-value lines at v1). Each concept may carry an optional **XBRL ref** to the IFRS/TFRS taxonomy ID, enabling future cross-walks to global datasets without renaming consumer-facing fields.

**XBRL ref**:
The IFRS/TFRS taxonomy concept ID associated with a thaifin concept (e.g., `capex` → `ifrs-full:PaymentsToAcquirePropertyPlantAndEquipment`). Stored as a sidebar column in `concepts.parquet`. Nullable for thaifin-specific concepts that have no standards mapping (e.g., `cash_cycle`).

**Raw label**:
The original Thai text of a financial-statement line as it appears in `FINANCIAL_STATEMENTS.XLS`. Preserved verbatim per row for audit.

**Tagged long-format**:
The shape of the primary line-items table. Each row is `(symbol, period, statement, concept, raw_label_th, value, audit_basis, consolidation, filing_id)`.
_Avoid_: "normalized", "long-form" (vague).

**Concept dictionary**:
The curated mapping from concepts → raw labels. Lives alongside the dataset as `concepts.parquet`. The dictionary IS the editorial product of the project; the rest of the pipeline is mechanical.

### Filing companions

**Notes** (NOTES.DOC, หมายเหตุประกอบงบการเงิน):
The narrative + supporting tables that accompany financial statements. Typically ~1 MB DOC file. Contains segment reporting, accounting policies, related-party transactions, contingencies, etc. Distilled into the dataset as text (markdown extraction) plus selected structured tables in later layers.

**Auditor report** (AUDITOR_REPORT.DOC, รายงานของผู้สอบบัญชี):
The auditor's signed opinion on a filing. Structured into one row per filing with fields: `auditor_firm`, `opinion_type` (`unqualified` / `qualified` / `adverse` / `disclaimer`), `signing_date`, `signing_partner`, `going_concern_emphasis` (bool), `raw_text_md`.

## Relationships

- A **Filing** belongs to exactly one company (symbol) and one **Period**, with one **Audit basis**.
- A **Filing** produces rows in three dataset tables: `financial_lines` (tagged long-format), `notes_text`, `auditor_reports`.
- A **Concept** maps to many **Raw labels** (across companies, industries, and years); the **Concept dictionary** is the curated mapping.
- A row in `financial_lines` carries both **Consolidation** values for the same `(symbol, period, concept)` — represented as two rows differing in the `consolidation` column.

## Flagged ambiguities

- "financial statement" was used ambiguously to mean (a) the whole filing zip, (b) one of the four statement types (BS/IS/CF/EQ), and (c) the XLS file inside the zip. Resolved: **Filing** = the zip; **Statement type** = which of BS/IS/CF/EQ a line belongs to; the XLS is just `FINANCIAL_STATEMENTS.XLS`.
- "snapshot" was used to mean both a one-company history and the published dataset. Resolved: **Snapshot** = one company's history at a point in time; **Dataset** / **Artifact** = the published bundle.

## Example dialogue

> **Researcher:** "Pull me PTT's CapEx for the last 10 years."
> **Library user:** "I'll filter `financial_lines` where `symbol = 'PTT'`, `concept = 'capex'`, `consolidation = 'consolidated'`, then group by **Period**."
> **Researcher:** "Audited values only — I don't trust the reviewed Q1–Q3."
> **Library user:** "Add `audit_basis = 'audited'` — that filters to annual filings only, which gives FY totals but not quarter-level CapEx."
> **Researcher:** "Right, and I need the going-concern flag for each year too."
> **Library user:** "That's in `auditor_reports`, joined on `(symbol, period)`."
