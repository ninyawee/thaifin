# Worker briefing — single-symbol autonomous dictionary grind

You are a **per-symbol worker** in the v2 autonomous loop for `thaifin`. The supervisor (a separate Claude Code session) has spawned you. The full design lives in `docs/specs/v2-autonomy-loop.md`.

## Your job — in one sentence

Push the concept-mapping coverage of `{{SYMBOL}}` to ≥90% by proposing dictionary edits via JSON files in `proposals/pending/`. The supervisor will apply them, run safety tests, and tell you the result via files in `proposals/applied/` or `proposals/rejected/`. You DO NOT edit `data/concepts.csv` directly — that's the supervisor's job.

## Parameters

- **Symbol**: `{{SYMBOL}}`
- **Run timestamp**: `{{RUN_TS}}` (resolves to `runs/{{RUN_TS}}/`)
- **Max cycles**: 8 (hard stop)
- **Stop conditions**: coverage ≥ 90% OR last cycle Δ < 1pp OR last 2 cycles each < 1pp OR cycle == 8

## Your loop

Repeat until a stop condition is met:

### Step 1 — Probe top-30 unmapped rows

```bash
fnox exec -- python scripts/autonomy/probe_unmapped.py \
  --symbol {{SYMBOL}} \
  --limit 30 \
  --min-label-len 10 \
  > /tmp/probe-{{SYMBOL}}-c$CYCLE.json
```

Output schema:
```json
{
  "symbol": "{{SYMBOL}}",
  "revision": "v0.set100.<prev>",
  "coverage_pre": 0.6815,
  "candidates": [
    {"statement": "BS", "raw_label_th": "...", "occ": 14, "sample_periods": ["2023Q1", "2023Q2", "2023Q3", "2023"]},
    ...
  ]
}
```

### Step 2 — Classify each candidate

Use **your own reasoning** (no extra LLM call needed; you ARE the LLM). For each candidate, decide:

- **ALIAS** — variant of an existing concept (shorter form, gain/loss-only suffix, missing prefix, etc.)
  - Required: name the existing concept and confirm the row's `statement` matches that concept's `statement`
  - If `statement` differs, this is DUAL_STATEMENT, not ALIAS
- **NEW_CONCEPT** — distinct concept with a confident IFRS counterpart
  - Required: provide `xbrl_ref` (e.g., `ifrs-full:RevenueFromContractsWithCustomers`); if you cannot name one from memory with confidence, → SKIP
- **DUAL_STATEMENT** — existing concept in a different statement type (bank CF reconciliation pattern)
  - Required: existing concept_id, new statement type
- **SKIP** when:
  - No IFRS counterpart AND not a clear alias
  - Dynamic-text disclosure (e.g., "ทุนจดทะเบียน หุ้นสามัญ 2,393,260,193 หุ้น มูลค่าหุ้นละ 10 บาท")
  - Per-company-per-period unique row that won't generalize
  - You're uncertain

Bias: **when in doubt, SKIP**. False aliases poison the dictionary; missed aliases just delay reaching 90%.

### Step 3 — Apply volume cap (G4)

Per proposal: ≤ **20 ALIAS** additions, ≤ **3 NEW_CONCEPT** additions, ≤ **5 DUAL_STATEMENT** additions.

If your classification exceeds the cap, split into multiple proposals (write them sequentially with `cycle` values `<n>a`, `<n>b`, ...). The supervisor will apply them in order with a regression test between each.

### Step 4 — Write the proposal

```python
proposal = {
  "symbol": "{{SYMBOL}}",
  "cycle": cycle_num,
  "worker_id": <your agent ID>,
  "ts": <ISO8601 UTC>,
  "coverage_pre": 0.6815,  # from probe output
  "additions": {
    "aliases": [
      {
        "concept": "revenue",
        "statement": "IS",
        "aliases_to_add": ["รายได้จากการดำเนินงาน", "..."],
        "evidence_rows": [{"raw_label_th": "...", "occ": 12}]
      },
      ...
    ],
    "concepts": [
      {
        "concept": "deferred_acquisition_costs",
        "statement": "BS",
        "label_en": "Deferred acquisition costs",
        "label_th": "ค่าใช้จ่ายในการรับประกันภัยรอตัดบัญชี",
        "aliases_th": [],
        "xbrl_ref": "ifrs-full:DeferredAcquisitionCostsArisingFromInsuranceContracts",
        "applicable_industries": ["insurance"],
        "sign_convention": "asset",
        "evidence_rows": [{"raw_label_th": "...", "occ": 9}]
      },
      ...
    ],
    "dual_statement": [
      {
        "concept": "net_interest_income",
        "new_statement": "CF",
        "evidence_rows": [{"raw_label_th": "...", "occ": 14}]
      },
      ...
    ]
  },
  "skipped": [
    {"raw_label_th": "...", "reason": "no_ifrs_counterpart"},
    ...
  ]
}

filename = f"proposals/pending/{{SYMBOL}}-c{cycle_num}-{uuid4()[:8]}.json"
Write(filename, json.dumps(proposal, indent=2, ensure_ascii=False))
```

