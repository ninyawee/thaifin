"""Discover all SET/mai-listed symbols from SEC IDISC and write data/symbols.csv.

Usage::

    uv run python scripts/discover_symbols.py
    uv run python scripts/discover_symbols.py --out /tmp/sym.csv --delay 0.2

Empirical: ~866 symbols, ~3 s wall-clock at 0.15 s polite delay.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from thaifin.sources.sec_idisc.symbols import (
    DEFAULT_DELAY_SEC,
    walk_listed_symbols,
    write_symbols_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/symbols.csv"),
        help="Where to write the symbols CSV (default: data/symbols.csv)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SEC,
        help=f"Polite delay between letter-page fetches (default {DEFAULT_DELAY_SEC}s)",
    )
    args = parser.parse_args()

    started = time.monotonic()
    symbols = walk_listed_symbols(delay=args.delay)
    elapsed = time.monotonic() - started

    write_symbols_csv(symbols, args.out)
    print(
        f"Discovered {len(symbols)} symbols in {elapsed:.1f}s -> {args.out}",
        file=sys.stderr,
    )
    by_market: dict[str, int] = {}
    for s in symbols:
        by_market[s.listed_market or "unknown"] = (
            by_market.get(s.listed_market or "unknown", 0) + 1
        )
    print(f"By market: {by_market}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
