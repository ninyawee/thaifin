"""Parsers for the three documents inside a Thai SEC IDISC filing zip.

- :mod:`thaifin.parsers.financial_statements` — XLS/XLSX → tagged long rows.
- :mod:`thaifin.parsers.auditor_report`       — DOC/DOCX → structured row.
- :mod:`thaifin.parsers.notes`                — DOC/DOCX → markdown blob.

All three share the magic-byte sniff in :mod:`thaifin.parsers._convert`:
OOXML is fed straight into the python library; legacy CFB documents are
routed through ``libreoffice --headless --convert-to ...``.
"""

from thaifin.parsers.auditor_report import (
    AuditorReportRow,
    parse_auditor_report,
)
from thaifin.parsers.financial_statements import (
    FinancialLineRow,
    parse_financial_statements,
)
from thaifin.parsers.notes import NotesRow, parse_notes

__all__ = [
    "AuditorReportRow",
    "FinancialLineRow",
    "NotesRow",
    "parse_auditor_report",
    "parse_financial_statements",
    "parse_notes",
]
