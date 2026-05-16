# Iteration loop methodology — driving `concepts.csv` coverage to 90%+

> Source of truth lives in this repo. Mirrored on GitHub issue #11 (PRD). When PR #12 lands, this doc moves to `master`.

## TL;DR

Across one extended session we proved an iteration loop that drives concept-mapping coverage in `financial_lines.parquet` from a parser-fix baseline of ~68% to **≥90% per symbol** for symbols the dataset can parse. Method, evidence, and remaining work are captured below so the same loop can run on the next batch of symbols (AOT / CPN / ADVANC are queued).

## Per-symbol status (as of session end)

**Scope expanded mid-wrap: now SET100 (was 10-symbol seed).** All 100 SET100 symbols have complete zip downloads at `data/sec_idisc/zips/` (~2.6 GB, 108 symbols actually — 100 SET100 + 8 extras). Parsing → publishing to HF is the next bottleneck. The 6 symbols below have been ground; the other 94 are unparsed at session end.

### Symbols already ground (published on HF main)

| Symbol | Filings | Start | End | Δpp | Cycles | Status |
|---|---|---|---|---|---|---|
| **PTT** | 40 | 70.30% (pre-parser-fix) / 68.07% (post) | **90.68%** (then 90.80% with re-tag) | +22.61 | 10 + 1 grind | ✅ goal met |
| **BBL** | 119 | 8.04% (initial multi-symbol cycle 1) → 25.05% (post bank concepts) | **90.38%** | +65.33 | 5 | ✅ goal met |
| **KBANK** | 116 | 7.89% → 21.38% → 44.80% (compounded from BBL) | **91.01%** | +69.63 | 5 (1+4) | ✅ goal met |
| AOT | 89 | 28.24% → 31.62% (cross-industry compounding) | 32.62% | — | 0 | 🔜 next in queue |
| CPN | 116 | 10.61% → 11.46% | 11.46% | — | 0 | queued |
| ADVANC | 117 | 12.28% | 12.28% | — | 0 | queued (only 114 rows total — likely parser quirk) |

### Symbols downloaded but NOT yet parsed (94)

All other SET100 symbols. Zips in `data/sec_idisc/zips/<SYM>/<filing_id>.zip`. Indicative volumes from spot-checks: BBL 138, SCC 229, BDMS 134, KBANK 132, CPALL 92. Each symbol has 17–230 filings.

### Parser-blocked even after parsing attempts

