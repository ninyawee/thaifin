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

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from thaifin.parsers._convert import ensure_xlsx

logger = logging.getLogger(__name__)

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

# Hidden / vendor-internal sheets to skip outright. Covers the SAP BI export
# ``_com.sap.ip.bi.xl.hiddensheet`` (AOT 2020+), DataSnipper artifact sheets
# ``DS_INTERNAL_*`` (CPALL 2026Q1), and any other ``_``-prefixed scratch sheet.
SHEET_NAME_BLACKLIST_RE = re.compile(r"^(_|DS_INTERNAL)")

# Line-wrap detection (Fix 1). When a long financial-statement label doesn't
# fit one print row, Excel splits it across two cells: the first cell holds
# the head of the phrase (with empty value cells), the next cell holds the
# tail (with the value cells populated). The tail almost always indents with
# leading whitespace OR starts with a Thai grammatical particle that can't
# begin a fresh sentence. Without merging, the parser emits the tail as a
# phantom orphan label that never maps to a canonical concept (PTT FY2025
# cash-flow row 39 ``และหนี้สินดำเนินงาน`` is the textbook case).
_THAI_CONTINUATION_PARTICLES = (
    "และ",     # "and"
    "หรือ",    # "or"
    "ที่",     # relative pronoun "that/which"
    "จาก",     # "from"
    "ของ",     # "of"
    "ใน",      # "in"
    "ต่อ",     # "per/to"
    "ภาษี",    # "tax" — common tail in cash-flow-line continuations
    "มูลค่า",  # "value"
    "เพื่อ",   # "for"
    "ตาม",     # "according to"
    "โดย",     # "by"
    "กับ",     # "with"
)


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


def _label_at(ws: Worksheet, row: int, label_cols: list[int]) -> tuple[str, str] | None:
    """Return ``(stripped, raw)`` for the first non-empty label across ``label_cols``.

    The raw form preserves leading whitespace, which is the strongest signal
    that a row is a line-wrap continuation of the row above.
    """
    for col in label_cols:
        v = ws.cell(row=row, column=col).value
        if isinstance(v, str) and v.strip():
            return v.strip(), v
    return None


def _looks_like_continuation(stripped: str, raw: str) -> bool:
    """Return True if ``(stripped, raw)`` looks like a line-wrap tail.

    Two orthogonal signals — either is enough:

    1. Raw label starts with whitespace (Excel renders wrapped text
       indented; this is the strongest signal observed in PTT filings).
    2. Stripped label starts with a Thai grammatical particle that can't
       grammatically begin a fresh line item (และ, ที่, จาก, …).

    A short-length heuristic was considered but rejected — legitimate short
    line items (``เงินกู้ยืมระยะยาว``, ``กำไรขั้นต้น``) collide with the
    common section-header-then-first-item pattern in BS sheets.
    """
    if raw != raw.lstrip():
        return True
    for particle in _THAI_CONTINUATION_PARTICLES:
        if stripped.startswith(particle):
            return True
    return False


# --- Sheet extraction ------------------------------------------------------


@dataclass(frozen=True)
class _RawRow:
    """Pre-merge view of one worksheet row."""

    row_num: int
    label_stripped: str
    label_raw: str
    cons_value: float | None
    comp_value: float | None


def _collect_rows(
    ws: Worksheet,
    label_cols: list[int],
    consolidated_col: int | None,
    company_col: int | None,
    multiplier: float,
) -> list[_RawRow]:
    """First pass: gather every labelled row with its scaled values."""
    out: list[_RawRow] = []
    for row in range(1, ws.max_row + 1):
        label = _label_at(ws, row, label_cols)
        if label is None:
            continue
        stripped, raw = label
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
        cons = cons_raw * multiplier if cons_raw is not None else None
        comp = comp_raw * multiplier if comp_raw is not None else None
        out.append(_RawRow(row, stripped, raw, cons, comp))
    return out


def _merge_line_wraps(rows: list[_RawRow]) -> list[_RawRow]:
    """Fold tail rows that look like line-wrap continuations into their head.

    Value-continuity guardrail: only fold when the head row's value cells
    are empty AND the tail row's value cells are non-empty. If both have
    values they're separate line items; if both are empty neither survives
    the value-filter downstream so the merge would be a no-op anyway.
    """
    merged: list[_RawRow] = []
    skip_next = False
    for i, row in enumerate(rows):
        if skip_next:
            skip_next = False
            continue
        head_has_value = row.cons_value is not None or row.comp_value is not None
        if head_has_value or i + 1 >= len(rows):
            merged.append(row)
            continue
        tail = rows[i + 1]
        tail_has_value = tail.cons_value is not None or tail.comp_value is not None
        if not tail_has_value:
            merged.append(row)
            continue
        if not _looks_like_continuation(tail.label_stripped, tail.label_raw):
            merged.append(row)
            continue
        combined_label = f"{row.label_stripped} {tail.label_stripped}"
        merged.append(
            _RawRow(
                row_num=row.row_num,
                label_stripped=combined_label,
                label_raw=combined_label,
                cons_value=tail.cons_value,
                comp_value=tail.comp_value,
            )
        )
        skip_next = True
    return merged


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

    A line-wrap pre-pass folds two-row labels back into a single row before
    emission — see :func:`_merge_line_wraps`.
    """
    consolidated_col, company_col = _find_section_columns(ws)
    multiplier = _detect_unit_multiplier(ws)

    label_col_primary = _guess_label_column(ws)
    # Allow the label to live one column to the right (sub-section indent).
    label_cols = [label_col_primary, label_col_primary + 1]

    raw_rows = _collect_rows(
        ws, label_cols, consolidated_col, company_col, multiplier
    )
    rows = _merge_line_wraps(raw_rows)

    out: list[FinancialLineRow] = []
    seen_labels: set[str] = set()
    for r in rows:
        if r.cons_value is None and r.comp_value is None:
            continue
        # Deduplicate within the sheet — labels can recur (e.g. note
        # references) but only the first numeric occurrence is canonical.
        if r.label_stripped in seen_labels:
            continue
        seen_labels.add(r.label_stripped)
        if r.cons_value is not None:
            out.append(
                FinancialLineRow(
                    statement=statement,
                    raw_label_th=r.label_stripped,
                    value=r.cons_value,
                    audit_basis=audit_basis,
                    consolidation="consolidated",
                    filing_id=filing_id,
                    period=period,
                    symbol=symbol,
                )
            )
        if r.comp_value is not None:
            out.append(
                FinancialLineRow(
                    statement=statement,
                    raw_label_th=r.label_stripped,
                    value=r.comp_value,
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
            if SHEET_NAME_BLACKLIST_RE.match(sheet_name):
                logger.debug(
                    "skip-hidden-sheet filing=%s sheet=%s",
                    filing_id,
                    sheet_name,
                )
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
