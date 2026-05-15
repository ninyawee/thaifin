"""Parse ``AUDITOR_REPORT.DOC[X]`` into one structured row per filing.

The Thai SEC IDISC ships a Word document for each filing's auditor report.
Layout is mostly free-form prose, but a few keywords are reliable:

- The opinion-type sentence appears in or near the ``ความเห็น`` section.
- The going-concern emphasis is announced with the phrase
  ``การดำเนินงานต่อเนื่อง`` *outside* the standard responsibility-of-management
  paragraphs (which always mention it). We approximate "outside" by
  requiring the phrase to appear in a paragraph whose heading is an
  emphasis-of-matter / ``เรื่องอื่น`` / ``ข้อสังเกต`` band, which is the
  standard placement for a real GC modification.
- The signature block always lives at the bottom of the document. We grab
  the auditor firm via a known-firm lookup (EY / KPMG / PwC / Deloitte +
  Thai equivalents) and the signing date by Thai-date regex.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import docx

from thaifin.parsers._convert import ensure_docx

# --- Opinion classification (most-specific keywords first) ------------------
#
# Order matters: the more specific qualifiers must match before the
# unqualified default. The auditor often paraphrases or *negates* the
# modifier phrases inside boilerplate ("the auditor did NOT issue a
# qualified opinion") so plain substring matches would flip every clean
# filing. ``_NEGATION_TOKENS`` filters those out via a sliding-window
# lookback in :func:`_classify_opinion`.

_OPINION_RULES: list[tuple[str, str]] = [
    ("ไม่แสดงความเห็น", "disclaimer"),
    ("แสดงความเห็นในทางตรงข้าม", "adverse"),
    ("แสดงความเห็นอย่างมีเงื่อนไข", "qualified"),
]

# Modern reports use ``มิได้`` / ``ไม่ได้`` / ``ไม่``-prefix to disclaim
# a modification. Any phrase preceded by one of these in the immediately
# preceding ~20-char window is *not* the actual opinion.
_NEGATION_TOKENS = ("มิได้", "ไม่ได้")
_NEGATION_LOOKBACK = 20

# Going-concern phrase (case-sensitive Thai). The phrase appears in *every*
# auditor report inside the standard "ความรับผิดชอบของผู้บริหาร…ดำเนินงาน
# ต่อเนื่อง" boilerplate, so we can't just substring-match. Instead we look
# for it inside paragraphs whose nearest preceding heading marks an
# emphasis-of-matter band. ``เรื่องอื่น``/``ข้อสังเกต`` are also valid placement.
_GC_PHRASE = "การดำเนินงานต่อเนื่อง"
_EOM_HEADING_TOKENS = (
    "เน้นข้อมูลและเหตุการณ์",  # standard EOM heading
    "การดำเนินงานต่อเนื่อง",  # heading-as-phrase: explicit GC heading
)

# Boilerplate paragraphs in which the GC phrase is a false positive — these
# are always present in modern auditor reports.
_GC_BOILERPLATE_TOKENS = (
    "ความรับผิดชอบของผู้บริหาร",
    "ความรับผิดชอบของผู้สอบบัญชี",
    "การจัดทำงบการเงิน",
    "ความรับผิดชอบในการประเมิน",
    "เกณฑ์การบัญชีสำหรับกิจการที่ดำเนินงานต่อเนื่อง",
    # SAO equivalents (older PTT filings audited by State Audit Office)
    "สำนักงานการตรวจเงินแผ่นดินใช้",
    "สำนักงานการตรวจเงินแผ่นดินสรุป",
    "สรุปเกี่ยวกับความเหมาะสม",
    "ผู้บริหารใช้เกณฑ์",
)

# Known auditor firms — search the signature band (last ~12 paragraphs) for
# any of these tokens. Add new firms here as they appear in real filings.
# State Audit Office (สตง./SAO) audits state-owned enterprises like PTT
# in many years and is treated as a distinct "firm" for provenance.
_AUDITOR_FIRMS: list[tuple[str, str]] = [
    ("อีวาย", "EY"),
    ("ดีลอยท์ ทู้ช โธมัทสุ", "Deloitte"),
    ("ดีลอยท์", "Deloitte"),
    ("เคพีเอ็มจี", "KPMG"),
    ("ไพร้ซวอเตอร์เฮาส์", "PwC"),
    ("สำนักงานการตรวจเงินแผ่นดิน", "SAO"),  # Thai State Audit Office
    ("EY", "EY"),
    ("Ernst & Young", "EY"),
    ("KPMG", "KPMG"),
    ("PwC", "PwC"),
    ("PricewaterhouseCoopers", "PwC"),
    ("Deloitte", "Deloitte"),
    ("BDO", "BDO"),
    ("แกรนท์ ธอร์นตัน", "Grant Thornton"),
    ("Grant Thornton", "Grant Thornton"),
    ("Mazars", "Mazars"),
]

# Thai-date regex: ``19 กุมภาพันธ์ 2569`` → (19, 2, 2569).
_THAI_MONTHS = {
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}
_DATE_RE = re.compile(
    r"(\d{1,2})\s*("
    + "|".join(_THAI_MONTHS.keys())
    + r")\s*(\d{4})"
)


@dataclass(frozen=True)
class AuditorReportRow:
    """One row in ``auditor_reports.parquet``.

    Mirrors the schema in ``notes/cicd-design.md`` plus a ``filing_id`` PK.
    ``raw_text_md`` is the entire document collapsed to markdown — the
    structured fields are best-effort heuristics extracted from it.
    """

    filing_id: str
    symbol: str
    period: str
    audit_basis: str
    opinion_type: str
    going_concern_emphasis: bool
    auditor_firm: str | None
    signing_date: date | None
    signing_partner: str | None
    raw_text_md: str


# --- Helpers ----------------------------------------------------------------


def _document_to_markdown(doc) -> str:
    """Collapse a python-docx ``Document`` to markdown.

    Headings (style starts with ``Heading``) become ``#`` lines; other
    paragraphs are written verbatim with blank-line separation. Tables are
    rendered as pipe-tables. The output is stable for diffing across
    pipeline runs.
    """
    out: list[str] = []
    body_iter = list(doc.paragraphs)
    for para in body_iter:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if style.startswith("heading 1") or style.startswith("title"):
            out.append(f"# {text}")
        elif style.startswith("heading 2"):
            out.append(f"## {text}")
        elif style.startswith("heading 3"):
            out.append(f"### {text}")
        else:
            out.append(text)
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [c.text.replace("\n", " ").strip() for c in row.cells]
            out.append("| " + " | ".join(cells) + " |")
        out.append("")
    return "\n\n".join(out)


_REVIEW_BOILERPLATE_FOLLOWUPS = (
    "ต่อข้อมูลทางการเงินระหว่างกาล",
    "ต่องบการเงินระหว่างกาล",
)

# Title markers that distinguish review (ISRE 2410) reports from full audits.
# Reviews use NEGATIVE-form language ("nothing has come to our attention...")
# while audits use POSITIVE-form ("the statements present fairly..."), so the
# qualifier-detection logic differs.
_REVIEW_TITLE_TOKENS = (
    "รายงานการสอบทาน",
    "Independent Auditor's Review Report",
)
_AUDIT_TITLE_TOKENS = (
    "รายงานของผู้สอบบัญชี",
    "Independent Auditor's Report",
)

# Qualifier markers used inside review-form reports. Presence anywhere in
# the document body indicates the review is NOT clean.
_REVIEW_QUALIFIER_RULES: list[tuple[str, str]] = [
    ("ไม่สามารถแสดงความเห็น", "disclaimer"),
    ("ไม่ถูกต้อง", "adverse"),
    ("ยกเว้น", "qualified"),
]


def _is_review_form(text: str) -> bool:
    """True if the report's title or opening band marks an ISRE 2410 review."""
    head = text[:600]
    return any(tok in head for tok in _REVIEW_TITLE_TOKENS) and not any(
        tok in head for tok in _AUDIT_TITLE_TOKENS
    )


