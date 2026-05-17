"""Fixture-driven tests for the three SEC IDISC parsers.

Fixtures live in ``tests/sample_data/``:

- ``PTT_2025_annual.zip``  — full PTT FY2025 filing (audited, ~1.1 MB)
- ``COM7_2025Q1.zip``      — full COM7 Q1 2025 filing (reviewed, ~380 KB)

Both are real downloads from the SEC IDISC pinned in
``data/concepts.csv``. The COM7 zip is included even though COM7's modern
sheet layout differs from PTT — the test asserts that the parser
gracefully reports zero rows there rather than crashing (slice #15 ships
modern-PTT-only support; broader symbol coverage is slice #17).

Synthetic XLSX fixtures (built in-memory with openpyxl) cover the parser
robustness fixes added in slice #20: line-wrap merging, value-continuity
guardrail, hidden-sheet filtering, and currency-scale detection.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import openpyxl
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
        # Generic short-code fallbacks for CPALL / SCB / BDMS (issue #24)
        ("BS 3-5", "BS"),
        ("BS Conso-3-5", "BS"),
        ("BS&PL Thai", "BS"),
        ("BS", "BS"),
        ("PL 3M 6-8", "IS"),
        ("PL (3M)", "IS"),
        ("PL-T (3)", "IS"),
        ("PL", "IS"),
        ("CF 12-15", "CF"),
        ("CF", "CF"),
        # Short-code regex must not greedy-match other prefixes.
        ("BSE", None),
        ("PLN", None),
        ("CFA", None),
        # Unknown sheet — ADVANC's SFP/SCI/SCE/SCF stays unrecognised.
        ("SFP(P.3-5)", None),
        ("SCI (3ด) P.7", None),
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


# --- PTT FY2025 line-wrap merge — real-fixture regression ------------------


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_phantom_fragments_are_merged() -> None:
    """The cash-flow phantom fragments observed in v0 must NOT appear as
    standalone labels — they should be folded into their head row.

    Before slice #20 these fragments were the top alias candidates for
    half the cash-flow concepts, poisoning the coverage signal.
    """
    data = _read_member(PTT_ZIP, "FINANCIAL_STATEMENTS.")
    assert data is not None
    rows = parse_financial_statements(
        data,
        filing_id="PTT-2025-A",
        period="2025",
        audit_basis="audited",
        symbol="PTT",
    )
    labels = {r.raw_label_th for r in rows}
    # Phantom fragments must no longer appear standalone.
    assert "และหนี้สินดำเนินงาน" not in labels
    assert "ที่ยังไม่เกิดขึ้นจริง" not in labels
    # The merged composite label must exist.
    assert (
        "กำไรจากการดำเนินงานก่อนการเปลี่ยนแปลงในสินทรัพย์ และหนี้สินดำเนินงาน"
        in labels
    )


@pytest.mark.skipif(not PTT_ZIP.exists(), reason="fixture missing")
def test_ptt_2025_capex_value_unchanged_after_merge() -> None:
    """Line-wrap merging must not regress the canonical capex value."""
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
        if r.raw_label_th == PTT_CAPEX_LABEL
        and r.consolidation == "consolidated"
    ]
    assert len(capex) == 1
    assert int(capex[0].value) == PTT_CAPEX_VALUE


# --- Synthetic XLSX fixtures for the parser-robustness fixes ---------------


def _build_xlsx_bytes(
    sheets: dict[str, list[list[object]]],
) -> bytes:
    """Build an in-memory XLSX with the given ``{sheet_name: rows}``.

    Each row is a list of cell values (None, str, int, float). The default
    sheet auto-created by openpyxl is removed.
    """
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for r, row in enumerate(rows, start=1):
            for c, val in enumerate(row, start=1):
                ws.cell(row=r, column=c, value=val)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cf_header_rows() -> list[list[object]]:
    """A minimal cash-flow header band that the parser recognises."""
    # Column layout: col 2 = label (section-header col), col 3 = label (item col),
    # col 9 = consolidated value, col 13 = company value.
    return [
        [None] * 15,
        [None, "Mock Co.", None, None, None, None, None, None, None, None, None, None, None, None, None],
        [None, "งบกระแสเงินสด", None, None, None, None, None, None, None, None, None, None, None, None, None],
        [None] * 15,
        [None] * 15,
        [None, None, None, None, None, None, None, None, None, None, None, None, None, None, "หน่วย : บาท"],
        [None, None, None, None, None, None, None, None, "งบการเงินรวม", None, None, None, "งบการเงินเฉพาะกิจการ", None, None],
        [None, None, None, None, None, None, None, None, "2568", None, "2567", None, "2568", None, "2567"],
        [None] * 15,
    ]


def test_fix1_line_wrap_merge_consolidates_two_rows() -> None:
    """Fix 1: row N has label + empty values; row N+1 has continuation
    label (leading whitespace) + values → emit one merged row."""
    rows = _cf_header_rows()
    # Row 10: head label, empty values
    rows.append(
        [None, None, "กำไรจากการดำเนินงานก่อนการเปลี่ยนแปลงในสินทรัพย์",
         None, None, None, None, None, None, None, None, None, None, None, None]
    )
    # Row 11: leading-whitespace tail label, with values
    rows.append(
        [None, None, "   และหนี้สินดำเนินงาน",
         None, None, None, None, None, 355_139_365_210, None,
         404_542_353_867, None, 40_182_417_264, None, 47_975_544_467]
    )
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-1", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    labels = [r.raw_label_th for r in out]
    # The orphan fragment must NOT appear.
    assert "และหนี้สินดำเนินงาน" not in labels
    # The merged composite must appear.
    merged = (
        "กำไรจากการดำเนินงานก่อนการเปลี่ยนแปลงในสินทรัพย์ และหนี้สินดำเนินงาน"
    )
    assert merged in labels
    # Value must come from the tail row.
    consolidated = [
        r for r in out
        if r.raw_label_th == merged and r.consolidation == "consolidated"
    ]
    assert len(consolidated) == 1
    assert consolidated[0].value == 355_139_365_210


def test_fix1_guardrail_no_merge_when_both_rows_have_values() -> None:
    """Fix 1 guardrail: two rows that BOTH have values are separate line
    items and must not be merged even when the second label could pass
    the continuation heuristic."""
    rows = _cf_header_rows()
    # Row 10: head label, WITH values
    rows.append(
        [None, None, "หัวข้อแรก",
         None, None, None, None, None, 100, None, 200, None, 50, None, 60]
    )
    # Row 11: leading-whitespace label that would look like continuation,
    # but it has its own values — must remain a separate row.
    rows.append(
        [None, None, "   และหัวข้อรอง",
         None, None, None, None, None, 300, None, 400, None, 70, None, 80]
    )
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-2", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    labels = [r.raw_label_th for r in out]
    # Both originals must appear; no merge.
    assert "หัวข้อแรก" in labels
    assert "และหัวข้อรอง" in labels
    assert "หัวข้อแรก และหัวข้อรอง" not in labels


def test_fix1_no_merge_when_both_rows_empty() -> None:
    """Two empty rows produce zero output — neither emits."""
    rows = _cf_header_rows()
    rows.append(
        [None, None, "หัวข้อส่วน",
         None, None, None, None, None, None, None, None, None, None, None, None]
    )
    rows.append(
        [None, None, "   ของส่วน",
         None, None, None, None, None, None, None, None, None, None, None, None]
    )
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-3", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    labels = [r.raw_label_th for r in out]
    assert labels == []


def test_fix2_hidden_sheets_are_skipped() -> None:
    """Fix 2: sheets matching ``^_`` or ``^DS_INTERNAL`` must be skipped.

    Build a workbook with one real Cash flow sheet plus three hidden
    sheets; only the Cash flow rows should appear in the output.
    """
    real_rows = _cf_header_rows()
    real_rows.append(
        [None, None, "เงินสดสุทธิจากการดำเนินงาน",
         None, None, None, None, None, 12_345, None, 0, None, 0, None, 0]
    )
    hidden_rows = _cf_header_rows()
    hidden_rows.append(
        [None, None, "should not appear",
         None, None, None, None, None, 99_999, None, 0, None, 0, None, 0]
    )
    xlsx = _build_xlsx_bytes({
        "Cash flow": real_rows,
        "_com.sap.ip.bi.xl.hiddensheet": hidden_rows,
        "DS_INTERNAL_SETTINGS_STORAGE": hidden_rows,
        "_scratch": hidden_rows,
    })
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-4", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    labels = [r.raw_label_th for r in out]
    assert "เงินสดสุทธิจากการดำเนินงาน" in labels
    assert "should not appear" not in labels


def test_fix3_currency_scale_thousands_baht_multiplier() -> None:
    """Fix 3: a sheet declaring ``(พันบาท)`` must have its numeric values
    multiplied by 1000 before emission."""
    # Build with the thousands-of-baht marker in the page-header band.
    rows: list[list[object]] = [
        [None] * 15,
        [None, "Mock Co.", None, None, None, None, None, None, None, None, None, None, None, None, None],
        [None, "งบกระแสเงินสด", None, None, None, None, None, None, None, None, None, None, None, None, None],
        [None] * 15,
        [None] * 15,
        [None, None, None, None, None, None, None, None, None, None, None, None, None, None, "หน่วย : พันบาท"],
        [None, None, None, None, None, None, None, None, "งบการเงินรวม", None, None, None, "งบการเงินเฉพาะกิจการ", None, None],
        [None, None, None, None, None, None, None, None, "2568", None, "2567", None, "2568", None, "2567"],
        [None] * 15,
        [None, None, "เงินสดสุทธิจากการดำเนินงาน",
         None, None, None, None, None, 12_345, None, 0, None, 678, None, 0],
    ]
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-5", period="2025Q1",
        audit_basis="reviewed", symbol="MOCK",
    )
    consolidated = [
        r for r in out
        if r.raw_label_th == "เงินสดสุทธิจากการดำเนินงาน"
        and r.consolidation == "consolidated"
    ]
    assert len(consolidated) == 1
    # 12_345 * 1000 = 12_345_000
    assert consolidated[0].value == 12_345_000
    company = [
        r for r in out
        if r.raw_label_th == "เงินสดสุทธิจากการดำเนินงาน"
        and r.consolidation == "company"
    ]
    assert len(company) == 1
    assert company[0].value == 678_000


def test_fix3_currency_scale_default_baht_no_multiplier() -> None:
    """No unit marker → multiplier defaults to 1.0 (raw baht)."""
    rows = _cf_header_rows()  # includes 'หน่วย : บาท'
    rows.append(
        [None, None, "เงินสดสุทธิจากการดำเนินงาน",
         None, None, None, None, None, 12_345, None, 0, None, 0, None, 0]
    )
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-6", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    consolidated = [
        r for r in out
        if r.raw_label_th == "เงินสดสุทธิจากการดำเนินงาน"
        and r.consolidation == "consolidated"
    ]
    assert len(consolidated) == 1
    assert consolidated[0].value == 12_345


def test_fix3_currency_scale_million_baht_multiplier() -> None:
    """``(ล้านบาท)`` → multiplier 1_000_000."""
    rows: list[list[object]] = [
        [None] * 15,
        [None, "Mock Co."] + [None] * 13,
        [None, "งบกระแสเงินสด"] + [None] * 13,
        [None] * 15,
        [None] * 15,
        [None, None, None, None, None, None, None, None, None, None, None, None, None, None, "หน่วย : ล้านบาท"],
        [None, None, None, None, None, None, None, None, "งบการเงินรวม", None, None, None, "งบการเงินเฉพาะกิจการ", None, None],
        [None, None, None, None, None, None, None, None, "2568", None, "2567", None, "2568", None, "2567"],
        [None] * 15,
        [None, None, "เงินสดสุทธิจากการดำเนินงาน",
         None, None, None, None, None, 12, None, 0, None, 0, None, 0],
    ]
    xlsx = _build_xlsx_bytes({"Cash flow": rows})
    out = parse_financial_statements(
        xlsx, filing_id="MOCK-7", period="2025",
        audit_basis="audited", symbol="MOCK",
    )
    consolidated = [
        r for r in out
        if r.raw_label_th == "เงินสดสุทธิจากการดำเนินงาน"
        and r.consolidation == "consolidated"
    ]
    assert len(consolidated) == 1
    assert consolidated[0].value == 12_000_000
