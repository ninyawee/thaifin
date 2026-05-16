#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["duckdb"]
# ///
"""Probe top-N unmapped raw labels for a symbol on the latest HF revision.

Output: JSON to stdout matching scripts/autonomy/worker_prompt.md "Step 1" schema.

Usage:
    uv run scripts/autonomy/probe_unmapped.py --symbol PTTGC --revision v0.set100.0 --limit 30
"""
from __future__ import annotations

import argparse
import json
import sys

import duckdb

DEFAULT_HF_PARQUET = (
    "https://huggingface.co/datasets/ninyawee/thaifin-financials"
    "/resolve/{revision}/financial_lines.parquet"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--revision", default="main")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--min-label-len", type=int, default=10)
    args = ap.parse_args()

    url = DEFAULT_HF_PARQUET.format(revision=args.revision)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    cov_row = con.execute(
        f"""
        SELECT COUNT_IF(concept IS NOT NULL) AS mapped, COUNT(*) AS total
        FROM read_parquet('{url}')
        WHERE symbol = ?
        """,
        [args.symbol],
    ).fetchone()
    mapped, total = cov_row
    coverage = mapped / total if total else 0.0

    rows = con.execute(
        f"""
        SELECT statement, raw_label_th, COUNT(*) AS occ,
               LIST(DISTINCT period ORDER BY period DESC) AS sample_periods
        FROM read_parquet('{url}')
        WHERE symbol = ?
          AND concept IS NULL
          AND length(raw_label_th) >= ?
        GROUP BY statement, raw_label_th
        ORDER BY occ DESC
        LIMIT ?
        """,
        [args.symbol, args.min_label_len, args.limit],
    ).fetchall()

    out = {
        "symbol": args.symbol,
        "revision": args.revision,
        "coverage_pre": coverage,
        "mapped": mapped,
        "total": total,
        "candidates": [
            {
                "statement": r[0],
                "raw_label_th": r[1],
                "occ": r[2],
                "sample_periods": list(r[3])[:6],
            }
            for r in rows
        ],
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
