"""Parse ``FINANCIAL_STATEMENTS.XLS[X]`` into tagged-long financial-line rows.

Sheet-name dispatch is regex-based. The modern PTT format (2025-onwards)
uses the eight-sheet layout below; older filings vary considerably and are
treated as best-effort. Filings whose layout can't be classified are
returned as zero rows by :func:`parse_financial_statements` — the caller
should track them as ``unsupported_format_count``.

Sheet → statement mapping (regex against the trimmed sheet name)::

    BS-Asset / BS-Liability / BS-Equity      → BS
    PL_Accum / OCI_Accum / PL_Q / OCI_Q      → IS
    EQ Change*                               → EQ
    Cash flow / กระแสเงินสด                  → CF

Mid-era variants observed in PTT filings are also matched::

    BS-Asset Consol / BS-Lai Consol / ...    → BS
    BS-Asset Separat / BS-Lai Separate / ... → BS
    กำไรขาดทุน Accum                         → IS
    OCI Accum                                → IS
    งบกระแสเงินสด                            → CF

Per-sheet column layout discovery
---------------------------------

Each sheet has at most two ``งบการเงินรวม`` / ``งบการเงินเฉพาะกิจการ``
section headers in the page-header band (typically rows 5–8). We treat the
section-header column as the *current-period* value column for that
consolidation mode. The label column is sniffed as the leftmost column with
a non-empty Thai string in the data band.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from thaifin.parsers._convert import ensure_xlsx

# --- Sheet → statement classification ---------------------------------------

# Order matters: more specific patterns first. Each tuple is (regex, statement).
_SHEET_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^EQ\s*Change", re.IGNORECASE), "EQ"),
    (re.compile(r"^BS[-\s]?Asset", re.IGNORECASE), "BS"),
    (re.compile(r"^BS[-\s]?Lai", re.IGNORECASE), "BS"),
    (re.compile(r"^BS[-\s]?Lia", re.IGNORECASE), "BS"),
    (re.compile(r"^BS[-\s]?Equity", re.IGNORECASE), "BS"),
    (re.compile(r"^PL[_\s]?(Accum|Q)", re.IGNORECASE), "IS"),
    (re.compile(r"^OCI[_\s]?(Accum|Q)", re.IGNORECASE), "IS"),
    (re.compile(r"กำไรขาดทุน"), "IS"),
    (re.compile(r"^Cash\s*flow", re.IGNORECASE), "CF"),
    (re.compile(r"กระแสเงินสด"), "CF"),
    # Legacy BS sheet names — pre-2010 filings used "งบดุล" before TFRS
    # adopted "งบแสดงฐานะการเงิน" / "งบฐานะการเงิน".
    (re.compile(r"^(งบ)?(ดุล|แสดงฐานะการเงิน|ฐานะการเงิน)"), "BS"),
]

# Headers that mark the consolidated / company section bands.
_CONSOLIDATED_HEADERS = ("งบการเงินรวม", "ข้อมูลทางการเงินรวม")
_COMPANY_HEADERS = ("งบการเงินเฉพาะกิจการ", "ข้อมูลทางการเงินเฉพาะกิจการ")

# Column scanning bounds — sheet headers always sit in the first 12 rows.
_HEADER_ROW_LIMIT = 12

# Unit-of-currency markers. Quarterly filings often use thousands-of-baht;
# annuals (and PTT in particular) typically use raw baht. Without per-sheet
# unit detection a CPALL Q1 figure ends up 1000× too small alongside a
# CPALL annual figure. Order matters: longer phrases first so "ล้านบาท"
# matches before "บาท".
_UNIT_MARKERS: list[tuple[str, float]] = [
    ("ล้านบาท", 1_000_000.0),
    ("พันบาท", 1_000.0),
    ("บาท", 1.0),
]

# Hidden / vendor-internal sheets to skip outright.
_HIDDEN_SHEET_PREFIXES = ("_", "DS_INTERNAL", "_com.sap")


def classify_sheet(name: str) -> str | None:
    """Return ``'BS' | 'IS' | 'CF' | 'EQ'`` or None if unknown."""
    s = name.strip()
    for pattern, statement in _SHEET_RULES:
        if pattern.search(s):
            return statement
    return None


@dataclass(frozen=True)
class FinancialLineRow:
    """One ``(filing × raw-label × consolidation × period)`` row.

    ``concept`` is always None at this stage — the ConceptMapper fills it in
    later. ``raw_label_th`` is the verbatim Thai cell value.
    """

    statement: str
    raw_label_th: str
    value: float
    audit_basis: str
    consolidation: str
    filing_id: str
    period: str
    symbol: str


# --- Per-sheet column discovery --------------------------------------------


def _detect_unit_multiplier(ws: Worksheet) -> float:
    """Scan the page-header band for a unit-of-currency marker.

    Returns the multiplier to apply to every numeric cell on the sheet.
    Defaults to 1.0 (raw baht) when no marker is found.
    """
    for row in range(1, min(_HEADER_ROW_LIMIT, ws.max_row) + 1):
        for col in range(1, ws.max_column + 1):
            v = ws.cell(row=row, column=col).value
            if not isinstance(v, str):
                continue
            text = v.strip()
            for marker, multiplier in _UNIT_MARKERS:
                if marker in text:
                    return multiplier
    return 1.0


def _find_section_columns(ws: Worksheet) -> tuple[int | None, int | None]:
    """Locate the column containing ``งบการเงินรวม`` / ``งบการเงินเฉพาะกิจการ``.

    Returns ``(consolidated_col, company_col)``; either may be None.
    """
    consolidated_col: int | None = None
    company_col: int | None = None
    for row in range(1, min(_HEADER_ROW_LIMIT, ws.max_row) + 1):
        for col in range(1, ws.max_column + 1):
            v = ws.cell(row=row, column=col).value
            if not isinstance(v, str):
                continue
            text = v.strip()
            if consolidated_col is None and any(h in text for h in _CONSOLIDATED_HEADERS):
                consolidated_col = col
            if company_col is None and any(h in text for h in _COMPANY_HEADERS):
                company_col = col
    return consolidated_col, company_col


def _guess_label_column(ws: Worksheet) -> int:
    """Return the leftmost column that holds Thai labels in the data band.

    Strategy: scan rows 10–40, pick the lowest column index that contains at
    least three non-numeric Thai strings.
    """
    candidate_counts: dict[int, int] = {}
    end = min(40, ws.max_row) + 1
    for row in range(10, end):
        for col in (1, 2, 3, 4):
            if col > ws.max_column:
                continue
            v = ws.cell(row=row, column=col).value
            if isinstance(v, str) and v.strip() and not v.strip().isdigit():
                candidate_counts[col] = candidate_counts.get(col, 0) + 1
    for col in (2, 3, 1, 4):
        if candidate_counts.get(col, 0) >= 3:
            return col
    return 2  # safe default for the modern PTT layout


def _data_row_value(ws: Worksheet, row: int, col: int) -> float | None:
    """Return ``ws.cell(row, col)`` as a float if it's numeric, else None.

    Empty strings, whitespace-only strings and ``-`` placeholders → None.
    """
    v = ws.cell(row=row, column=col).value
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s or s == "-":
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _label_at(ws: Worksheet, row: int, label_cols: list[int]) -> str | None:
    """Return the first non-empty Thai label found across ``label_cols``."""
    for col in label_cols:
        v = ws.cell(row=row, column=col).value
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


# --- Sheet extraction ------------------------------------------------------


def _extract_sheet(
    ws: Worksheet,
    *,
    statement: str,
    filing_id: str,
    period: str,
    audit_basis: str,
    symbol: str,
) -> list[FinancialLineRow]:
    """Pull all ``(label, value)`` pairs from one sheet, both consolidations.

    Each labelled data row produces up to two rows in the output (one per
    populated consolidation column). Prior-year columns inside the same
    filing are intentionally dropped because the prior filing's own
    current-year column carries the canonical value.
    """
    consolidated_col, company_col = _find_section_columns(ws)
    multiplier = _detect_unit_multiplier(ws)

    label_col_primary = _guess_label_column(ws)
    # Allow the label to live one column to the right (sub-section indent).
    label_cols = [label_col_primary, label_col_primary + 1]

    out: list[FinancialLineRow] = []
    seen_labels: set[str] = set()
    for row in range(1, ws.max_row + 1):
        label = _label_at(ws, row, label_cols)
        if label is None:
            continue
        cons_raw = (
            _data_row_value(ws, row, consolidated_col)
            if consolidated_col is not None
            else None
        )
        comp_raw = (
            _data_row_value(ws, row, company_col)
            if company_col is not None
            else None
        )
        cons_value = cons_raw * multiplier if cons_raw is not None else None
        comp_value = comp_raw * multiplier if comp_raw is not None else None
        if cons_value is None and comp_value is None:
            continue
        # Deduplicate within the sheet — labels can recur (e.g. note
        # references) but only the first numeric occurrence is canonical.
        if label in seen_labels:
            continue
        seen_labels.add(label)
        if cons_value is not None:
            out.append(
                FinancialLineRow(
                    statement=statement,
                    raw_label_th=label,
                    value=cons_value,
                    audit_basis=audit_basis,
                    consolidation="consolidated",
                    filing_id=filing_id,
                    period=period,
                    symbol=symbol,
                )
            )
        if comp_value is not None:
            out.append(
                FinancialLineRow(
                    statement=statement,
                    raw_label_th=label,
                    value=comp_value,
                    audit_basis=audit_basis,
                    consolidation="company",
                    filing_id=filing_id,
                    period=period,
                    symbol=symbol,
                )
            )
    return out


def parse_financial_statements(
    data: bytes,
    *,
    filing_id: str,
    period: str,
    audit_basis: str,
    symbol: str,
) -> list[FinancialLineRow]:
    """Parse one ``FINANCIAL_STATEMENTS.XLS[X]`` payload into tagged rows.

    ``data`` is the raw bytes (we sniff magic bytes internally and delegate
    to libreoffice for legacy CFB inputs). Returns an empty list if no
    sheet matches a known statement pattern — caller treats that as
    ``unsupported_format``.
    """
    with TemporaryDirectory(prefix="thaifin-fs-") as tmp:
        # Stem must be filesystem-safe; strip slashes from the filing_id.
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", filing_id) or "filing"
        xlsx_path = ensure_xlsx(data, Path(tmp), stem=safe_stem)
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=False)

        rows: list[FinancialLineRow] = []
        for sheet_name in wb.sheetnames:
            # Skip vendor / hidden / DataSnipper / SAP-export sheets.
            if any(sheet_name.startswith(p) for p in _HIDDEN_SHEET_PREFIXES):
                continue
            statement = classify_sheet(sheet_name)
            if statement is None:
                continue
            ws = wb[sheet_name]
            rows.extend(
                _extract_sheet(
                    ws,
                    statement=statement,
                    filing_id=filing_id,
                    period=period,
                    audit_basis=audit_basis,
                    symbol=symbol,
                )
            )
        return rows


def rows_to_records(rows: Iterable[FinancialLineRow]) -> list[dict]:
    """Plain-dict serialiser for parquet writers."""
    return [
        {
            "symbol": r.symbol,
            "period": r.period,
            "statement": r.statement,
            "concept": None,
            "raw_label_th": r.raw_label_th,
            "value": r.value,
            "audit_basis": r.audit_basis,
            "consolidation": r.consolidation,
            "filing_id": r.filing_id,
        }
        for r in rows
    ]


__all__ = [
    "FinancialLineRow",
    "classify_sheet",
    "parse_financial_statements",
    "rows_to_records",
]
