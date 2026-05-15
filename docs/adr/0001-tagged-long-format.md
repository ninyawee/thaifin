---
status: accepted
---

# Tagged long-format for financial line items

The published `financial_lines` table is shaped as one row per `(symbol, period, statement, concept, raw_label_th, value, audit_basis, consolidation, filing_id)` — long-format with both a curated **concept** ID and the original Thai **raw label** preserved per row. A separate `concepts.parquet` is the editorial product mapping concepts → labels, with an optional `xbrl_ref` column for forward compatibility with the IFRS/TFRS XBRL taxonomy.

## Considered options

- **Raw passthrough per filing** — Mirror each XLS as-is into parquet, no normalization. Rejected: filings vary in shape across companies and across years (column positions shift, line counts differ); cross-company queries become "compare anyone's pile of Thai strings."
- **Wide pre-joined (Compustat-style)** — One row per `(symbol, period)`, one column per concept. Rejected: every new concept requires a schema migration that breaks pinned consumers; doesn't preserve the long-tail raw labels for audit.
- **All three layers (raw + tagged + wide)** — Build raw, tagged, and wide in sequence. Rejected for v1: triples the engineering surface for marginal additional value when the tagged layer can be pivoted to wide on demand client-side.
- **No dictionary, raw labels only** — Lowest maintenance, but breaks the "research-grade" framing since cross-company queries become impossible without users writing their own mapping.

## Consequences

- The **concept dictionary IS the editorial product**. Quality of the dataset = quality of the dictionary. Mapping rules must be reviewable (PRs against `concepts.parquet`) and auditable (each rule cites the raw labels it matches).
- Consumers pivot to wide format client-side: `df.pivot(index=['symbol','period'], columns='concept', values='value')`.
- Adding a new concept is non-breaking: existing consumers' queries continue to work; new column appears for those who query it.
- The `xbrl_ref` column is nullable. For thaifin-specific concepts with no IFRS analog (e.g., `cash_cycle`), it stays null.
- Raw labels are preserved per row even when tagged, so any concept-mapping bug can be retroactively diagnosed and fixed without re-downloading filings.
