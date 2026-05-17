"""Tests for ``thaifin.sources.sec_idisc.discovery``.

Fixture is a snapshot of the live ``fs-norm?searchSymbol=PTT`` page
(``tests/sample_data/fs_norm_PTT.html``) — no network IO.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thaifin.sources.sec_idisc.discovery import (
    FilingManifestEntry,
    parse_fs_norm_html,
)

FIXTURE_DIR = Path(__file__).parent / "sample_data"


@pytest.fixture
def ptt_html() -> str:
    return (FIXTURE_DIR / "fs_norm_PTT.html").read_text()


def test_parses_full_manifest(ptt_html: str) -> None:
    entries = parse_fs_norm_html(ptt_html, "PTT")
    # PTT has 8 filings/year × 25 years − 6 missing 2001 entries ≈ 97.
    # Two HTML rows (consolidated + company) collapse to one entry.
    assert 80 <= len(entries) <= 110, f"expected ~97 entries, got {len(entries)}"


def test_first_entry_is_most_recent(ptt_html: str) -> None:
    entries = parse_fs_norm_html(ptt_html, "PTT")
    head = entries[0]
    assert head.symbol == "PTT"
    assert head.audit_basis == "audited"
    assert head.period == "2025"
    assert head.source_url.startswith(
        "https://market.sec.or.th/public/idisc/Download?FILEID="
    )


def test_filing_id_dedupes_consol_and_company(ptt_html: str) -> None:
    """Same FILEID across consolidation rows collapses to one entry."""
    entries = parse_fs_norm_html(ptt_html, "PTT")
    seen = {e.filing_id for e in entries}
    assert len(seen) == len(entries), "filing_ids should be unique"


def test_quarterly_period_format(ptt_html: str) -> None:
    entries = parse_fs_norm_html(ptt_html, "PTT")
    quarterly = [e for e in entries if "Q" in e.period]
    assert quarterly, "expected at least one quarterly filing"
    sample = quarterly[0]
    # YYYYQq pattern with Gregorian year.
    assert sample.period[4] == "Q"
    year = int(sample.period[:4])
    assert 2000 <= year <= 2100
    assert sample.audit_basis == "reviewed"


def test_period_end_is_gregorian(ptt_html: str) -> None:
    entries = parse_fs_norm_html(ptt_html, "PTT")
    head = entries[0]
    assert head.period_end is not None
    assert head.period_end.year == 2025
    assert head.period_end.month == 12
    assert head.period_end.day == 31


def test_entries_are_immutable_dataclass() -> None:
    e = FilingManifestEntry(
        filing_id="ID",
        symbol="PTT",
        source_url="x",
        period="2025",
        audit_basis="audited",
        period_end=None,
    )
    with pytest.raises(Exception):
        e.symbol = "X"  # type: ignore[misc]


def test_parses_to_records_serialisation(ptt_html: str) -> None:
    from thaifin.sources.sec_idisc.discovery import filings_to_records

    entries = parse_fs_norm_html(ptt_html, "PTT")
    records = filings_to_records(entries)
    sample = records[0]
    assert set(sample.keys()) == {
        "filing_id",
        "symbol",
        "source_url",
        "period",
        "audit_basis",
        "period_end",
    }
    assert sample["period_end"] == "2025-12-31"
