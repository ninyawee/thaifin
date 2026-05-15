"""Unit tests for ``scripts/aggregate_shards.py``.

Builds synthetic per-shard parquets in a tmp dir, runs the aggregator, and
verifies row counts + curated-table SHA verification + state.json merge.
No network IO, no HF, no dependency on Agent C/E's scripts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.aggregate_shards import (
    CONCAT_TABLES,
    aggregate,
    concat_table,
    copy_curated_table,
    merge_state_files,
)


def _write_parquet(path: Path, rows: list[dict]) -> None:
    """Write ``rows`` to a parquet at ``path`` (creating parents)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)


def _make_shard(
    in_dir: Path, letter: str, financial_rows: int, concepts: list[dict]
) -> Path:
    """Create ``in_dir/shard-<letter>/`` populated with all required tables."""
    shard = in_dir / f"shard-{letter}"
    _write_parquet(
        shard / "financial_lines.parquet",
        [
            {
                "symbol": f"{letter}TEST",
                "period": "2025",
                "statement": "IS",
                "concept": "revenue" if i % 2 == 0 else None,
                "raw_label_th": "รายได้",
                "value": float(i),
                "audit_basis": "audited",
                "consolidation": "consolidated",
                "filing_id": f"{letter}TEST-2025-{i}",
            }
            for i in range(financial_rows)
        ],
    )
    _write_parquet(
        shard / "auditor_reports.parquet",
        [
            {
                "filing_id": f"{letter}TEST-2025-{i}",
                "symbol": f"{letter}TEST",
                "period": "2025",
                "audit_basis": "audited",
                "auditor_firm": "EY",
                "opinion_type": "unqualified",
                "going_concern_emphasis": False,
                "raw_text_md": "...",
            }
            for i in range(2)
        ],
    )
    _write_parquet(
        shard / "notes_text.parquet",
        [
            {
                "filing_id": f"{letter}TEST-2025-{i}",
                "symbol": f"{letter}TEST",
                "period": "2025",
                "raw_text_md": "Notes...",
            }
            for i in range(2)
        ],
    )
    _write_parquet(
        shard / "filings.parquet",
        [
            {
                "filing_id": f"{letter}TEST-2025-{i}",
                "symbol": f"{letter}TEST",
                "period": "2025",
                "audit_basis": "audited",
                "source_url": f"https://example.test/{letter}/{i}.zip",
                "source_sha256": "deadbeef" * 8,
                "fetched_at": "2026-05-15T00:00:00Z",
            }
            for i in range(3)
        ],
    )
    _write_parquet(shard / "concepts.parquet", concepts)
    return shard


def test_concat_table_merges_all_shards(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    out_dir = tmp_path / "final"
    out_dir.mkdir()
    concepts = [{"concept": "revenue", "statement": "IS", "label_en": "Revenue"}]
    _make_shard(in_dir, "A", financial_rows=4, concepts=concepts)
    _make_shard(in_dir, "B", financial_rows=6, concepts=concepts)

    rows = concat_table(in_dir, "financial_lines", out_dir)

    assert rows == 10
    out = pq.read_table(out_dir / "financial_lines.parquet")
    assert out.num_rows == 10
    # Sanity-check both letters made it in
    symbols = set(out.column("symbol").to_pylist())
    assert symbols == {"ATEST", "BTEST"}


def test_concat_table_handles_missing_shards(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    in_dir.mkdir()
    out_dir = tmp_path / "final"
    out_dir.mkdir()

    rows = concat_table(in_dir, "financial_lines", out_dir)

    assert rows == 0
    assert not (out_dir / "financial_lines.parquet").exists()


def test_concat_table_rejects_schema_mismatch(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    out_dir = tmp_path / "final"
    out_dir.mkdir()
    _write_parquet(
        in_dir / "shard-A" / "financial_lines.parquet",
        [{"symbol": "A", "value": 1.0}],
    )
    _write_parquet(
        in_dir / "shard-B" / "financial_lines.parquet",
        [{"symbol": "B", "value": "not-a-float"}],   # wrong type
    )
    with pytest.raises(ValueError, match="Schema mismatch"):
        concat_table(in_dir, "financial_lines", out_dir)


def test_copy_curated_table_verifies_sha_match(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    out_dir = tmp_path / "final"
    out_dir.mkdir()
    concepts = [
        {"concept": "revenue", "statement": "IS", "label_en": "Revenue"},
        {"concept": "capex", "statement": "CF", "label_en": "CapEx"},
    ]
    _make_shard(in_dir, "A", 1, concepts)
    _make_shard(in_dir, "B", 1, concepts)

    rows = copy_curated_table(in_dir, "concepts", out_dir)

    assert rows == 2
    assert (out_dir / "concepts.parquet").exists()


def test_copy_curated_table_fails_on_sha_mismatch(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    out_dir = tmp_path / "final"
    out_dir.mkdir()
    _make_shard(in_dir, "A", 1, [{"concept": "revenue", "statement": "IS", "label_en": "Revenue"}])
    _make_shard(in_dir, "B", 1, [{"concept": "capex", "statement": "CF", "label_en": "CapEx"}])

    with pytest.raises(ValueError, match="differs across shards"):
        copy_curated_table(in_dir, "concepts", out_dir)


def test_aggregate_full_pipeline(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    out_dir = tmp_path / "final"
    concepts = [{"concept": "revenue", "statement": "IS", "label_en": "Revenue"}]
    _make_shard(in_dir, "A", financial_rows=5, concepts=concepts)
    _make_shard(in_dir, "B", financial_rows=7, concepts=concepts)
    _make_shard(in_dir, "C", financial_rows=3, concepts=concepts)

    counts = aggregate(in_dir, out_dir)

    assert counts["financial_lines"] == 15
    assert counts["auditor_reports"] == 6   # 2 per shard × 3 shards
    assert counts["notes_text"] == 6
    assert counts["filings"] == 9            # 3 per shard × 3 shards
    assert counts["concepts"] == 1
    for table in CONCAT_TABLES:
        assert (out_dir / f"{table}.parquet").exists()
    assert (out_dir / "concepts.parquet").exists()


def test_merge_state_files_unions_and_picks_latest_fetched_at(tmp_path: Path) -> None:
    in_dir = tmp_path / "shards"
    (in_dir / "shard-A").mkdir(parents=True)
    (in_dir / "shard-B").mkdir(parents=True)
    (in_dir / "shard-A" / "state.json").write_text(
        json.dumps(
            {
                "F1": {"sha256": "aaa", "fetched_at": "2026-05-01T00:00:00Z"},
                "F2": {"sha256": "bbb", "fetched_at": "2026-05-10T00:00:00Z"},
            }
        )
    )
    (in_dir / "shard-B" / "state.json").write_text(
        json.dumps(
            {
                # F2 collision: B has newer fetched_at; should win.
                "F2": {"sha256": "ccc", "fetched_at": "2026-05-20T00:00:00Z"},
                "F3": {"sha256": "ddd", "fetched_at": "2026-05-15T00:00:00Z"},
            }
        )
    )

    out = tmp_path / "data" / "state.json"
    n = merge_state_files(in_dir, out)

    assert n == 3
    merged = json.loads(out.read_text())
    assert set(merged.keys()) == {"F1", "F2", "F3"}
    # F2's value should be the newer one from shard-B
    assert merged["F2"]["sha256"] == "ccc"


def test_merge_state_files_no_shards(tmp_path: Path) -> None:
    """Empty input writes an empty object (still valid JSON)."""
    out = tmp_path / "state.json"
    n = merge_state_files(tmp_path, out)
    assert n == 0
    assert json.loads(out.read_text()) == {}
