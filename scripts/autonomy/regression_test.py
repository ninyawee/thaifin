#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["duckdb"]
# ///
"""G1 — regression test on the ground-symbol set.

Re-tag each ground symbol's filing rows using the CURRENT data/concepts.csv,
compare against the per-symbol coverage baseline in baseline.json. Fail if any
symbol drops > --max-drop-pp from its baseline OR if any concept's per-row
value distribution shifts > --max-value-shift-pct (median or p99).

Exit:
    0 — all symbols within tolerance
    1 — at least one regression

Output: JSON to stdout with per-symbol deltas and (on fail) the violations.

Usage:
    uv run scripts/autonomy/regression_test.py \\
        --ground PTT,BBL,KBANK \\
        --baseline runs/<ts>/baseline.json \\
        --revision v0.set100.0 \\
        --max-drop-pp 2.0 \\
        --max-value-shift-pct 5.0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

# importable from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from thaifin.concepts import apply_concepts, build_lookup, coverage, load_concepts  # noqa: E402

DEFAULT_HF_PARQUET = (
    "https://huggingface.co/datasets/ninyawee/thaifin-financials"
    "/resolve/{revision}/financial_lines.parquet"
)


def _per_symbol_coverage(rows: list[dict], lookup) -> float:
    tagged = apply_concepts(rows, lookup)
    _, _, ratio = coverage(tagged)
    return ratio


def _value_distribution(rows: list[dict]) -> dict[str, dict[str, float]]:
    """For each concept, return {median, p99} of values."""
    from statistics import median, quantiles

    by_concept: dict[str, list[float]] = {}
    for r in rows:
        c = r.get("concept")
        v = r.get("value")
        if c is None or v is None:
            continue
        try:
            by_concept.setdefault(c, []).append(abs(float(v)))
        except (TypeError, ValueError):
            continue
    out = {}
    for c, vals in by_concept.items():
        if len(vals) < 3:
            continue
        out[c] = {
            "median": median(vals),
            "p99": quantiles(vals, n=100)[98] if len(vals) >= 100 else max(vals),
        }
    return out


def _shift_pct(a: float, b: float) -> float:
    if a == 0 and b == 0:
        return 0.0
    base = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / base * 100.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ground", required=True, help="Comma-separated symbol list")
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--revision", default="main")
    ap.add_argument(
        "--concepts-csv", default="data/concepts.csv", type=Path
    )
    ap.add_argument("--max-drop-pp", type=float, default=2.0)
    ap.add_argument("--max-value-shift-pct", type=float, default=5.0)
    args = ap.parse_args()

    symbols = [s.strip() for s in args.ground.split(",") if s.strip()]
    entries = load_concepts(args.concepts_csv)
    lookup = build_lookup(entries)

    baseline = json.loads(args.baseline.read_text())  # {symbol: {coverage, value_dist}}

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    url = DEFAULT_HF_PARQUET.format(revision=args.revision)

    violations = []
    per_symbol = {}
    for sym in symbols:
        rows = [
            {"statement": s, "raw_label_th": l, "value": v, "concept": None}
            for s, l, v in con.execute(
                f"SELECT statement, raw_label_th, value FROM read_parquet('{url}') WHERE symbol = ?",
                [sym],
            ).fetchall()
        ]
        new_cov = _per_symbol_coverage(rows, lookup)
        base_cov = baseline.get(sym, {}).get("coverage")
        drop_pp = (base_cov - new_cov) * 100 if base_cov is not None else 0.0

        tagged = apply_concepts(rows, lookup)
        new_dist = _value_distribution(tagged)
        base_dist = baseline.get(sym, {}).get("value_dist", {})
        dist_violations = []
        for concept, new_stats in new_dist.items():
            base_stats = base_dist.get(concept)
            if not base_stats:
                continue
            for stat in ("median", "p99"):
                shift = _shift_pct(base_stats[stat], new_stats[stat])
                if shift > args.max_value_shift_pct:
                    dist_violations.append(
                        {"concept": concept, "stat": stat, "baseline": base_stats[stat],
                         "new": new_stats[stat], "shift_pct": shift}
                    )

        per_symbol[sym] = {
            "baseline_coverage": base_cov,
            "new_coverage": new_cov,
            "drop_pp": drop_pp,
            "dist_violations": dist_violations,
        }

        if base_cov is not None and drop_pp > args.max_drop_pp:
            violations.append({"symbol": sym, "kind": "coverage_drop", "drop_pp": drop_pp,
                               "baseline": base_cov, "new": new_cov})
        if dist_violations:
            violations.append({"symbol": sym, "kind": "value_shift",
                               "concepts": [v["concept"] for v in dist_violations]})

    result = {
        "passed": not violations,
        "revision": args.revision,
        "per_symbol": per_symbol,
        "violations": violations,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
