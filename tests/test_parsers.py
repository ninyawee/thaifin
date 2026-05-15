"""Fixture-driven tests for the three SEC IDISC parsers.

Fixtures live in ``tests/sample_data/``:

- ``PTT_2025_annual.zip``  — full PTT FY2025 filing (audited, ~1.1 MB)
- ``COM7_2025Q1.zip``      — full COM7 Q1 2025 filing (reviewed, ~380 KB)

Both are real downloads from the SEC IDISC pinned in
``data/concepts.csv``. The COM7 zip is included even though COM7's modern
sheet layout differs from PTT — the test asserts that the parser
gracefully reports zero rows there rather than crashing (slice #15 ships
modern-PTT-only support; broader symbol coverage is slice #17).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from thaifin.parsers import (
    parse_auditor_report,
    parse_financial_statements,
    parse_notes,
)
from thaifin.parsers.financial_statements import classify_sheet

FIXTURE_DIR = Path(__file__).parent / "sample_data"
PTT_ZIP = FIXTURE_DIR / "PTT_2025_annual.zip"
COM7_ZIP = FIXTURE_DIR / "COM7_2025Q1.zip"

# Canonical Thai labels we expect to find in the PTT FY2025 filing.
PTT_CAPEX_LABEL = (
    "เงินสดจ่ายสำหรับที่ดิน อาคารและอุปกรณ์ และอสังหาริมทรัพย์เพื่อการลงทุน"
)
PTT_CAPEX_VALUE = -159_512_958_954
PTT_REVENUE_LABEL = "รายได้จากการขายและการให้บริการ"
PTT_REVENUE_VALUE = 2_662_144_872_754
PTT_GROSS_PROFIT_LABEL = "กำไรขั้นต้น"
PTT_GROSS_PROFIT_VALUE = 272_935_086_154


def _read_member(zip_path: Path, name_prefix: str) -> bytes | None:
    with zipfile.ZipFile(zip_path) as zf:
        for n in zf.namelist():
            if n.upper().startswith(name_prefix):
                return zf.read(n)
    return None


# --- Sheet classification ---------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("BS-Asset", "BS"),
        ("BS-Liability", "BS"),
        ("BS-Equity", "BS"),
        ("PL_Accum", "IS"),
        ("PL_Q", "IS"),
        ("OCI_Accum", "IS"),
        ("OCI_Q", "IS"),
        ("Cash flow", "CF"),
        ("EQ Change Conso", "EQ"),
        ("EQ Change PTT", "EQ"),
        # Mid-era PTT variants
        ("BS-Asset Consol", "BS"),
        ("BS-Lai Consol", "BS"),
        ("กำไรขาดทุน Accum", "IS"),
        ("OCI Accum", "IS"),
        ("งบกระแสเงินสด", "CF"),
        # Unknown sheet
        ("Sheet1", None),
        ("Cover", None),
    ],
)
def test_classify_sheet(name: str, expected: str | None) -> None:
    assert classify_sheet(name) == expected


# --- PTT FY2025 financial statements ---------------------------------------


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_financial_statements_capex() -> None:
    data = _read_member(PTT_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="PTT-2025-A",
        period="2025",
        audit_basis="audited",
        symbol="PTT",
    )
    capex = [
        r for r in rows
        if r.raw_label_th == PTT_CAPEX_LABEL and r.consolidation == "consolidated"
    ]
    assert len(capex) == 1
    assert int(capex[0].value) == PTT_CAPEX_VALUE
    assert capex[0].statement == "CF"


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_financial_statements_revenue_and_gross_profit() -> None:
    data = _read_member(PTT_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="PTT-2025-A",
        period="2025",
        audit_basis="audited",
        symbol="PTT",
    )

    def first(label: str, consolidation: str = "consolidated"):
        matches = [
            r for r in rows
            if r.raw_label_th == label and r.consolidation == consolidation
        ]
        assert matches, f"label not found: {label!r}"
        return matches[0]

    rev = first(PTT_REVENUE_LABEL)
    gp = first(PTT_GROSS_PROFIT_LABEL)
    assert int(rev.value) == PTT_REVENUE_VALUE
    assert rev.statement == "IS"
    assert int(gp.value) == PTT_GROSS_PROFIT_VALUE
    assert gp.statement == "IS"


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_covers_all_four_statements() -> None:
    data = _read_member(PTT_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="PTT-2025-A",
        period="2025",
        audit_basis="audited",
        symbol="PTT",
    )
    statements = {r.statement for r in rows}
    assert statements == {"BS", "IS", "CF", "EQ"}


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_has_both_consolidations() -> None:
    data = _read_member(PTT_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="PTT-2025-A",
        period="2025",
        audit_basis="audited",
        symbol="PTT",
    )
    consolidations = {r.consolidation for r in rows}
    assert consolidations == {"consolidated", "company"}


# --- COM7 Q1 2025 (graceful zero-rows on unsupported layout) ---------------


@pytest.mark.skipif(not COM7_ZIP.exists(), reason="fixture missing")
def test_com7_q1_does_not_crash() -> None:
    """COM7 ships a different sheet layout (numeric page-range names);
    slice #15 only supports the modern PTT layout, so the parser should
    return zero rows rather than raise."""
    data = _read_member(COM7_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="COM7-2025Q1",
        period="2025Q1",
        audit_basis="reviewed",
        symbol="COM7",
    )
    # Layout is unsupported in v0 → zero rows is the contract.
    assert isinstance(rows, list)


# --- PTT FY2025 auditor report ---------------------------------------------


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_auditor_report_unqualified_with_no_gc() -> None:
    data = _read_member(PTT_ZIP, "AUDITOR_REPORT.")
    assert data is not None
    row = parse_auditor_report(
        data,
        filing_id="PTT-2025-A",
        symbol="PTT",
        period="2025",
        audit_basis="audited",
    )
    assert row.opinion_type == "unqualified"
    assert row.going_concern_emphasis is False
    assert row.auditor_firm == "EY"
    assert row.signing_date is not None
    assert row.signing_date.year == 2026
    assert row.raw_text_md, "raw markdown should be non-empty"
    # Signing partner is best-effort but PTT FY2025 has it cleanly.
    assert row.signing_partner == "กิตติพันธ์ เกียรติสมภพ"


# --- PTT FY2025 notes ------------------------------------------------------


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_notes_non_empty_markdown() -> None:
    data = _read_member(PTT_ZIP, "NOTES.")
    assert data is not None
    row = parse_notes(
        data,
        filing_id="PTT-2025-A",
        symbol="PTT",
        period="2025",
    )
    # Notes are large (~400 KB markdown for PTT FY2025).
    assert len(row.raw_text_md) > 10_000
    assert "หมายเหตุประกอบงบการเงิน" in row.raw_text_md
