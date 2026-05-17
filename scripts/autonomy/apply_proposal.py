#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["duckdb"]
# ///
"""Atomic apply of a worker proposal to data/concepts.csv with gates G1+G4+G5+G6.

Steps:
    1. Parse + schema-validate the proposal JSON (G4 volume-cap enforced here)
    2. Compute coverage_pre against current revision
    3. Validate every NEW_CONCEPT row has a valid xbrl_ref (G5)
    4. Apply edits to data/concepts.csv surgically (no csv.writer; line-precise)
    5. Run G1 regression test on ground symbols
    6. Run G6 value-continuity check on touched concepts for the proposing symbol
    7. Compute coverage_post for the proposing symbol
    8. On any gate failure: git checkout -- data/concepts.csv; return reason JSON
    9. On success: return {coverage_pre, coverage_post, delta_pp, dirty_files}

Does NOT commit or push to HF. The supervisor caller does that on success.

Exit:
    0 — applied successfully; result JSON on stdout
    1 — gate failure (any of G1/G4/G5/G6); reason JSON on stdout
    2 — schema/IO error; reason JSON on stdout

Usage:
    uv run scripts/autonomy/apply_proposal.py \\
        --proposal proposals/pending/PTTGC-c1-abc.json \\
        --baseline runs/<ts>/baseline.json \\
        --revision v0.set100.0 \\
        --ground PTT,BBL,KBANK
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from thaifin.concepts import apply_concepts, build_lookup, load_concepts  # noqa: E402

DEFAULT_HF_PARQUET = (
    "https://huggingface.co/datasets/ninyawee/thaifin-financials"
    "/resolve/{revision}/financial_lines.parquet"
)
XBRL_REF_RE = re.compile(r"^(ifrs-full|tfrs|set-tfrs):[A-Za-z][A-Za-z0-9]*$")

VOLUME_CAP_ALIAS = 20
VOLUME_CAP_NEW = 3
VOLUME_CAP_DUAL = 5

VALUE_CONTINUITY_DEFAULT_FACTOR = 5.0


def _fail(stage: str, **details) -> int:
    json.dump({"applied": False, "gate_failed": stage, **details}, sys.stdout,
              ensure_ascii=False, indent=2)
    print()
    return 1


def _ok(**payload) -> int:
    json.dump({"applied": True, **payload}, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def _validate_schema(p: dict) -> tuple[bool, str]:
    for k in ("symbol", "cycle", "additions"):
        if k not in p:
            return False, f"missing key: {k}"
    add = p["additions"]
    aliases = add.get("aliases", [])
    concepts = add.get("concepts", [])
    duals = add.get("dual_statement", [])
    if len(aliases) > VOLUME_CAP_ALIAS:
        return False, f"alias count {len(aliases)} > cap {VOLUME_CAP_ALIAS}"
    if len(concepts) > VOLUME_CAP_NEW:
        return False, f"new-concept count {len(concepts)} > cap {VOLUME_CAP_NEW}"
    if len(duals) > VOLUME_CAP_DUAL:
        return False, f"dual-statement count {len(duals)} > cap {VOLUME_CAP_DUAL}"
    return True, ""


def _validate_xbrl(concepts: list[dict]) -> list[dict]:
    """Return list of concepts that fail G5 grounding."""
    failed = []
    for c in concepts:
        ref = c.get("xbrl_ref", "")
        if not ref or not XBRL_REF_RE.match(ref):
            failed.append({"concept": c.get("concept"), "xbrl_ref": ref})
    return failed


def _apply_to_csv(csv_path: Path, additions: dict) -> None:
    """Surgical line-precise edit. Aliases append to existing rows; new concepts append at end.

    Never use csv.writer — it re-quotes every row and ruins the diff.
    """
    lines = csv_path.read_text().splitlines(keepends=False)

    # Index header
    header_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") or not line.strip():
            continue
        header_idx = i
        break
    if header_idx is None:
        raise RuntimeError("concepts.csv: no header found")
    header = [h.strip() for h in lines[header_idx].split(",")]
    col = {h: i for i, h in enumerate(header)}

    # Aliases: append "|<new>" to aliases_th column for matching (concept, statement)
    alias_targets = {(a["concept"], a["statement"]): a["aliases_to_add"] for a in additions.get("aliases", [])}
    for i in range(header_idx + 1, len(lines)):
        ln = lines[i]
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        cells = ln.split(",")
        if len(cells) < len(header):
            continue
        key = (cells[col["concept"]].strip(), cells[col["statement"]].strip())
        if key in alias_targets:
            existing = cells[col["aliases_th"]].strip()
            new = "|".join(alias_targets[key])
            cells[col["aliases_th"]] = (existing + "|" + new) if existing else new
            lines[i] = ",".join(cells)
            del alias_targets[key]
    if alias_targets:
        # Aliases for non-existent (concept,statement) — treat as dual_statement-style addition.
        for (concept, statement), to_add in alias_targets.items():
            lines.append(f"{concept},{statement},,,{'|'.join(to_add)},,,")

    # Dual-statement: add a new row mirroring existing concept, with new statement and empty label
    for d in additions.get("dual_statement", []):
        concept = d["concept"]
        statement = d["new_statement"]
        lines.append(f"{concept},{statement},,,,,,")

    # New concepts: append at end
    for c in additions.get("concepts", []):
        row = [
            c.get("concept", ""),
            c.get("statement", ""),
            c.get("label_en", "").replace(",", " "),  # G_schema: no unescaped commas
            c.get("label_th", "").replace(",", " "),
            "|".join(c.get("aliases_th", [])),
            c.get("xbrl_ref", ""),
            ";".join(c.get("applicable_industries", [])),
            c.get("sign_convention", ""),
        ]
        lines.append(",".join(row))

    csv_path.write_text("\n".join(lines) + "\n")


def _value_continuity_check(symbol: str, revision: str, touched_concepts: list[str],
                            factor: float) -> list[dict]:
    """G6 — within-symbol period-over-period magnitude shouldn't jump > factor×.
    Returns list of violations (empty if all ok).
    """
    if not touched_concepts:
        return []
    url = DEFAULT_HF_PARQUET.format(revision=revision)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    # Re-tag in-memory with new dictionary, but for this we need to re-derive concept
    # for each row using the just-updated CSV.
    from thaifin.concepts import build_lookup, load_concepts
    lookup = build_lookup(load_concepts(Path("data/concepts.csv")))

    rows = con.execute(
        f"""
        SELECT period, statement, raw_label_th, value
        FROM read_parquet('{url}')
        WHERE symbol = ?
        ORDER BY period
        """,
        [symbol],
    ).fetchall()
    typed = [
        {"period": p, "statement": s, "raw_label_th": l, "value": v, "concept": None}
        for p, s, l, v in rows
    ]
    tagged = apply_concepts(typed, lookup)
    by_concept_period: dict[str, dict[str, float]] = {}
    for r in tagged:
        c = r["concept"]
        if c not in touched_concepts:
            continue
        try:
            v = abs(float(r["value"]))
        except (TypeError, ValueError):
            continue
        by_concept_period.setdefault(c, {})[r["period"]] = v

    violations = []
    for concept, series in by_concept_period.items():
        periods = sorted(series.keys())
        for i in range(1, len(periods)):
            prev, cur = series[periods[i - 1]], series[periods[i]]
            if prev == 0 or cur == 0:
                continue
            ratio = max(prev, cur) / max(min(prev, cur), 1e-9)
            if ratio > factor:
                violations.append({
                    "concept": concept,
                    "period_a": periods[i - 1], "period_b": periods[i],
                    "value_a": prev, "value_b": cur, "ratio": ratio,
                })
    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--revision", default="main")
    ap.add_argument("--ground", default="", help="Comma-separated symbols for G1")
    ap.add_argument("--concepts-csv", default="data/concepts.csv", type=Path)
    ap.add_argument("--value-continuity-factor", type=float,
                    default=VALUE_CONTINUITY_DEFAULT_FACTOR)
    args = ap.parse_args()

    try:
        proposal = json.loads(args.proposal.read_text())
    except Exception as e:
        return _fail("G_schema_invalid", error=f"could not parse: {e}")

    ok, reason = _validate_schema(proposal)
    if not ok:
        if "cap" in reason:
            return _fail("G4_volume_cap", error=reason)
        return _fail("G_schema_invalid", error=reason)

    additions = proposal["additions"]
    symbol = proposal["symbol"]

    # G5 — XBRL grounding (only NEW_CONCEPTs; aliases inherit)
    xbrl_fail = _validate_xbrl(additions.get("concepts", []))
    if xbrl_fail:
        return _fail("G5_no_xbrl", failed=xbrl_fail)

    # Snapshot for rollback (just remember the content)
    csv_before = args.concepts_csv.read_text()
    try:
        _apply_to_csv(args.concepts_csv, additions)
    except Exception as e:
        args.concepts_csv.write_text(csv_before)
        return _fail("G_apply_error", error=str(e))

    # G1 — regression test on ground symbols (uses the new CSV)
    if args.ground:
        g1 = subprocess.run(
            ["uv", "run", "scripts/autonomy/regression_test.py",
             "--ground", args.ground,
             "--baseline", str(args.baseline),
             "--revision", args.revision,
             "--concepts-csv", str(args.concepts_csv)],
            capture_output=True, text=True,
        )
        if g1.returncode != 0:
            args.concepts_csv.write_text(csv_before)
            try:
                payload = json.loads(g1.stdout)
            except Exception:
                payload = {"raw": g1.stdout, "stderr": g1.stderr}
            return _fail("G1_regression", **payload)

    # G6 — value continuity on touched concepts for the symbol
    touched = (
        [a["concept"] for a in additions.get("aliases", [])]
        + [c["concept"] for c in additions.get("concepts", [])]
        + [d["concept"] for d in additions.get("dual_statement", [])]
    )
    g6_violations = _value_continuity_check(
        symbol, args.revision, touched, args.value_continuity_factor
    )
    if g6_violations:
        args.concepts_csv.write_text(csv_before)
        return _fail("G6_value_continuity", violations=g6_violations)

    # Compute coverage_post for the symbol
    entries = load_concepts(args.concepts_csv)
    lookup = build_lookup(entries)
    url = DEFAULT_HF_PARQUET.format(revision=args.revision)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    rows = [
        {"statement": s, "raw_label_th": l, "concept": None}
        for s, l in con.execute(
            f"SELECT statement, raw_label_th FROM read_parquet('{url}') WHERE symbol = ?",
            [symbol],
        ).fetchall()
    ]
    tagged = apply_concepts(rows, lookup)
    mapped = sum(1 for r in tagged if r.get("concept"))
    total = len(tagged)
    coverage_post = mapped / total if total else 0.0
    coverage_pre = proposal.get("coverage_pre", 0.0)

    return _ok(
        symbol=symbol,
        cycle=proposal.get("cycle"),
        coverage_pre=coverage_pre,
        coverage_post=coverage_post,
        delta_pp=(coverage_post - coverage_pre) * 100,
        alias_count=len(additions.get("aliases", [])),
        new_concept_count=len(additions.get("concepts", [])),
        dual_count=len(additions.get("dual_statement", [])),
        dirty_files=["data/concepts.csv"],
    )


if __name__ == "__main__":
    sys.exit(main())
