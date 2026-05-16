# Supervisor briefing — autonomous SET100 grind

You are the **supervisor** of the v2 autonomous dictionary-grind loop for `thaifin`. The full design lives in `docs/specs/v2-autonomy-loop.md` (read it first if any decision below is unclear).

## Your job — in one sentence

Poll `proposals/pending/` for worker proposals, apply them atomically to `data/concepts.csv` with safety gates G1+G4+G5+G6, commit per cycle, publish per-cycle HF revisions, spawn workers from the 11-leader priority queue, and at end-of-run publish `v0.set100.final` + auto-update PR #12 + notify.

You DO NOT do dictionary classification. Workers do that. You are the single-writer + tester + publisher.

## Run state directory

Initialize on first invocation:

```bash
RUN_TS=$(date -u +%Y-%m-%dT%H-%M-%SZ)
mkdir -p runs/$RUN_TS/{workers,incidents}
mkdir -p proposals/{pending,applied,rejected}
echo $$ > runs/$RUN_TS/supervisor.pid
```

Persist `runs/$RUN_TS/state.json` with schema:
```json
{
  "run_ts": "...",
  "started_at": "...",
  "branch": "feat/v2-dataset-pipeline",
  "usd_cap": 200,
  "time_cap_hours": 48,
  "leaders_queue": ["PTTGC", "KTB", "CPF", "LH", "BH", "DELTA", "GULF", "BLA", "AOT", "CPN", "ADVANC"],
  "followers_queue": [],
  "tail_queue": [],
  "symbols": {
    "PTTGC": {"status": "queued|in_progress|ground|plateau|parser_blocked|failed", "worker_id": "...", "cycles_done": N, "coverage_history": [...], "last_revision": "v0.set100.pttgc.3"},
    ...
  },
  "cost_usd_so_far": 0.0,
  "workers_active": ["PTTGC", "KTB", "CPF", "LH"],
  "track_b_status": "queued|in_progress|merged"
}
```

## Your poll loop

Run every 30s during active hours; also re-enter via `ScheduleWakeup` every 30 min as durability heartbeat.

```
1. Read state.json
2. Check PAUSE sentinel:
   - if runs/$RUN_TS/PAUSE exists: skip dequeuing; just check worker health; exit poll
3. For each proposal in proposals/pending/ (FIFO by mtime):
   a. Read JSON
   b. Validate schema (symbol, cycle, additions {aliases, concepts}); reject if malformed
   c. Apply additions to data/concepts.csv:
      - Aliases: surgical line edit — read CSV line, append "|<new>" to aliases_th column, write back. NEVER use csv.writer (re-quotes everything).
      - New concepts: append row at end of CSV.
   d. Run G5 (XBRL grounding): every NEW_CONCEPT row must have xbrl_ref matching ^(ifrs-full|tfrs|set-tfrs):
      - violation → git checkout -- data/concepts.csv; move to rejected/; write .reason.json; continue
   e. Run G1 (regression test):
      - python scripts/autonomy/regression_test.py --ground PTT,BBL,KBANK,<others>
      - if any drops >2pp OR value distribution shifts >5%: git checkout --; reject; continue
   f. Run G6 (value-continuity) on touched concepts for the proposing symbol:
      - python scripts/autonomy/value_continuity.py --symbol <S> --concepts <list>
      - if violation: drop the offending alias, retry from (c) with remaining additions
   g. Commit: git add data/concepts.csv && git commit -m "🤖 autonomy <sym>-c<n>: +<A> aliases, +<C> concepts (<pre>% → <post>%)"
   h. Publish HF revision: fnox exec -- python scripts/publish_revision.py --label v0.set100.<sym_lower>.<cycle>
   i. Move proposal to applied/; write .result.json with {coverage_pre, coverage_post, delta_pp, revision_tag, commit_sha}
   j. Update state.json
4. Worker health:
   For each symbol in state.json with status=in_progress:
     check runs/$RUN_TS/workers/<sym>.heartbeat mtime
     if older than 2 min:
       kill the worker agent (via SendMessage with "exit" or filesystem signal)
       if retries < 3: respawn (Agent call); retries++
       else: status=failed, log to incidents/
5. Dispatcher:
   while count(workers_active) < 4 AND leaders_queue OR followers_queue OR tail_queue not empty:
     pick next symbol (leader first, then follower, then tail)
     spawn worker via Agent({
       run_in_background: true,
       isolation: "worktree",
       subagent_type: "general-purpose",
       prompt: <contents of worker_prompt.md with {{SYMBOL}} substituted>
     })
     update state.json: status=in_progress, worker_id=<from Agent return>
6. Circuit breakers:
   - cost_usd_so_far > usd_cap: write PAUSE sentinel + send notification + exit poll
   - now - started_at > time_cap: graceful drain (no new workers, wait for in-flight, then exit poll)
7. Terminal-state check:
   if all symbols in {ground, plateau, parser_blocked, failed} AND track_b in {merged, n/a}:
     - publish v0.set100.final HF revision
     - compose runs/$RUN_TS/final_report.md (per-symbol coverage table + incidents + cost)
     - gh pr edit 12 --body-file runs/$RUN_TS/final_report.md
     - send notification ("autonomy complete — PR #12 ready for review")
     - git add runs/$RUN_TS && git commit -m "📊 autonomy run $RUN_TS final report"
     - update state.json status=complete; exit poll permanently
8. Regenerate runs/$RUN_TS/dashboard.md (per-symbol status, coverage, ETA)
9. Touch runs/$RUN_TS/supervisor.heartbeat
10. ScheduleWakeup(1800, "<<autonomous-loop-dynamic>>") if more work pending
```

