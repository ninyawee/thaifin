"""FilingDiscovery — enumerate a symbol's filings on Thai SEC IDISC.

The IDISC search endpoint returns a single HTML table whose rows describe
each filing with these columns:

    ชื่อ            company name
    ประจำปี         Buddhist-calendar year (e.g. ``2568`` = 2025)
    ประเภทงบ       audit basis (``ตรวจสอบ`` audited / ``สอบทาน`` reviewed)
    ชนิดงบ          consolidation (``รวม`` consolidated / ``เดี่ยว`` company)
    งวด             period bucket (``งบปี`` annual / ``ไตรมาสที่ N`` Q-N)
    สิ้นสุดวันที่    period-end (DD/MM/YYYY in BE calendar)
    รายละเอียด     anchor with the zip URL (FILEID query param)

Two rows share the same ``FILEID`` for the consolidated and company variants
of the same filing. We collapse those into a single
:class:`FilingManifestEntry` because the zip already contains both columns
side by side; the consolidation distinction lives at the row level inside
``financial_lines``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

FS_NORM_URL = "https://market.sec.or.th/public/idisc/th/Viewmore/fs-norm"

# Header text → canonical column index. The page is in Thai and the order is
# stable across symbols, but we look up by header so a future column reorder
# breaks loudly rather than silently.
_HEADER_NAME = "ชื่อ"
_HEADER_YEAR = "ประจำปี"
_HEADER_AUDIT = "ประเภทงบ"
_HEADER_CONSOL = "ชนิดงบ"
_HEADER_PERIOD = "งวด"
_HEADER_END = "สิ้นสุดวันที่"
_HEADER_DETAIL = "รายละเอียด"

# Maps the period-bucket cell to (kind, quarter). For annuals quarter is 0.
_QUARTER_RE = re.compile(r"ไตรมาสที่\s*(\d+)")


@dataclass(frozen=True)
class FilingManifestEntry:
    """One filing in a symbol's history.

    ``filing_id`` is derived from the IDISC ``FILEID`` query parameter — it
    is the canonical primary key in ``filings.parquet``. Both consolidation
    variants share the same id because they live inside the same zip.
    """

    filing_id: str
    symbol: str
    source_url: str
    period: str  # YYYY (annual) or YYYYQq (quarterly), Gregorian
    audit_basis: str  # 'audited' | 'reviewed'
    period_end: date | None  # Gregorian; None if header value is unparsable


def _filing_id_from_url(url: str) -> str:
    """Strip the path/extension off the FILEID query param to get a stable id.

    ``dat/news/202602/0646FIN190220261747440265T.zip`` → ``0646FIN190220261747440265T``.
    """
    qs = parse_qs(urlparse(url).query)
    file_id_path = qs.get("FILEID", [""])[0]
    stem = file_id_path.rsplit("/", 1)[-1]
    return stem.rsplit(".", 1)[0]


def _be_to_ce(year: int) -> int:
    """Buddhist-Era year to Common-Era. BE - 543 = CE."""
    return year - 543


def _parse_period(year_th_text: str, period_bucket_text: str) -> str:
    """Build a canonical period token (Gregorian) from the BE year + bucket.

    Annual → ``YYYY``. Quarterly → ``YYYYQq``.
    """
    year_be = int(year_th_text.strip())
    year_ce = _be_to_ce(year_be)
    bucket = period_bucket_text.strip()
    if bucket == "งบปี":
        return f"{year_ce}"
    m = _QUARTER_RE.search(bucket)
    if m:
        return f"{year_ce}Q{m.group(1)}"
    # Unknown bucket — keep the text as a diagnostic suffix.
    return f"{year_ce}-{bucket}"


def _parse_audit_basis(text: str) -> str:
    if text.strip() == "ตรวจสอบ":
        return "audited"
    if text.strip() == "สอบทาน":
        return "reviewed"
    return text.strip()


def _parse_period_end(text: str) -> date | None:
    """``31/12/2568`` (BE) → ``date(2025, 12, 31)``. None on unparsable input."""
    s = text.strip()
    parts = s.split("/")
    if len(parts) != 3:
        return None
    try:
        d, m, y_be = (int(p) for p in parts)
    except ValueError:
        return None
    try:
        return date(_be_to_ce(y_be), m, d)
    except ValueError:
        return None


def parse_fs_norm_html(html: str, symbol: str) -> list[FilingManifestEntry]:
    """Parse the fs-norm HTML response into a deduplicated manifest.

    Two rows per filing (consolidated + company) collapse to one entry.
    Order matches the table's rendering order (most-recent first).
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    rows = table.find_all("tr")
    if not rows:
        return []

    header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
    expected = [
        _HEADER_NAME,
        _HEADER_YEAR,
        _HEADER_AUDIT,
        _HEADER_CONSOL,
        _HEADER_PERIOD,
        _HEADER_END,
        _HEADER_DETAIL,
    ]
    if header_cells[: len(expected)] != expected:
        raise ValueError(
            f"fs-norm header changed; got {header_cells!r} expected {expected!r}"
        )

    seen: dict[str, FilingManifestEntry] = {}
    symbol_upper = symbol.upper()
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        anchor = cells[6].find("a")
        if anchor is None:
            continue
        url = anchor.get("href", "")
        if not url:
            continue
        filing_id = _filing_id_from_url(url)
        if filing_id in seen:
            continue
        period = _parse_period(cells[1].get_text(strip=True), cells[4].get_text(strip=True))
        audit_basis = _parse_audit_basis(cells[2].get_text(strip=True))
        period_end = _parse_period_end(cells[5].get_text(strip=True))
        seen[filing_id] = FilingManifestEntry(
            filing_id=filing_id,
            symbol=symbol_upper,
            source_url=url,
            period=period,
            audit_basis=audit_basis,
            period_end=period_end,
        )
    return list(seen.values())


def discover_filings(
    symbol: str, *, client: httpx.Client | None = None, timeout: float = 30.0
) -> list[FilingManifestEntry]:
    """Live discovery — GET ``fs-norm`` and parse into a manifest.

    Pass ``client`` for connection reuse across many symbols.
    """
    own_client = client is None
    if own_client:
        client = httpx.Client(follow_redirects=True, timeout=timeout)
    try:
        resp = client.get(FS_NORM_URL, params={"searchSymbol": symbol})
        resp.raise_for_status()
        return parse_fs_norm_html(resp.text, symbol)
    finally:
        if own_client:
            client.close()


def filings_to_records(entries: Iterable[FilingManifestEntry]) -> list[dict]:
    """Helper for serialisation — turn entries into plain dicts."""
    return [
        {
            "filing_id": e.filing_id,
            "symbol": e.symbol,
            "source_url": e.source_url,
            "period": e.period,
            "audit_basis": e.audit_basis,
            "period_end": e.period_end.isoformat() if e.period_end else None,
        }
        for e in entries
    ]
