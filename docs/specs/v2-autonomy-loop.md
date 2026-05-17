# v2 autonomy loop — autonomous SET100 grind

> **Status**: design locked via grilling 2026-05-16. Implementation pending launch.
> **Predecessor**: [`v2-iteration-loop.md`](./v2-iteration-loop.md) — the manual-loop methodology this autonomy plan scales up.
> **Branch**: `feat/v2-dataset-pipeline` (PR [#12](https://github.com/ninyawee/thaifin/pull/12))
> **Issue tracker**: PRD [#11](https://github.com/ninyawee/thaifin/issues/11)

## TL;DR

Run the proven per-symbol grind loop autonomously across the 100 SET100 symbols and unblock the 4 parser-blocked ones, with **no human approval gate per cycle**. LLM workers propose dictionary edits; a supervisor applies + tests + publishes serially. Hard safety gates catch regressions. Target wall-clock: ~20h on a 4-worker cluster. Final artifact: HF revision `v0.set100.final` + auto-opened PR with per-symbol coverage report.

## Goal (locked)

**Per-symbol concept-mapping coverage on parseable filing rows ≥90% OR last cycle Δ<1pp OR 8 cycles total**, applied to:

- 100 SET100 symbols (zips already cached at `data/sec_idisc/zips/`)
- 4 of which are parser-blocked today (SCC, CPALL, BDMS, SCB) — unblocked by Track B before they're eligible

Finnomena field parity is **not a goal** — used only as an end-of-run smoke test ("can `Stock(sym).<field>` resolve for the 33 filings-derivable Finnomena fields?").

## Locked decisions (this grilling)

| Q | Decision | Why |
|---|---|---|
| Goal definition | A: field-mapping coverage on parseable filings; Finnomena = smoke-test only | Parity as a goal would force a price-data sub-project; user wants filings-only scope first |
| Coverage denominator | 90% of parseable rows per symbol | Matches the empirically-proven manual loop |
| Scope | **S5** — parse 94 + grind 100 to 90%/<1pp/8-cyc + unblock #24 | Smaller scopes ship a dataset that silently drops 4 SET50 tickers (SCC/CPALL); S6 is multi-week, deferred |
| Sequencing | **O3** — two parallel tracks (A=parse+grind, B=#24 parser fix in worktree) | #24 has unknown blast radius; don't gate 96 symbols on it. Files disjoint: A touches `concepts.csv`, B touches `parsers/financial_statements.py` |
| Leader selection | **L4** — industry-first ordering (11 leaders), row-volume sanity-check after parsing | Compounding off cluster leaders is the dominant ROI lever (BBL→KBANK gave +24.55pp free) |
| Safety net | **G1 + G4 + G5 + G6 + G8** — regression test + volume cap + IFRS grounding + value-continuity + per-cycle revisions | G1 is load-bearing; everything else bounds blast radius. G2 (model confidence) too noisy; G3 (consensus) reserve for escalation |
| Topology | **T2** — supervisor + 4 worker grinders, queue-mediated | Single-writer discipline; workers can crash without poisoning. ~4× throughput over serial |
| Architecture | **A1** — all Claude Code (Agent team + this session's tool primitives) | Reuses the proven loop verbatim; A2 (raw API) requires reimplementing tool use |
| Kick-off | **K2** — document NOW, launch in fresh `claude -p` later | Fresh supervisor has minimal context; cron heartbeat re-entering THIS conversation would push past every cache window |

## Architecture

```
                       Fresh `claude -p` session = SUPERVISOR
                       (briefed by scripts/autonomy/supervisor_prompt.md)
                                     │
                       ┌─────────────┼─────────────┐
                       │             │             │
                  proposals/    runs/<ts>/    HF + git
                  pending/      state.json    (single writer)
                       ▲             │             │
                       │             ▼             │
                       │      CronCreate /30min    │
                       │                           │
       ┌───────────┬───┴──────┬───────────┬───────┴─────┐
       │           │          │           │             │
   Worker 1    Worker 2   Worker 3    Worker 4    Track B agent
   (PTTGC)    (KTB)      (CPF)       (LH)        (#24 parser fix)
   isolation: worktree                            isolation: worktree
   run_in_background:true                         run_in_background:true
   briefed by worker_prompt.md                    briefed inline
       │           │          │           │
       └───────────┴──────────┴───────────┘
            each writes proposals/pending/<sym>-c<n>-<uuid>.json
            each touches runs/<ts>/workers/<sym>.heartbeat
```

## The autonomous per-symbol loop (worker)

For each cycle (max 8 per symbol):

1. **Probe top-30 unmapped** for the symbol against current HF revision via DuckDB (`scripts/autonomy/probe_unmapped.py --symbol <S>`)
2. **Classify each candidate** using the worker Agent's own reasoning, with the inline rule:
   - **ALIAS** an existing concept → append to `aliases_th`
   - **NEW_CONCEPT** with a confident `ifrs-full:*` XBRL ref → propose new row (G5 enforcement)
   - **DUAL_STATEMENT** — existing concept in another statement type → propose a 2nd row with new `statement`
   - **SKIP** if no IFRS counterpart OR dynamic-text disclosure OR uncertain
3. **Apply volume cap (G4)**: ≤20 ALIAS + ≤3 NEW_CONCEPT additions per proposal. Over-cap → split into multiple proposals.
4. **Write proposal JSON** to `proposals/pending/<sym>-c<n>-<uuid>.json`:
   ```json
   {
     "symbol": "PTTGC",
     "cycle": 3,
     "worker_id": "agent-...",
     "ts": "2026-05-16T22:14:03Z",
     "additions": {
       "aliases": [{"concept": "revenue", "aliases_to_add": ["..."], "evidence_rows": [...]}],
       "concepts": [{"concept": "...", "statement": "BS", "label_en": "...", "label_th": "...", "xbrl_ref": "ifrs-full:..."}]
     },
     "stop_after_apply": false,
     "self_reported_coverage_pre": 0.7831
   }
   ```
5. **Touch heartbeat** (`runs/<ts>/workers/<sym>.heartbeat`)
6. **Wait for proposal to be archived** (poll `proposals/applied/` and `proposals/rejected/`)
7. **If applied**: read coverage delta from `proposals/applied/<file>.result.json`; decide stop:
   - coverage ≥ 90% → set `stop_after_apply=true`, exit cleanly
   - last 2 cycles Δ < 1pp each → exit cleanly
   - cycle == 8 → exit with `plateau` status
8. **If rejected**: read rejection reason; reduce batch size, drop the offending entries, retry as cycle N+1.

Worker exits after symbol terminates. Supervisor promotes symbol to `ground`.

## The autonomous supervisor loop

Single-writer, no LLM intelligence required for the apply path (deterministic file ops). LLM intelligence used for:
- Detecting parallel-session uncommitted state and refusing to clobber
- End-of-run PR body composition
- Dispatching next leader from the priority queue when a worker exits

Every poll (every 30s during active hours, every cron-tick of 30min as heartbeat):

```
poll_loop:
  for proposal in proposals/pending/ (FIFO):
    read JSON
    apply additions to data/concepts.csv (surgical line-precise edit; never csv.writer)
    run apply_concepts in memory (no commit yet)
    run G1 regression test (scripts/autonomy/regression_test.py)
      → re-tag all ground symbols using new dict
      → fail if any drops >2pp OR any concept's value distribution shifts >5%
    run G6 value-continuity test on touched concepts
      → fail if any new alias creates a within-symbol period-over-period jump >5×
    if G1 or G6 fails:
      git checkout -- data/concepts.csv
      mv proposals/pending/<file> proposals/rejected/<file>
      write proposals/rejected/<file>.reason.json with diagnostic
      continue
    git add data/concepts.csv && git commit -m "🤖 autonomy cycle <sym>-c<n>: +<A> aliases, +<C> concepts (coverage <pre>% → <post>%)"
    fnox exec -- python scripts/publish_revision.py --label v0.set100.<sym><n>
    mv proposals/pending/<file> proposals/applied/<file>
    write proposals/applied/<file>.result.json (coverage delta + revision tag)
    update runs/<ts>/state.json (per-symbol coverage history)

  check_worker_health:
    for each active worker in state.json:
      if heartbeat older than 2 min → SIGKILL + respawn (max 3 retries per symbol)
    if no workers + queue not empty:
      spawn next leader from priority queue (cap 4 concurrent)

  check_circuit_breakers:
    if cost > USD_CAP: PAUSE + notify; exit poll
    if wall_clock > TIME_CAP: graceful drain + notify; exit poll
    if PAUSE sentinel exists: stop dequeuing; workers finish in-flight; exit poll

  check_terminal_state:
    if all 100 symbols have terminal status (ground/plateau/parser-blocked):
      publish v0.set100.final
      gh pr edit #12 --body "$(cat runs/<ts>/final_report.md)"
      send notification (chief-of-staff channel)
      exit poll
```

## Safety gates (locked)

### G1 — Regression test on ground set
After each proposal apply, re-tag all `ground` symbols. Fail-loud if:
- Any symbol's coverage drops > **2pp** from its last-published value, OR
- Any concept's per-row value distribution (median + p99) shifts > **5%** between baseline and post-apply re-tag

Implementation: `scripts/autonomy/regression_test.py`. Runs in supervisor process (no extra agent call needed). Wall-time ~30s for 6 ground symbols, ~5min for full SET100 ground set.

### G4 — Volume cap per cycle
Per proposal: ≤ **20 ALIAS** additions, ≤ **3 NEW_CONCEPT** additions. Enforced by worker (split into multiple proposals if over). Hard-rejected by supervisor as a defense-in-depth check.

### G5 — IFRS XBRL grounding
Every `NEW_CONCEPT` row must have a non-empty `xbrl_ref` matching `^(ifrs-full|tfrs|set-tfrs):[A-Za-z][A-Za-z0-9]*$`. Supervisor rejects proposals that violate. Aliases of existing concepts inherit the parent's `xbrl_ref` — no extra check needed.

### G6 — Value-continuity check
For each newly-aliased concept on the worker's symbol: pull the time series, fail if any consecutive period (Q→Q or Y→Y) shows magnitude jump > **5×** that isn't already present in the prior dictionary. Catches the "wrong-magnitude alias" failure mode (share count merged with monetary value).

Per-concept tunable thresholds in `data/value_continuity_thresholds.csv` for known-volatile concepts (e.g., `goodwill_impairment` legitimately spikes; raise threshold to 20×).

### G8 — Append-only per-cycle revisions
Every applied proposal = one git commit + one HF revision (`v0.set100.<sym><n>`). Rollback = `git revert <sha>` + `huggingface-cli delete-tag`. Already in place from the manual loop.

## 11-leader priority queue (industry-first, L4)

Dispatched in this order. Workers cap at 4 concurrent — when one finishes, supervisor dequeues the next.

| # | Symbol | Industry cluster | Followers (expected compounding) |
|---|---|---|---|
| 1 | **PTTGC** | Petrochem / refinery | TOP, IRPC, BCP, PTTEP, BANPU, SPRC (~6) |
| 2 | **KTB** | Banks (tier-2) — compounding-test off BBL/KBANK | TTB, KKP, BAY, TISCO (~4); SCB after #24 |
| 3 | **CPF** | Food / agribusiness | OSP, ICHI, SAPPE, M, MINT, ZEN, TU (~7) |
| 4 | **LH** | Property / real-estate (non-REIT) | SPALI, AP, PSH, SC, SIRI, ANAN, QH, NOBLE, ORIGIN (~9) |
| 5 | **BH** | Healthcare / hospital | BCH, CHG, PR9, RAM (~4); BDMS after #24 |
| 6 | **DELTA** | Electronics / EMS | KCE, HANA, SVI (~3) |
| 7 | **GULF** | Utilities / IPP | EGCO, GPSC, RATCH, BPP, BGRIM, BCPG (~6) |
| 8 | **BLA** | Insurance / life | THRE, TIPH (~2) |
| 9 | **AOT** | Transport (already parsed, 32.62% start) | — |
| 10 | **CPN** | REIT / mall (already parsed, 11.46% start) | — |
| 11 | **ADVANC** | Telco (already parsed, 12.28% start, parser quirk — only 114 rows; will plateau early) | TRUE, INTUCH (~2) |

Sanity-check after parsing the 94: query unmapped-row volume per symbol, swap leader if any non-listed symbol shows >2× volume of its cluster leader.

After leaders complete, supervisor dispatches **followers** in descending row-count order; expected to terminate in 1–2 cycles each.

After all leaders + followers, supervisor dispatches the **tail** (remaining low-volume SET100 symbols) — expected to terminate in 1 cycle each via pure compounding.

## Track B — #24 parser fix (parallel worker)

Single Agent call with `isolation: "worktree"`, `run_in_background: true`. Briefed inline by the supervisor (no separate prompt file needed). Scope:

- Add sheet-name patterns for SCC (`1,2,3,4,5`), CPALL (`BS 3-5`, `PL3M-6-7`, `CF-11-14`), BDMS (`BS&PL Thai`, `PL-T (3)`, `CE Thai`), SCB (bank format different from BBL/KBANK — investigate)
- Verify via `python -m thaifin.parsers.financial_statements <zip>` on one zip per symbol
- Commit to a child branch of `feat/v2-dataset-pipeline`; open sub-PR

When Track B lands and is merged, supervisor:
- Re-parses only the 4 newly-unblocked symbols (cheap, zips cached)
- Adds them to the dispatch queue (industry positions: SCC=construction-materials new cluster, CPALL=retail-convenience new cluster, BDMS=healthcare-hospital follower of BH, SCB=banks follower of KTB)

## Lifecycle commands (mise tasks)

```bash
# Launch (one-shot)
mise run autonomy:start \
  --leaders "PTTGC,KTB,CPF,LH,BH,DELTA,GULF,BLA,AOT,CPN,ADVANC" \
  --queue-all-set100 \
  --usd-cap 200 \
  --time-cap 48h
# → starts a `claude -p` supervisor session with scripts/autonomy/supervisor_prompt.md
# → writes runs/<timestamp>/ skeleton
# → returns immediately; you can close the terminal

# Status (anytime, idempotent, read-only)
mise run autonomy:status
# → prints runs/<latest>/dashboard.md (regenerated by supervisor every 5 min)

# Pause (graceful drain — workers finish in-flight, supervisor stops dequeuing)
mise run autonomy:pause

# Resume from pause OR after a supervisor crash
mise run autonomy:resume

# Kill (only if pause doesn't drain)
mise run autonomy:kill
```

## Cost + time budget

| Quantity | Estimate | Cap |
|---|---|---|
| Wall-clock (full SET100, 4 workers) | ~20h | 48h (soft) |
| Anthropic spend | ~$300–500 | $200 tripwire → notify; user bumps cap to continue |
| Cycles total | ~500 (5 avg/symbol × 100) | hard per-symbol cap 8 |
| Git commits | ~500 | one per applied cycle |
| HF revisions | ~500 named `v0.set100.<sym>.<n>` + 1 final `v0.set100.final` | — |

## End-of-run artifact bundle

When all symbols reach terminal state (ground / plateau / parser-blocked), supervisor:

1. Publishes HF revision `v0.set100.final` (canonical "release" tag)
2. Composes `runs/<ts>/final_report.md` — per-symbol coverage table, regression incidents log, alias/concept additions list, cost summary
3. `gh pr edit #12 --body-file runs/<ts>/final_report.md` (appends to existing PR body, preserves earlier sections)
4. Sends notification through chief-of-staff channel
5. Commits `runs/<ts>/final_report.md` to the branch
6. Exits clean (no more cron tick re-entry needed)

## Resume here — launch sequence

```bash
# Prerequisites (one-time)
git fetch origin
git switch feat/v2-dataset-pipeline
git pull --ff-only
# Make sure latest spec doc commit is present:
git log --oneline -3 docs/specs/

# Verify autonomy scripts present
ls scripts/autonomy/
#   apply_proposal.py
#   probe_unmapped.py
#   regression_test.py
#   supervisor_prompt.md
#   worker_prompt.md

# Verify mise tasks
mise tasks | grep autonomy

# Verify SET100 zips cached
ls data/sec_idisc/zips/ | wc -l   # ≥100

# Verify HF token reachable via fnox
fnox exec -- python -c "import os; assert os.environ['HF_TOKEN']; print('ok')"

# Launch
mise run autonomy:start

# Walk away. Notification arrives in ~20–30h.
```

## Out-of-scope follow-ups (deferred)

- **Per-industry coverage gate** ([#19](https://github.com/ninyawee/thaifin/issues/19)) — useful but blocking S5 on it adds 2-3 hours of work. Defer; the per-symbol gate is sufficient for v2.
- **Price-data source integration** — required for full Finnomena field parity (close, mkt_cap, P/E, P/BV, dividend_yield, EV/EBITDA). Separate workstream; not in this autonomy plan.
- **SET+mai universe extension** (S6) — 8–12 week scope; rerun this same autonomy loop with `--queue-all-setmai`.
- **LLM model selection per gate** — currently uses worker Agent's own intelligence. Future: cheap Haiku for SKIP classification, Sonnet for ALIAS, Opus for NEW_CONCEPT.

## Cross-links

- Manual-loop predecessor: [`docs/specs/v2-iteration-loop.md`](./v2-iteration-loop.md)
- PRD: [#11](https://github.com/ninyawee/thaifin/issues/11)
- Open PR: [#12](https://github.com/ninyawee/thaifin/pull/12)
- Parser unblock dependency: [#24](https://github.com/ninyawee/thaifin/issues/24)
- Per-industry gate (deferred): [#19](https://github.com/ninyawee/thaifin/issues/19)
- SEC IDISC download module (parallel): [#21](https://github.com/ninyawee/thaifin/issues/21)