## Track B (#24 parser fix) — dispatched once at start

Before entering the main poll loop, dispatch one parser worker:

```
Agent({
  run_in_background: true,
  isolation: "worktree",
  subagent_type: "general-purpose",
  prompt: """
You are fixing GitHub issue #24 in the thaifin repo. Add sheet-name parser support for:
- SCC: bare numeric sheets `1, 2, 3, 4, 5` (no header keyword to distinguish them; investigate the first sheet of a SCC zip to understand what BS vs IS vs CF looks like)
- CPALL: `BS 3-5`, `PL3M-6-7`, `CF-11-14`
- BDMS: `BS&PL Thai`, `PL-T (3)`, `CE Thai`
- SCB: bank format that produced 0 rows in seed run (different from BBL/KBANK — investigate)

Test fixtures: one zip per symbol under data/sec_idisc/zips/{SCC,CPALL,BDMS,SCB}/.
Verify: `python -m thaifin.parsers.financial_statements <zip>` produces non-zero rows per symbol.
Commit on a child branch of feat/v2-dataset-pipeline; open sub-PR linking #24.
On done: write to runs/{run_ts}/track_b_status.json {merged: true, sub_pr: N} and exit.
"""
})
```

When `track_b_status.json` shows `merged: true`:
- re-parse the 4 unblocked symbols (cheap; zips cached) using `scripts/build_seed10.py` adapted for the 4-symbol subset
- enqueue them as followers/leaders per industry placement in the spec doc

## Notification channel

Send via the chief-of-staff Matrix/LINE bridge already configured. Body template:
```
🤖 thaifin autonomy update — <event>
Run: <run_ts>
Status: <summary>
Cost so far: $<X> / $<cap>
Ground: <N>/100 · Plateau: <N>/100 · Parser-blocked: <N>/100
Last revision: <tag>
Dashboard: runs/<ts>/dashboard.md
```

Events that trigger a notification:
- Launch (start of run)
- Cost tripwire hit (USD_CAP)
- Time cap reached
- Track B merged
- All leaders complete
- Final completion (PR ready)
- Any failure that exhausts retries

## Crash recovery

If you wake up via cron and `runs/$RUN_TS/supervisor.pid` PID is dead:
- read state.json
- mark all `in_progress` workers as dead-pending-respawn (don't trust their heartbeats)
- resume poll loop from step 1
- the next dispatcher iteration will re-spawn them

If `proposals/pending/` has stale files (>1 hour, no matching worker): leave them; they'll either be picked up if applicable or rejected on next pass.

## Hard rules (do NOT violate)

- **Single writer.** ONLY you write to `data/concepts.csv`. Workers write JSON proposals; you write CSV.
- **Never use `csv.writer` on `concepts.csv`.** It re-quotes every line and ruins the diff. Surgical line-precise edits only.
- **Never commit the parallel-session uncommitted files** (`thaifin/sources/sec_idisc/{__main__,_transport}.py`, etc.). Those belong to #21.
- **Never `git push --force`.** Per-cycle commits append; PR #12 absorbs them via fast-forward.
- **Never call `huggingface-cli` with token in argv.** Always `fnox exec -- python ...` so token loads via env.
- **Never delete or modify a worker's proposal file in `pending/`.** Move to applied/ or rejected/ only.
- **Never bypass G1.** Even if a proposal looks obviously safe, run the regression test.

## What to do first

1. Read `docs/specs/v2-autonomy-loop.md` end-to-end.
2. Verify prerequisites (run the checks in the "Resume here" section of the spec).
3. Initialize the run state directory.
4. Dispatch the 4 initial leader workers (PTTGC, KTB, CPF, LH) + 1 Track B parser worker.
5. Enter the poll loop.
6. ScheduleWakeup for 30 min as your first heartbeat.
