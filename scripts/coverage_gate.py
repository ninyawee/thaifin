"""Concept-coverage regression gate for the dataset publish pipeline.

Slice #18 of PRD #11. Before a new revision is uploaded to HuggingFace,
compare its concept-mapping coverage % against the previously published
revision. If coverage drops by more than ``--max-regression-pp`` percentage
points, exit non-zero so the workflow aborts before publishing.

Coverage is defined as::

    coverage = non_null_concept_count / total_count

(rows in ``financial_lines.parquet`` whose ``concept`` field is not null,
divided by total rows). A row with ``concept=NULL`` is a raw-label that
hasn't been mapped to a curated concept yet — coverage going down means
either new symbols brought in unfamiliar Thai labels, or somebody removed
entries from ``data/concepts.csv``. Either way, surface it before publishing.

Previous-revision coverage is computed by reading the same parquet from the
HF dataset repo via DuckDB-over-HTTP. No local caching needed; this only
runs once per publish.

Usage::

    python scripts/coverage_gate.py \
        --new final/financial_lines.parquet \
        --previous-revision main \
        --max-regression-pp 1.0

Exit codes:
    0  — coverage is within tolerance (or no previous revision exists yet)
    1  — coverage regression exceeds tolerance; build should NOT publish
    2  — invalid input (missing file, bad arg, etc.)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import duckdb
import pyarrow.parquet as pq

DEFAULT_HF_REPO_ID = "ninyawee/thaifin-financials"
DEFAULT_FILE = "financial_lines.parquet"


def coverage_from_local(parquet_path: Path) -> tuple[int, int, float]:
    """Compute (non_null, total, pct) for ``concept`` in a local parquet.

    ``pct`` is in [0, 100]. A parquet with zero rows has 0% coverage.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet not found: {parquet_path}")
    table = pq.read_table(parquet_path, columns=["concept"])
    total = table.num_rows
    if total == 0:
        return 0, 0, 0.0
    # Pyarrow null_count is fast and avoids materializing the column.
    null_count = table.column("concept").null_count
    non_null = total - null_count
    pct = (non_null / total) * 100.0
    return non_null, total, pct


def _hf_url(repo_id: str, revision: str, filename: str) -> str:
    """Build the HF dataset HTTPS URL for a parquet at a given revision."""
    return (
        f"https://huggingface.co/datasets/{repo_id}/resolve/{revision}/{filename}"
    )


def coverage_from_hf(
    repo_id: str,
    revision: str,
    filename: str = DEFAULT_FILE,
) -> tuple[int, int, float] | None:
    """Compute coverage at a given HF revision via DuckDB-over-HTTP.

    Returns ``None`` if the file doesn't exist at that revision (e.g. first
    publish, or the revision predates the schema). Anything else (network
    failure, bad token, malformed parquet) raises.
    """
    url = _hf_url(repo_id, revision, filename)
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
    except duckdb.Error:
        # httpfs may already be bundled / loaded in newer duckdb builds.
        pass

    # If HF_TOKEN is set, pass it as a bearer header so private/gated
    # datasets work too.
    token = os.environ.get("HF_TOKEN")
    if token:
        con.execute(
            f"SET extra_http_headers={{'Authorization': 'Bearer {token}'}};"
        )

    try:
        result = con.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE concept IS NOT NULL) AS non_null
            FROM read_parquet('{url}')
            """
        ).fetchone()
    except duckdb.Error as e:
        msg = str(e).lower()
        if any(
            needle in msg for needle in ("404", "not found", "could not", "http error")
        ):
            return None
        raise

    if result is None:
        return None
    total, non_null = int(result[0]), int(result[1])
    if total == 0:
        return 0, 0, 0.0
    pct = (non_null / total) * 100.0
    return non_null, total, pct


def evaluate_gate(
    new_pct: float,
    prev_pct: float | None,
    max_regression_pp: float,
) -> tuple[bool, str]:
    """Evaluate whether the new build passes the gate.

    Returns ``(passed, message)``. ``passed`` is True iff the gate allows
    publishing. ``message`` is a human-readable summary, suitable for
    printing to stdout/stderr or a CI job log.

    Special-cases:
      - ``prev_pct is None`` → first publish; pass with a note.
      - ``max_regression_pp >= 100`` → effectively disabled; always pass.
    """
    if prev_pct is None:
        return True, (
            f"No previous revision found; treating as first publish. "
            f"New coverage = {new_pct:.2f}%."
        )

    delta = new_pct - prev_pct
    if max_regression_pp >= 100:
        return True, (
            f"Gate disabled (max_regression_pp={max_regression_pp}). "
            f"prev={prev_pct:.2f}% new={new_pct:.2f}% Δ={delta:+.2f}pp."
        )

    if delta < -max_regression_pp:
        return False, (
            f"COVERAGE REGRESSION: prev={prev_pct:.2f}% new={new_pct:.2f}% "
            f"Δ={delta:+.2f}pp (tolerance ±{max_regression_pp}pp). "
            f"Refusing to publish — investigate which symbols/labels regressed."
        )

    return True, (
        f"Coverage OK: prev={prev_pct:.2f}% new={new_pct:.2f}% "
        f"Δ={delta:+.2f}pp (tolerance ±{max_regression_pp}pp)."
    )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Concept-coverage regression gate before HF publish."
    )
    p.add_argument(
        "--new",
        type=Path,
        required=True,
        help="Path to the new financial_lines.parquet built this run.",
    )
    p.add_argument(
        "--previous-revision",
        default="main",
        help=(
            "HF git ref to compare against (tag like '2026.04' or 'main'). "
            "Default: main."
        ),
    )
    p.add_argument(
        "--max-regression-pp",
        type=float,
        default=1.0,
        help=(
            "Max allowed coverage drop in percentage points (default: 1.0). "
            "Set to 999 to disable the gate (e.g. for the very first publish)."
        ),
    )
    p.add_argument(
        "--repo-id",
        default=DEFAULT_HF_REPO_ID,
        help=f"HF dataset repo id (default: {DEFAULT_HF_REPO_ID}).",
    )
    p.add_argument(
        "--filename",
        default=DEFAULT_FILE,
        help=f"Parquet filename inside the HF repo (default: {DEFAULT_FILE}).",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        new_non_null, new_total, new_pct = coverage_from_local(args.new)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(
        f"New build:  {new_non_null:,}/{new_total:,} mapped concepts "
        f"({new_pct:.2f}%)"
    )

    prev_result = coverage_from_hf(
        args.repo_id, args.previous_revision, args.filename
    )
    if prev_result is None:
        prev_pct: float | None = None
        print(
            f"Previous revision '{args.previous_revision}' not found at "
            f"{args.repo_id}/{args.filename} — first publish."
        )
    else:
        prev_non_null, prev_total, prev_pct = prev_result
        print(
            f"Previous:   {prev_non_null:,}/{prev_total:,} mapped concepts "
            f"({prev_pct:.2f}%) @ {args.previous_revision}"
        )

    passed, message = evaluate_gate(
        new_pct, prev_pct, args.max_regression_pp
    )
    print(message)
    return 0 if passed else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
