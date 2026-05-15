"""Unit tests for ``scripts/coverage_gate.py``.

Synthetic local parquets exercise the pure-logic paths (counting non-null
concepts, evaluating the regression threshold, first-publish behaviour).
The HF-side `coverage_from_hf` is not exercised here because it requires
network — it gets covered by an integration smoke run in CI.
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.coverage_gate import (
    coverage_from_local,
    evaluate_gate,
    main,
)


_LINES_SCHEMA = pa.schema(
    [
        ("symbol", pa.string()),
        ("period", pa.string()),
        ("statement", pa.string()),
        ("concept", pa.string()),
        ("raw_label_th", pa.string()),
        ("value", pa.float64()),
        ("audit_basis", pa.string()),
        ("consolidation", pa.string()),
        ("filing_id", pa.string()),
    ]
)


def _write_lines(path: Path, concepts: list[str | None]) -> None:
    """Write a financial_lines parquet with the given concept values."""
    rows = [
        {
            "symbol": "TST",
            "period": "2025",
            "statement": "IS",
            "concept": c,
            "raw_label_th": "x",
            "value": float(i),
            "audit_basis": "audited",
            "consolidation": "consolidated",
            "filing_id": f"TST-2025-{i}",
        }
        for i, c in enumerate(concepts)
    ]
    # Use an explicit schema so an empty rows list still produces a parquet
    # with the `concept` column (otherwise pyarrow infers no schema).
    table = pa.Table.from_pylist(rows, schema=_LINES_SCHEMA)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_coverage_from_local_counts_non_null(tmp_path: Path) -> None:
    p = tmp_path / "lines.parquet"
    # 3 mapped, 1 unmapped → 75%
    _write_lines(p, ["revenue", "cogs", "gross_profit", None])

    non_null, total, pct = coverage_from_local(p)

    assert non_null == 3
    assert total == 4
    assert pct == pytest.approx(75.0)


def test_coverage_from_local_handles_empty_parquet(tmp_path: Path) -> None:
    p = tmp_path / "lines.parquet"
    _write_lines(p, [])

    non_null, total, pct = coverage_from_local(p)

    assert (non_null, total, pct) == (0, 0, 0.0)


def test_coverage_from_local_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        coverage_from_local(tmp_path / "nope.parquet")


def test_evaluate_gate_first_publish_passes() -> None:
    passed, msg = evaluate_gate(new_pct=80.0, prev_pct=None, max_regression_pp=1.0)
    assert passed is True
    assert "first publish" in msg.lower()


def test_evaluate_gate_pass_within_tolerance() -> None:
    # 0.5pp drop is within ±1pp tolerance
    passed, msg = evaluate_gate(new_pct=80.0, prev_pct=80.5, max_regression_pp=1.0)
    assert passed is True
    assert "Coverage OK" in msg


def test_evaluate_gate_pass_when_coverage_improves() -> None:
    passed, msg = evaluate_gate(new_pct=85.0, prev_pct=80.0, max_regression_pp=1.0)
    assert passed is True
    assert "+5.00pp" in msg


def test_evaluate_gate_fail_when_regression_exceeds_threshold() -> None:
    # 2pp drop > 1pp tolerance
    passed, msg = evaluate_gate(new_pct=78.0, prev_pct=80.0, max_regression_pp=1.0)
    assert passed is False
    assert "REGRESSION" in msg


def test_evaluate_gate_disabled_via_high_tolerance() -> None:
    """Setting tolerance >= 100 effectively disables the gate."""
    passed, msg = evaluate_gate(new_pct=10.0, prev_pct=90.0, max_regression_pp=999.0)
    assert passed is True
    assert "disabled" in msg.lower()


def test_evaluate_gate_exact_threshold_is_tolerated() -> None:
    """A drop equal to the threshold is allowed (strict >)."""
    passed, _ = evaluate_gate(new_pct=79.0, prev_pct=80.0, max_regression_pp=1.0)
    assert passed is True


def test_main_first_publish_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: when previous revision is absent, exit 0."""
    p = tmp_path / "new.parquet"
    _write_lines(p, ["revenue", "cogs", None])  # 66.7%

    # Stub HF lookup to simulate "first publish".
    monkeypatch.setattr(
        "scripts.coverage_gate.coverage_from_hf",
        lambda *a, **kw: None,
    )

    rc = main(
        [
            "--new",
            str(p),
            "--previous-revision",
            "main",
            "--max-regression-pp",
            "1.0",
        ]
    )
    assert rc == 0


def test_main_regression_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "new.parquet"
    # 50% coverage
    _write_lines(p, ["revenue", None])

    # Previous revision had 80% coverage → 30pp drop, way over threshold.
    monkeypatch.setattr(
        "scripts.coverage_gate.coverage_from_hf",
        lambda *a, **kw: (8, 10, 80.0),
    )

    rc = main(
        [
            "--new",
            str(p),
            "--previous-revision",
            "main",
            "--max-regression-pp",
            "1.0",
        ]
    )
    assert rc == 1


def test_main_within_tolerance_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "new.parquet"
    _write_lines(p, ["a", "b", "c", "d", None])  # 80%
    monkeypatch.setattr(
        "scripts.coverage_gate.coverage_from_hf",
        lambda *a, **kw: (805, 1000, 80.5),
    )
    rc = main(
        [
            "--new",
            str(p),
            "--previous-revision",
            "main",
            "--max-regression-pp",
            "1.0",
        ]
    )
    assert rc == 0
