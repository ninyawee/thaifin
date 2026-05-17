"""Tests for the SEC IDISC letter-page symbol enumerator (slice #17)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thaifin.sources.sec_idisc.symbols import (
    Symbol,
    parse_letter_page,
    write_symbols_csv,
)

SAMPLE_DATA = Path(__file__).parent / "sample_data"
LETTER_C_HTML = SAMPLE_DATA / "letter_page_C.html"


@pytest.fixture
def letter_c_symbols() -> list[Symbol]:
    return parse_letter_page(LETTER_C_HTML.read_text(encoding="utf-8"))


def test_parses_expected_count(letter_c_symbols: list[Symbol]) -> None:
    """Letter C should yield ~61 symbols (probed 2026-05-16)."""
    assert 50 <= len(letter_c_symbols) <= 80, (
        f"unexpected count: {len(letter_c_symbols)}"
    )


def test_includes_well_known_symbols(letter_c_symbols: list[Symbol]) -> None:
    syms = {s.symbol for s in letter_c_symbols}
    for must_have in ("CPN", "CK", "CPALL"):
        assert must_have in syms, f"missing {must_have} from letter-C page"


def test_symbol_fields_are_populated(letter_c_symbols: list[Symbol]) -> None:
    """Every entry has a non-empty Thai name; market is SET, mai, or None."""
    for s in letter_c_symbols:
        assert s.symbol, "symbol must be non-empty"
        assert s.symbol.isascii() and s.symbol.replace("-", "").isalnum(), (
            f"symbol has unexpected chars: {s.symbol!r}"
        )
        assert s.name_th, f"{s.symbol}: name_th must be non-empty"
        assert s.listed_market in (None, "SET", "mai"), (
            f"{s.symbol}: unexpected market {s.listed_market!r}"
        )


def test_no_duplicate_symbols(letter_c_symbols: list[Symbol]) -> None:
    syms = [s.symbol for s in letter_c_symbols]
    assert len(syms) == len(set(syms)), "duplicate symbols on one letter page"


def test_market_distribution_reasonable(letter_c_symbols: list[Symbol]) -> None:
    """Both SET and mai entries should appear on letter C."""
    markets = [s.listed_market for s in letter_c_symbols]
    assert "SET" in markets
    assert "mai" in markets


def test_write_symbols_csv_roundtrip(tmp_path: Path) -> None:
    """write_symbols_csv produces a 3-column CSV in expected order."""
    data = [
        Symbol("PTT", "บริษัท ปตท. จำกัด (มหาชน)", "SET"),
        Symbol("ZIGA", "บริษัท ซิก้า อินโนเวชั่น จำกัด (มหาชน)", "mai"),
        Symbol("XYZ", "บริษัทตัวอย่าง", None),
    ]
    out = tmp_path / "symbols.csv"
    write_symbols_csv(data, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "symbol,name_th,listed_market"
    assert "PTT" in lines[1]
    assert "SET" in lines[1]
    # Third row's market is empty (None → empty string)
    assert lines[3].endswith(",")