def _classify_opinion(text: str) -> str:
    """Return one of ``unqualified|qualified|adverse|disclaimer``.

    Two paths:

    - **Audit form** (annual filings, positive-form language): scan for
      modifier phrases (``แสดงความเห็นอย่างมีเงื่อนไข``,
      ``แสดงความเห็นในทางตรงข้าม``, ``ไม่แสดงความเห็น``) with two guards:
        1. ``มิได้`` / ``ไม่ได้`` in the ~20-char window before → negation
           boilerplate denying the modification.
        2. ``ต่อข้อมูลทางการเงินระหว่างกาล`` in the ~50-char window after →
           SAO review-engagement boilerplate that mentions the disclaimer
           phrase only to explain a review can't issue an opinion.
      Default = ``unqualified``.

    - **Review form** (Q1/Q2/Q3 filings under ISRE 2410, negative-form
      language ``ไม่พบสิ่งที่เป็นเหตุให้เชื่อว่า…``): scan the body for
      qualifier markers and classify by the strongest one. If none fire,
      the review is unqualified.
    """
    if _is_review_form(text):
        for needle, opinion in _REVIEW_QUALIFIER_RULES:
            if needle in text:
                return opinion
        return "unqualified"

    for needle, opinion in _OPINION_RULES:
        idx = text.find(needle)
        while idx != -1:
            window_before = text[max(0, idx - _NEGATION_LOOKBACK) : idx]
            window_after = text[idx + len(needle) : idx + len(needle) + 50]
            negated = any(neg in window_before for neg in _NEGATION_TOKENS)
            review_boilerplate = any(
                tok in window_after for tok in _REVIEW_BOILERPLATE_FOLLOWUPS
            )
            if not negated and not review_boilerplate:
                return opinion
            idx = text.find(needle, idx + len(needle))
    return "unqualified"


