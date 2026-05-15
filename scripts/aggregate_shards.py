"""Aggregate per-shard parquets into the final published dataset.

Slice #18 of PRD #11. The monthly cron workflow runs 36 letter-sharded
backfill jobs in parallel; each shard emits its own per-table parquets into
``shard-output/`` and uploads them as a workflow artifact. After all shards
finish, this script downloads every artifact (laid out as
``all-shards/shard-<L>/<table>.parquet``) and concatenates them into one
``final/<table>.parquet`` per table.

Usage::

    python scripts/aggregate_shards.py \
        --in-dir all-shards/ \
        --out-dir final/

Side effects:
    - Writes ``final/<table>.parquet`` for each known table type.
    - Copies ``concepts.parquet`` from one shard (verifies all shards agree
      via SHA256, since concepts are a curated input — they MUST be byte
      identical across shards).
    - Optionally merges per-shard ``state.json`` files into a single
      top-level ``data/state.json`` if any shard produced one.
    - Prints row counts per table to stdout.

The script is idempotent and pure (no network, no secrets).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq

# Tables that are concatenated across shards (each shard contributes rows).
CONCAT_TABLES: tuple[str, ...] = (
    "financial_lines",
    "auditor_reports",
    "notes_text",
    "filings",
)

# Tables that are byte-identical across shards (curated inputs, just copied).
COPY_TABLES: tuple[str, ...] = ("concepts",)


def _sha256(path: Path) -> str:
    """Return hex SHA256 of the file at ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_shard_files(in_dir: Path, table: str) -> list[Path]:
    """Find every ``<table>.parquet`` under any shard subdir of ``in_dir``.

    Layout: ``in_dir/shard-<letter>/<table>.parquet``. We use a recursive
    glob so we tolerate either layout (artifact downloaded into a named
    subdir, or unpacked flat).
    """
    return sorted(in_dir.rglob(f"{table}.parquet"))


def concat_table(in_dir: Path, table: str, out_dir: Path) -> int:
    """Concatenate every ``<table>.parquet`` shard into ``out_dir/<table>.parquet``.

    Returns the total row count written. If no shards exist for the table,
    returns 0 and writes nothing (the table is simply absent from the
    final dataset for this build).

    Schema is taken from the first non-empty shard. Mismatched schemas are
    a build error — refuse to silently coerce types.
    """
    shards = _find_shard_files(in_dir, table)
    if not shards:
        print(f"  [{table}] no shards found, skipping", flush=True)
        return 0

    tables: list[pa.Table] = []
    base_schema: pa.Schema | None = None
    for shard_path in shards:
        t = pq.read_table(shard_path)
        if base_schema is None:
            base_schema = t.schema
        elif not t.schema.equals(base_schema):
            raise ValueError(
                f"Schema mismatch in {shard_path} for table {table!r}:\n"
                f"  expected: {base_schema}\n"
                f"  got:      {t.schema}"
            )
        tables.append(t)

    combined = pa.concat_tables(tables)
    out_path = out_dir / f"{table}.parquet"
    pq.write_table(combined, out_path)
    print(
        f"  [{table}] {len(shards)} shards -> {combined.num_rows} rows "
        f"({out_path.stat().st_size / 1e6:.2f} MB)",
        flush=True,
    )
    return combined.num_rows


def copy_curated_table(in_dir: Path, table: str, out_dir: Path) -> int:
    """Copy a curated input table that should be byte-identical across shards.

    Verifies SHA256 matches across all shard copies. Returns the row count
    of the copied table, or 0 if no shards have it.
    """
    shards = _find_shard_files(in_dir, table)
    if not shards:
        print(f"  [{table}] no shards found, skipping", flush=True)
        return 0

    digests = {p: _sha256(p) for p in shards}
    unique = set(digests.values())
    if len(unique) > 1:
        # Curated tables MUST agree byte-for-byte. Surface every mismatch.
        details = "\n".join(f"  {d} {p}" for p, d in digests.items())
        raise ValueError(
            f"Curated table {table!r} differs across shards:\n{details}"
        )

    src = shards[0]
    dst = out_dir / f"{table}.parquet"
    shutil.copyfile(src, dst)
    rows = pq.read_metadata(dst).num_rows
    print(
        f"  [{table}] copied from {src.name} -> {rows} rows "
        f"(SHA256 verified across {len(shards)} shards)",
        flush=True,
    )
    return rows


def merge_state_files(in_dir: Path, out_path: Path) -> int:
    """Merge per-shard ``state.json`` files into a single state file.

    Each shard's state file is a dict keyed by ``filing_id``. Merge by
    union; on key collision (same filing_id seen by two shards), prefer
    the latest ``fetched_at`` value.

    Returns the number of filings in the merged state. If no shard produced
    a state file, writes an empty object and returns 0.
    """
    shards = sorted(in_dir.rglob("state.json"))
    merged: dict[str, dict] = {}
    for shard_path in shards:
        try:
            data = json.loads(shard_path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {shard_path}: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected dict in {shard_path}, got {type(data).__name__}"
            )
        for filing_id, entry in data.items():
            existing = merged.get(filing_id)
            if existing is None:
                merged[filing_id] = entry
                continue
            # Prefer the entry with the latest fetched_at (lexicographic on
            # ISO-8601 strings is correct).
            new_ts = entry.get("fetched_at", "")
            old_ts = existing.get("fetched_at", "")
            if new_ts > old_ts:
                merged[filing_id] = entry

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2, sort_keys=True))
    print(
        f"  [state] merged {len(shards)} shard state files -> "
        f"{len(merged)} filings in {out_path}",
        flush=True,
    )
    return len(merged)


def aggregate(in_dir: Path, out_dir: Path) -> dict[str, int]:
    """Aggregate every shard under ``in_dir`` into ``out_dir``.

    Returns a dict mapping table name -> row count.
    """
    if not in_dir.exists():
        raise FileNotFoundError(f"in_dir does not exist: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    print(f"Aggregating shards from {in_dir} -> {out_dir}", flush=True)
    for table in CONCAT_TABLES:
        counts[table] = concat_table(in_dir, table, out_dir)
    for table in COPY_TABLES:
        counts[table] = copy_curated_table(in_dir, table, out_dir)
    return counts


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Aggregate per-shard parquets into final dataset."
    )
    p.add_argument(
        "--in-dir",
        type=Path,
        required=True,
        help="Directory containing per-shard subdirectories of parquets.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for the merged final/<table>.parquet files.",
    )
    p.add_argument(
        "--state-out",
        type=Path,
        default=Path("data/state.json"),
        help="Where to write the merged state.json (default: data/state.json).",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    counts = aggregate(args.in_dir, args.out_dir)
    # State merge is best-effort; absence isn't fatal.
    try:
        merge_state_files(args.in_dir, args.state_out)
    except Exception as e:  # pragma: no cover - defensive, surfaces in CI logs
        print(f"  [state] merge skipped due to error: {e}", flush=True)

    total = sum(counts.values())
    print(f"Aggregation done: {total} total rows across {len(counts)} tables.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