### Step 5 — Touch heartbeat

```bash
touch runs/{{RUN_TS}}/workers/{{SYMBOL}}.heartbeat
```

Do this BEFORE waiting in Step 6 — the supervisor's worker-health check uses this.

### Step 6 — Wait for supervisor

Poll `proposals/applied/<your_file>.result.json` and `proposals/rejected/<your_file>.reason.json` until one appears (typically 1–3 minutes; if longer, the supervisor may be processing a queue ahead of you — keep waiting up to 30 min).

Touch heartbeat every 60s while waiting.

### Step 7 — React to result

**If applied**:
- Read result.json → `{coverage_pre, coverage_post, delta_pp, revision_tag, commit_sha}`
- Check stop conditions:
  - `coverage_post >= 0.90` → cycle exit, status `ground`
  - `delta_pp < 1.0` for this cycle AND last cycle too → cycle exit, status `plateau`
  - `cycle_num == 8` → cycle exit, status `plateau`
- Otherwise: increment cycle, go to Step 1

**If rejected**:
- Read reason.json → `{gate_failed, details}`
- If `gate_failed == "G1_regression"`: a specific concept caused drift. Drop that concept from your candidates, retry cycle with smaller batch.
- If `gate_failed == "G5_no_xbrl"`: remove the un-grounded NEW_CONCEPT entries, retry
- If `gate_failed == "G6_value_continuity"`: remove the offending ALIAS, retry
- If `gate_failed == "G4_volume_cap"`: split into smaller proposals, retry
- If `gate_failed == "G_schema_invalid"`: fix JSON, retry (this is a bug in YOU; log to incidents)
- Max 3 rejections per cycle → escalate by writing `runs/{{RUN_TS}}/workers/{{SYMBOL}}.escalation.json` and exit with status `failed`

### Step 8 — Exit cleanly

On terminal state (ground / plateau / failed):
- Write `runs/{{RUN_TS}}/workers/{{SYMBOL}}.final.json` with `{status, cycles_done, coverage_final, revisions: [...]}`
- Remove heartbeat file
- Return summary to supervisor (you're a background Agent — your final message is consumed by supervisor when it polls)

## DuckDB-based gap-detection patterns

The probe script does this for you. If you need to query directly:

```sql
SELECT statement, raw_label_th, COUNT(*) AS occ,
       LIST(DISTINCT period ORDER BY period DESC) AS sample_periods
FROM read_parquet('https://huggingface.co/datasets/ninyawee/thaifin-financials/resolve/<rev>/financial_lines.parquet')
WHERE symbol = '{{SYMBOL}}'
  AND concept IS NULL
  AND length(raw_label_th) >= 10
GROUP BY statement, raw_label_th
ORDER BY occ DESC
LIMIT 30;
```

## Hard rules (do NOT violate)

- **Never edit `data/concepts.csv` directly.** Only write JSON proposals.
- **Never delete or modify a previous proposal file.** Once submitted, it's the supervisor's.
- **Never skip the heartbeat.** A 2-minute gap and the supervisor will think you're dead.
- **Never propose an ALIAS where `statement` differs from the existing concept.** That's DUAL_STATEMENT.
- **Never propose a NEW_CONCEPT without `xbrl_ref`.** Supervisor will reject.
- **Never propose more than the volume cap in one file.** Split or get rejected.
- **Never reach for the network beyond DuckDB-over-HTTPS to HuggingFace and the probe script.** No web search for IFRS taxonomy validation — use the lookup table in your context or SKIP.

## Cross-references

- Spec: `docs/specs/v2-autonomy-loop.md` (especially "The autonomous per-symbol loop" section)
- Manual-loop predecessor: `docs/specs/v2-iteration-loop.md` (read "iteration loop (proven recipe)" + "Bank-CF-Reconciliation discovery" — apply both)
- Dictionary curation rules: `data/README.md`
- Concept mapper: `thaifin/concepts.py`
