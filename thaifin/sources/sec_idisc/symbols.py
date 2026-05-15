"""Symbol enumeration via SEC IDISC letter pages.

Walks the 36 alphabetic letter pages of the Thai SEC IDISC site
(``/public/idisc/th/company/listed/{0-9,A-Z}``) and parses each per-row
table to produce the canonical (symbol, Thai name, listed market) tuple.

Empirically (probed 2026-05-16), the 36 pages return ~866 unique symbols
in ~3 s at 0.15 s polite delay. Pages ``0,1,3-7,9`` return zero symbols.
Letters ``2`` and ``8`` carry the "numeric-prefix" stocks (``2S``, ``88TH``).
"""

from __future__ import annotations

import re
import string
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

LISTED_BASE_URL = (
    "https://market.sec.or.th/public/idisc/th/company/listed"
)

LETTERS: tuple[str, ...] = tuple(string.digits) + tuple(string.ascii_uppercase)

DEFAULT_DELAY_SEC = 0.15
DEFAULT_TIMEOUT_SEC = 30.0

_SYMBOL_HREF_RE = re.compile(r"/companyprofile/listed/([A-Z0-9-]+)")
_MARKET_HREF_RE = re.compile(r"/Sector/(SET|mai)-")


@dataclass(frozen=True)
class Symbol:
    """One listed company entry from the SEC IDISC letter page.

    ``listed_market`` is ``"SET"`` or ``"mai"`` when the row carries a
    sector-ranking link (the vast majority of rows). ``None`` when the
    row has no ranking link — observed for a handful of edge-case
    delisted-but-still-indexed entries.
    """

    symbol: str
    name_th: str
    listed_market: str | None


def parse_letter_page(html: str) -> list[Symbol]:
    """Extract every symbol row from one letter page's HTML.

    Returns symbols in document order. A row is a ``<tr>`` containing
    an ``<a>`` whose href matches ``/companyprofile/listed/<SYMBOL>``.
    The Thai company name is the text of that anchor; the listed market
    is sniffed from the sector-ranking anchor in the same row.
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[Symbol] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        match = _SYMBOL_HREF_RE.search(link["href"])
        if not match:
            continue
        symbol = match.group(1)
        if symbol in seen:
            continue
        tr = link.find_parent("tr")
        if tr is None:
            continue
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue
        # Symbol cell is td[0]; Thai name is the linked text (td[1]).
        name_th = link.get_text(strip=True)
        if not name_th:
            # Fallback: second cell's full text
            name_th = cells[1].get_text(strip=True)
        market: str | None = None
        rank_link = tr.find(
            "a", href=lambda h: h and "Ranking/Listed/Sector/" in h
        )
        if rank_link:
            mm = _MARKET_HREF_RE.search(rank_link["href"])
            if mm:
                market = mm.group(1)
        seen.add(symbol)
        out.append(Symbol(symbol=symbol, name_th=name_th, listed_market=market))
    return out


def walk_listed_symbols(
    delay: float = DEFAULT_DELAY_SEC,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    client: httpx.Client | None = None,
    letters: Iterable[str] = LETTERS,
) -> list[Symbol]:
    """Walk all 36 letter pages and return a deduplicated symbol list.

    Polite by default (``0.15 s`` delay between requests). Passes through
    a caller-supplied ``httpx.Client`` for connection reuse and tests.
    Symbols are deduplicated globally (a symbol that appears under multiple
    letters — should never happen empirically — keeps its first occurrence).
    """
    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True, timeout=timeout, headers={"User-Agent": "thaifin/2.0"}
    )
    seen: set[str] = set()
    out: list[Symbol] = []
    try:
        for letter in letters:
            url = f"{LISTED_BASE_URL}/{letter}"
            resp = client.get(url)
            resp.raise_for_status()
            for sym in parse_letter_page(resp.text):
                if sym.symbol in seen:
                    continue
                seen.add(sym.symbol)
                out.append(sym)
            if delay > 0:
                time.sleep(delay)
    finally:
        if owns_client:
            client.close()
    return out


def write_symbols_csv(symbols: list[Symbol], out_path: Path) -> Path:
    """Write the symbol list to CSV with columns ``symbol,name_th,listed_market``.

    No third-party CSV writer — stdlib ``csv`` is enough and avoids tying
    this module to pandas.
    """
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["symbol", "name_th", "listed_market"])
        for s in symbols:
            writer.writerow([s.symbol, s.name_th, s.listed_market or ""])
    return out_path