def _detect_going_concern(paragraphs: list[str]) -> bool:
    """True iff the GC phrase appears outside the standard boilerplate.

    A GC modification is rare; the standard reports mention the phrase
    several times inside descriptions of management/auditor responsibilities.
    We scan paragraphs and require both:
      1. the phrase is present, AND
      2. the same paragraph (or its heading) explicitly flags an
         emphasis-of-matter / dedicated GC band.
    """
    for para in paragraphs:
        if _GC_PHRASE not in para:
            continue
        # Skip the boilerplate responsibility paragraphs.
        if any(token in para for token in _GC_BOILERPLATE_TOKENS):
            continue
        # If the paragraph itself is an EOM heading, count it.
        if any(token in para for token in _EOM_HEADING_TOKENS):
            return True
        # If the paragraph is short and stands alone as a heading-style
        # callout (≤80 chars), count it.
        if len(para.strip()) <= 80:
            return True
    return False


def _detect_auditor_firm(paragraphs: list[str]) -> str | None:
    """Scan the last ~12 paragraphs (signature band) for a known firm token."""
    tail = "\n".join(paragraphs[-12:])
    for token, canonical in _AUDITOR_FIRMS:
        if token in tail:
            return canonical
    # Fall back: scan the entire document.
    full = "\n".join(paragraphs)
    for token, canonical in _AUDITOR_FIRMS:
        if token in full:
            return canonical
    return None


def _be_to_ce(year: int) -> int:
    return year - 543


def _detect_signing_date(paragraphs: list[str]) -> date | None:
    """Pick the maximum Thai-date from the bottom-third of the document.

    The signing block always sits at the bottom and typically holds one
    isolated date. Older SAO-style reports include several intermediate
    dates (cited authorities, court orders) so we constrain the search
    band and pick the largest valid date — the signing date is always the
    most-recent one in that band.
    """
    if not paragraphs:
        return None
    cutoff = max(0, int(len(paragraphs) * 0.6))
    candidates: list[date] = []
    for para in paragraphs[cutoff:]:
        for m in _DATE_RE.finditer(para):
            day, month_th, year_th = m.group(1), m.group(2), m.group(3)
            year_be = int(year_th)
            year_ce = _be_to_ce(year_be) if year_be > 2400 else year_be
            try:
                candidates.append(
                    date(year_ce, _THAI_MONTHS[month_th], int(day))
                )
            except ValueError:
                continue
    if not candidates:
        return None
    return max(candidates)


def _detect_signing_partner(paragraphs: list[str]) -> str | None:
    """Best-effort: name on a short line directly above
    ``ผู้สอบบัญชีรับอนุญาต`` in the signature band.
    """
    tail = paragraphs[-12:]
    for i, para in enumerate(tail):
        if "ผู้สอบบัญชีรับอนุญาต" in para and i > 0:
            candidate = tail[i - 1].strip()
            # Reject paragraphs that are sentences (have spaces & length).
            if 4 <= len(candidate) <= 80 and "เลขทะเบียน" not in candidate:
                return candidate
    return None


# --- Public API -------------------------------------------------------------


def parse_auditor_report(
    data: bytes,
    *,
    filing_id: str,
    symbol: str,
    period: str,
    audit_basis: str,
) -> AuditorReportRow:
    """Parse one ``AUDITOR_REPORT.DOC[X]`` payload into a structured row."""
    with TemporaryDirectory(prefix="thaifin-aud-") as tmp:
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", filing_id) or "auditor"
        docx_path = ensure_docx(data, Path(tmp), stem=safe_stem)
        doc = docx.Document(str(docx_path))
        raw_md = _document_to_markdown(doc)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)
    return AuditorReportRow(
        filing_id=filing_id,
        symbol=symbol,
        period=period,
        audit_basis=audit_basis,
        opinion_type=_classify_opinion(full_text),
        going_concern_emphasis=_detect_going_concern(paragraphs),
        auditor_firm=_detect_auditor_firm(paragraphs),
        signing_date=_detect_signing_date(paragraphs),
        signing_partner=_detect_signing_partner(paragraphs),
        raw_text_md=raw_md,
    )


def row_to_record(row: AuditorReportRow) -> dict:
    return {
        "filing_id": row.filing_id,
        "symbol": row.symbol,
        "period": row.period,
        "audit_basis": row.audit_basis,
        "opinion_type": row.opinion_type,
        "going_concern_emphasis": row.going_concern_emphasis,
        "auditor_firm": row.auditor_firm,
        "signing_date": row.signing_date.isoformat() if row.signing_date else None,
        "signing_partner": row.signing_partner,
        "raw_text_md": row.raw_text_md,
    }


__all__ = [
    "AuditorReportRow",
    "parse_auditor_report",
    "row_to_record",
]
