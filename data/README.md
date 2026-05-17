# `data/` — committed inputs to the dataset pipeline

This directory holds **editorial inputs** to the pipeline that builds
`hf.co/datasets/ninyawee/thaifin-financials`. These files are PR-reviewable;
the pipeline treats them as ground truth.

## Files

### `concepts.csv`

The curated **concept dictionary**. Maps short stable English IDs (`capex`,
`revenue`, `gross_profit`) to their canonical Thai label and observed aliases
in real Thai SEC filings, plus an optional IFRS XBRL ref for cross-walks.

See [`CONTEXT.md`](../CONTEXT.md#concept) for the formal definition of
**Concept** and [`docs/adr/0001-tagged-long-format.md`](../docs/adr/0001-tagged-long-format.md)
for why the dictionary is structured as a sidecar table rather than baked into
the column schema.

The pipeline converts this CSV to `concepts.parquet` at build time.

## Curation rules

1. **No fabricated labels.** Every `label_th` and every entry in `aliases_th`
   must be observed verbatim in at least one real Thai SEC filing. Cite the
   source (symbol + period + sheet + row) in the PR description.
2. **Concept IDs are stable.** Renaming a `concept` is a **breaking change**
   for dataset consumers. Add new concepts; don't rename existing ones.
3. **Aliases extend existing rows.** If a new filing uses a different Thai
   phrasing for an already-known concept, append it to that row's `aliases_th`
   (pipe-separated). Do not create a duplicate concept.
4. **Statement-scoped.** A concept lives in exactly one statement
   (`BS` / `IS` / `CF` / `EQ`). The mapper uses `(statement, label_th)` as
   the join key, so `revenue` will never accidentally match a balance-sheet row.
5. **Omit when uncertain.** If a Thai label doesn't appear cleanly in any
   inspected filing — or the concept is a derived metric (EBITDA, FCF,
   net_debt) computed from other lines — leave it out. Better an empty cell
   than a mislabeled one.
6. **`xbrl_ref` is conservative.** Map only when confident the IFRS taxonomy
   ID applies. Empty is fine; mislabeled is not.

## Validation

A unit test (added in slice #15) reads `concepts.csv`, asserts:

- All 6 columns present on every row
- `statement` is one of `BS`/`IS`/`CF`/`EQ`
- No duplicate `concept` IDs
- `concept` is snake_case
- The `apply_concepts.py` step achieves a coverage threshold against
  PTT's full filing history before the build is allowed to publish

## v0 sources

The initial 26 concepts were anchored in two filings:

- **PTT FY2025** (annual, audited) — most line items present
- **COM7 2025-Q1** (quarterly, reviewed) — provides aliases for shorter
  quarterly-format phrasings

As the pipeline ingests more symbols, aliases will accumulate via PRs.
