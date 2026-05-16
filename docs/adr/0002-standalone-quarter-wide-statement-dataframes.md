---
status: accepted
---

# Standalone-quarter wide statement DataFrames

The dataset-mode statement accessors (`Stock.income_statement`, `Stock.balance_sheet`, `Stock.cash_flow_statement`) return a wide DataFrame indexed by fiscal year (`PeriodIndex(freq='Y')`) with a `MultiIndex` of `(concept, period_type)` on columns. For flow concepts (IS, CF), `period_type ∈ {Q1, Q2, Q3, Q4, FY}` with `Q1..Q4` as standalone-per-quarter values derived from the YTD-as-stored raw filings, and `Q4 = FY − Q3_YTD`. For stock concepts (BS, EQ), `period_type ∈ {Q1, Q2, Q3, FY}` — no `Q4` column, since Thai SEC IDISC publishes no Q4 filing and a balance-sheet snapshot has no standalone-quarter analogue.

The per-concept `Stock.capex` property is removed. Callers reach concepts through their parent statement: `stock.cash_flow_statement['capex']` returns the year × `{Q1, Q2, Q3, Q4, FY}` slice in the (3a) shape.

## Context

Thai SEC IDISC publishes three reviewed quarterlies (Q1/Q2/Q3) plus one audited annual filing per fiscal year. There is no separate Q4 filing — the audited annual is the year-end anchor. Quarterly IS and CF line items are recorded **year-to-date** in the raw XLS: Q1 = 3M, Q2 = 6M-YTD, Q3 = 9M-YTD. Balance-sheet line items are point-in-time snapshots.

The v1 `Stock.capex` returned a single `pd.Series` indexed by raw `period` strings (`"2016"`, `"2016Q1"`, `"2016Q2"`, …), interleaving the audited annual with the reviewed YTD quarterlies, and silently omitting Q4 because no Q4 row exists in the dataset. This was diagnosed as confusing in practice ("why no Q4?", "why are year and quarter values mixed?") and the underlying YTD semantics meant `.pct_change()` and other natural per-quarter operations gave nonsense.

## Decision

Statement accessors expose **standalone-quarter values for flow concepts** and **per-filing snapshots for stock concepts**, with the shape, classification, and edge-case behavior chosen to make the right thing the easy thing:

1. **Standalone derivation for flows.** `Q1 = Q1_YTD`, `Q2 = Q2_YTD − Q1_YTD`, `Q3 = Q3_YTD − Q2_YTD`, `Q4 = FY − Q3_YTD`. Stock concepts use the per-filing snapshot unchanged.

2. **Wide DataFrame with `(concept, period_type)` `MultiIndex` columns.** Rows are years; columns are tuples. `stock.cash_flow_statement['capex']` returns the (3a) year × `{Q1..FY}` slice — the canonical single-concept shape — without a separate helper.

3. **Per-statement column set.** BS and EQ use `{Q1, Q2, Q3, FY}` (no Q4). IS and CF use `{Q1, Q2, Q3, Q4, FY}`. The shape encodes the semantics; no structurally-NaN or structurally-redundant columns.

4. **Single-concept properties removed.** `Stock.capex` is dropped. Users go through `stock.cash_flow_statement['capex']`. Avoids committing to 80–150 hand-rolled properties on `Stock` as the concept dictionary grows.

5. **Flow vs stock classification is structural.** Derived from `statement`: `IS|CF → flow`, `BS|EQ → stock`. No per-concept override column in `concepts.csv`.

6. **NaN-on-gap, strict.** Missing input ⇒ NaN in the dependent cell. No best-effort gap-filling. The YTD-as-stored values remain recoverable as `df[concept][['Q1','Q2','Q3']].cumsum(axis=1)` when the chain is complete; a dedicated `_as_reported` accessor is deferred until a real auditor-reconciliation use case arrives.

7. **`PeriodIndex(freq='Y')` on the year axis** — consistent with the v1 `yearly_dataframe` accessor.

## Considered options

- **Single Series, mixed periods (status quo).** Rejected: produces the "Q4 missing, mixed year-and-quarter values" confusion that motivated this ADR. Quarterly values are YTD-as-stored, so `pct_change` / `rolling` are meaningless.
- **Two accessors per statement (`.income_statement` quarterly + `.income_statement_annual`).** Rejected: doubles the accessor count, and the user would still need to know which to reach for. The wide MultiIndex covers both shapes in one object via `df.xs('FY', level=1, axis=1)`.
- **Long-format DataFrame with `period_type` column.** Rejected: loses convenient column-arithmetic (`df['capex','FY'] - df['capex','Q3']`), harder to panel-join across companies.
- **Uniform 5-column set on BS, with `Q4` always NaN.** Rejected: a structurally-NaN column is a footgun — someone will eventually call `df[('cash','Q4')].mean()` and get NaN with no warning.
- **Uniform 5-column set on BS, with `Q4 = FY` (duplicate).** Rejected: bundles the audited year-end into a column labeled `Q4` (reviewed-basis everywhere else), silently changing the column's audit semantics.
- **Best-effort gap-filling.** Rejected: a missing intermediate YTD smeared into a downstream quarter looks correct but isn't. Strict NaN keeps bad data honest.
- **Per-concept `kind` column in `concepts.csv`.** Rejected: the rule is structural (a CF row is by construction a flow); a redundant column invites it being inconsistent with `statement`.
- **Keep `Stock.capex` as a thin wrapper, change its return type.** Rejected: a silent return-type change from `Series` to `DataFrame` is the worst kind of breaking change. Removing the property is cleaner and surfaces the breakage at import-time.

## Consequences

- **The statement accessors are the single source of truth.** Any per-concept convenience (if added later) is a thin wrapper over `statement[concept]`, not a parallel query path.
- **Audit basis is structurally encoded by column.** For IS/CF: `Q1..Q3` are reviewed-source, `Q4` is mixed-basis (audited FY − reviewed Q3-YTD), `FY` is audited. For BS: `Q1..Q3` reviewed, `FY` audited. The convention is documented per accessor; no per-row `audit_basis` tag in the returned frame.
- **`EQ` (changes-in-equity) is treated as stock for now.** Only the closing-balance rows are emitted; period-movement rows from EQ are not surfaced. If a future need for EQ period movements arises, it gets its own ADR (likely a separate `equity_movements` accessor rather than re-shaping EQ to a flow).
- **The YTD-as-stored view is not exposed in v2.** Recoverable via cumsum on the standalone Q-columns when the chain is complete. A dedicated `_as_reported` accessor is a follow-up if a user surfaces it.
- **`Stock.capex` and its v1 callers break.** Documented in `CHANGELOG.md`; the `_DEFAULT_SOURCE` sentinel already flags v0.x → v2 as the API-shape-flux window.
- **The dataset storage layer is unchanged.** `financial_lines.parquet` keeps the tagged long-format from ADR-0001 with YTD-as-stored raw values. All derivation is library-side, so any HF revision works against the new API.