These symbols WERE attempted in the 9-stock seed backfill but produced 0 rows because their sheet names don't match the current parser regex:
- **SCC** (~210 filings) — bare numeric sheets `1,2,3,4,5`
- **BDMS** (~117 filings) — `BS&PL Thai`, `PL-T (3)`, `CE Thai`
- **CPALL** (~91 filings) — `BS 3-5`, `PL3M-6-7`, `CF-11-14`
- **SCB** (~17 filings) — parser produced 0 rows despite bank format (different from BBL/KBANK; investigate at #24)

Per #24 (parser sheet-name variants), these need parser work before dictionary iteration can touch them.

### Global coverage on HF main

**47.39% → 68.36%** across the BBL+KBANK arc (across the 6-symbol seed bundle). New global metric will be computed when the 94 not-yet-parsed symbols land in the parquet — expect a temporary dip (new unmapped rows) followed by recovery as dictionary cycles process the new vocabulary.

## The iteration loop (proven recipe)

For each symbol, repeat until coverage ≥ 90% or last cycle adds < 1pp:

1. **Probe top-unmapped** for the symbol against the latest HF revision via DuckDB:
   ```sql
   SELECT statement, raw_label_th, COUNT(*) AS occ
   FROM read_parquet('https://huggingface.co/datasets/ninyawee/thaifin-financials/resolve/<rev>/financial_lines.parquet')
   WHERE symbol = '<SYM>' AND concept IS NULL AND length(raw_label_th) >= 10
   GROUP BY statement, raw_label_th ORDER BY occ DESC LIMIT 30
   ```
2. **LLM-style classify** each candidate:
   - **ALIAS** — variant of an existing concept (shorter form, gain/loss-only, missing prefix, etc.) → append to `aliases_th`
   - **NEW CONCEPT** with confident IFRS counterpart → add a fresh row with `xbrl_ref` populated
   - **DUAL-STATEMENT entry** — same concept appearing in another statement (e.g., bank IS line appearing in CF reconciliation) → add a second row with the new statement type
   - **SKIP** if no IFRS counterpart OR known-unmappable (PTT perpetual sub-bonds, gas-station-lease-termination, dynamic-text rows like "ทุนจดทะเบียน หุ้นสามัญ 3,048,614,697...")
3. **Apply surgically** to `data/concepts.csv` via Python that splits on `,` and reconstructs — avoid `csv.writer` which re-quotes every line and ruins the diff
4. **Re-tag in-memory** using `thaifin.concepts.apply_concepts` — pulls the prior revision's parquet, re-tags, returns delta
5. **Publish HF revision** (e.g., `v0.seed10.bbl1`, `bbl2`, …) using `fnox exec -- python …` so the token never lands in argv
6. **Commit per cycle** with a structured message: cycle number, alias/concept counts, before/after coverage, top contributors

Per-cycle wall time: ~5–10 min of foreground work (one Claude turn).

## The Bank-CF-Reconciliation discovery (load-bearing finding)

Bank cash-flow statements use the IFRS indirect method: they list IS / BS items as reconciliation adjustments under the CF sheet. Examples from BBL:
- `[CF] รายได้ดอกเบี้ยสุทธิ` — net_interest_income (IS concept, appears here as a CF adjustment)
- `[CF] เงินรับฝาก` — deposits_from_customers (BS concept, appears here as CF change)

The `ConceptMapper` requires `(statement, label)` match, so these CF appearances never matched the IS-typed or BS-typed dictionary entries. Solution: add **dual-statement entries** — same `concept` ID, second row with `statement=CF`. Concept namespace stays clean; lookup matches both contexts.

This single insight unlocked +25.28pp on BBL in cycle 2 alone. Now baked into the recipe for any new bank/insurer/REIT symbol.

## The "compounding effort" pattern (also load-bearing)

Per the grilling decision: **grind concept-dense symbols first**. Dictionary additions for BBL automatically lifted KBANK by 24.55pp before KBANK's own grind started. The order matters:

1. BBL (bank, ~4750 rows) — gives the bank vocab
2. KBANK (bank, ~6310 rows, 1.3× BBL) — gets ~70% of its work done by BBL's compounding
3. AOT (state-enterprise/transport, ~6759 rows) — next; will share some cross-industry concepts but distinct vertical
4. CPN (REIT, ~5419 rows) — own REIT vocab; minimal compounding from prior
5. ADVANC (telecom, only ~114 rows) — last; just sanity-check

The 5-symbol order was locked via `/grill-with-docs` before execution and verified empirically.

## Decisions captured (would be invisible without this doc)

| When | Question | Decision | Why |
|---|---|---|---|
| Cycle 0 PTT | Coverage definition? | **Row coverage**, target 90% (not 100% literal, not headline-only) | User picked. 100% requires inventing concepts no one queries; 90% is the practical asymptote where IFRS-mappable concepts saturate |
| Cycle 0 | Curation engine? | **LLM-style judgment** in foreground, tiered confidence | Frequency-driven + gap-detection signals; auto-only is unsafe (cross-statement false positives) |
| Cycle 0 | Sequencing | Parser fix FIRST, then dictionary cycles | Line-wrap fragments poison the gap signal; eliminating them lifts the signal quality 10× |
| BBL cycle 1 | Add concepts without IFRS refs? | **No** — IFRS-required for new concepts | Keeps dictionary anchored to a real taxonomy; rejects niche per-company items; aliases for existing concepts have NO IFRS requirement |
| BBL cycle 2 | How to handle bank CF reconciliation lines? | **Dual-statement entries** — same concept ID, second row with statement=CF | The CF entries are the same conceptual line appearing as a reconciliation adjustment. Each lookup is statement-typed so a 2nd dictionary row is needed |
| Throughout | "ทุนจดทะเบียน หุ้นสามัญ 2,393,260,193 หุ้น มูลค่าหุ้นละ 10 บาท" rows | **Skip** | Dynamic-text disclosures with embedded counts — vary per company per period. Can't alias generically without a regex matcher (deferred enhancement) |

## Architectural artifacts produced this session

### HF revisions (chronological)

PTT-only:
- `v0.ptt.1` (parser-fix baseline, 68.07%)
- `v0.ptt.2` through `v0.ptt.11` — one per cycle (1.11pp to 3.92pp per cycle)
- `v0.ptt.12` — post-grind, 90.68%

Multi-symbol:
- `v0.seed10` (initial 10-symbol bundle, 41.55%)
- `v0.seed10.1` (post-multi-symbol cycle 1, 47.39%)
- `v0.seed10.bbl1` through `v0.seed10.bbl5` — BBL grind (25.05% → 90.38%)
- `v0.seed10.kbank1` through `v0.seed10.kbank5` — KBANK grind (44.80% → 91.01%)
- `v0.seed10.bugfix1` — CSV comma-shift fix (no coverage delta; structural)

### `data/concepts.csv` v0.2 dictionary

314 rows after 22+ cycles (was 26 at session start). Mix of:
- ~120 cross-industry concepts (revenue/cogs/equity/capex/etc.)
- ~80 bank-specific (interest_income, loans, deposits, NPLs, IFRS-9 FVPL/FVOCI, indirect-method CF reconciliation entries, perpetual subordinated instruments)
- ~15 IFRS-9 / TFRS-16 specific (FVOCI debt + equity, right-of-use assets, lease liabilities)
- ~10 equity-statement transactions (opening balances, dividends to NCI, etc.)
- ~12 derivative/hedge accounting concepts
- ~10 deferred tax / OCI tax concepts
- The rest: industry-specific (REIT/transport/insurance hints), historical/legacy variants

Every concept has either an `ifrs-full:*` XBRL ref OR is an alias of one that does.

### Code changes

| Path | What |
|---|---|
| `thaifin/parsers/financial_statements.py` | Parser fix #17: line-wrap merge with value-continuity guardrail + hidden-sheet filter + currency-scale detection |
| `thaifin/stock.py` | `.capex` property restored (regression from #15 — PRD user story #2 lookup) |
| `data/concepts.csv` | The dictionary (288 rows added across cycles) |
| `scripts/build_seed10.py` | Multi-symbol backfill driver (added by parallel agent; bundles operational fixes for IPv6/UA/WAF until #21 lands) |

### Open follow-up issues (durable references)

- **#11** — PRD (umbrella, still open)
- **#19** — Per-industry coverage gate (the global metric will mislead once non-industrials dominate)
- **#20** — Parser robustness gaps (16-item checklist; **#24 sub-task is the blocker for SCC/CPALL/SCB/BDMS**)
- **#21** — Extract SEC IDISC download as standalone module + CLI (parallel session in progress — see uncommitted files)

## Resume here — concrete next-session plan

### Prerequisites

```bash
git fetch origin
git switch feat/v2-dataset-pipeline
git pull --ff-only
# Verify dictionary is at 314 rows:
wc -l data/concepts.csv  # should be ~333 (314 data + 19 comment lines)
# Verify last commit:
git log --oneline -1  # should be fe2adc5 'BBL + KBANK grinds both hit 90%+ + CSV comma-shift bugfix'
```

There are uncommitted files from a parallel session working on #21 (SEC IDISC module extraction):
```
M .gitignore                                 # adds data/sec_idisc/ ignore
M thaifin/sources/sec_idisc/discovery.py     # #21 refactor in progress
M thaifin/sources/sec_idisc/fetcher.py       # ditto
M thaifin/sources/sec_idisc/symbols.py       # ditto
?? data/set100_symbols.txt                   # 100-symbol SET100 list, valuable
?? data/setmai_symbols.txt                   # 866-symbol SET+mai universe
?? scripts/recover_missing_filings.py        # #21 helper
?? thaifin/sources/sec_idisc/__main__.py     # #21 CLI entry point
?? thaifin/sources/sec_idisc/_transport.py   # #21 IPv6/UA/WAF transport layer
```

Don't commit these blindly — the parallel session author should finalize and commit. They're left so the next session can see the parallel work and merge cleanly.

There's also one stash:
```bash
git stash list  # stash@{0}: WIP on feat/v2-dataset-pipeline: d848240 ...
```
Check before dropping — may contain useful WIP.

### Next loop iteration — TWO PARALLEL TRACKS

#### Track A — finish parsing SET100 (blocker)

The parallel session downloaded all 100 SET100 zips into `data/sec_idisc/zips/`. They need to be parsed → `financial_lines.parquet` → uploaded to HF before the iteration loop can target the new symbols.

Likely path: extend `scripts/build_seed10.py` (or its #21 successor) to iterate the SET100 list, reusing the already-cached zips:

```bash
# Confirm all SET100 symbols have zips
uv run python -c "
import os
with open('data/set100_symbols.txt') as f: target = {l.strip() for l in f if l.strip()}
have = set(os.listdir('data/sec_idisc/zips'))
print(f'{len(target & have)}/{len(target)} SET100 symbols have zips')
print(f'Missing: {sorted(target - have)}')"
# Expect: 100/100 (verified 2026-05-16 evening)

# Then run a parse-only driver over the cached zips
# (parallel session's recover_missing_filings.py + build_seed10.py
#  should be the seeds for this — they're uncommitted at session end)
```

After parse + publish (probably `v0.set100.0` revision), re-tag globally with the current 314-concept dictionary. Expect:
- Bank symbols (KBANK already done; new: BAY, KTB, TMB, TISCO, KKP) will have ~25-40% baseline from BBL+KBANK vocab
- Industrials (BANPU, SCC*, BCP, TOP, IRPC, PTTEP, GPSC) will lift from PTT vocab
- REITs (CPN already done; new: WHA, LH, SPALI, ANAN, etc.) will need REIT-specific vocab
- Telecom (ADVANC done; new: TRUE, JAS, INTUCH) — small share-count base
- New industries unlocked: insurance (BLA, TIPCO), healthcare (BH, BDMS*, RAM, EKH, CHG), media, food&bev, materials

*\* SCC, BDMS, CPALL, SCB still parser-blocked per #24 even after re-attempt.*

#### Track B — keep iterating the 6 ground symbols' siblings

For each new SET100 symbol, the same iteration loop applies. Order suggestion:
1. **Most concept-dense industries first** (compounding maximised):
   - Banks: BAY, KTB, TMB, TISCO, KKP (will inherit BBL+KBANK's full bank vocab — likely start at 30-50% baseline)
   - Industrial-conglomerates: PTTEP, BANPU, SCC, IRPC, TOP (will inherit PTT vocab heavily)
2. **Then by row count** (most absolute coverage gain per cycle)
3. **REIT/insurance** last — they bring new vocab clusters

Use the proven recipe per the methodology section above. Per-symbol grind: 3-6 cycles. 94 symbols × ~4 cycles avg = ~400 cycles of dictionary work. Total wall time ~30+ hours of focused iteration. Suggested: spawn one grind-agent per industry cluster (5-10 symbols each) for parallelism.

#### Track C — AOT/CPN/ADVANC (the symbols ALREADY parsed at session end)

Resume the iteration loop with **AOT** at 32.62% (state-enterprise transport, multi-auditor rotation observed in scout — SAO → EY → KPMG within 12 months).

```bash
# Probe top-unmapped against latest HF revision:
uv run python << 'PY'
import duckdb
con = duckdb.connect(); con.execute('INSTALL httpfs; LOAD httpfs;')
URL = 'https://huggingface.co/datasets/ninyawee/thaifin-financials/resolve/v0.seed10.bugfix1/financial_lines.parquet'
df = con.execute(f"""SELECT statement, raw_label_th, COUNT(*) as occ FROM read_parquet('{URL}')
WHERE symbol='AOT' AND concept IS NULL AND length(raw_label_th) >= 10
GROUP BY statement, raw_label_th ORDER BY occ DESC LIMIT 30""").fetchdf()
print(df.to_string())
PY
```

Apply the recipe. Expected: 3-4 cycles to hit 90% on AOT. Then CPN, ADVANC.

These three could be done IN PARALLEL with Track A's parse work (Track C is in-process, Track A is throughput-bound on libreoffice).

### Parser unblocks for the 4 zero-row symbols

After dictionary work on parseable symbols stabilizes, attack #24 (parser sheet-name variants). Specific gaps:
- **CPALL**: sheet names like `BS 3-5`, `PL3M-6-7`, `CF-11-14`
- **SCC**: bare numeric sheets `1`, `2`, `3`, `4`, `5`
- **BDMS**: `BS&PL Thai`, `PL-T (3)`, `CE Thai`
- **SCB**: parser produced 0 rows despite bank format (different from BBL/KBANK; investigate)

Estimated unlock: +35-40pp global coverage when these 4 symbols parse. 434 filings × ~150 rows/filing ≈ 60K new rows entering the parquet.

### Library polish (post-dictionary)

`Stock("PTT").capex` works at v0.ptt.12 (restored from regression). After more symbols hit 90%, validate `Stock("BBL").income_statement`, `.cash_flow_statement`, etc., return useful wide DataFrames. The MultiIndex `(concept, period_type)` columns from the slice #15 design may need a friendlier wrapper for common queries.

## Cross-references

- PR: **#12** (draft, feat/v2-dataset-pipeline → master)
- Umbrella PRD: **#11**
- Schema rationale: `docs/adr/0001-tagged-long-format.md`
- Domain language: `CONTEXT.md`
- Original design: `notes/cicd-design.md`
- This doc: `docs/specs/v2-iteration-loop.md` — canonical source for the iteration methodology and per-symbol progress

## Pre-merge checklist (eventual)

- [ ] All non-parser-blocked symbols at ≥90% (currently: PTT ✅, BBL ✅, KBANK ✅, AOT/CPN/ADVANC pending)
- [ ] Per-industry coverage gate (#19) implemented so CI doesn't fail on first bank ingest
- [ ] #20 parser robustness items addressed for the 4 zero-row symbols
- [ ] #21 SEC IDISC module extracted so the WAF/IPv6/UA gotchas are baked in
- [ ] `auditors.csv` consolidated from the 5 scout staging files (`data/auditors.<SYM>.csv` from BBL/AOT/CPALL/SCC/SCB)
- [ ] Final HF revision tagged for v2.0 release (e.g., `v0.public` or version-tag aligned)
- [ ] CHANGELOG.md updated with v1.x → v2.0 column-rename map and migration notes
- [ ] `notes/cicd-design.md` reconciled with this spec (or marked deprecated)
