"""End-to-end backfill: discover symbols → discover filings → fetch → normalize.

This slice (#17) produces:

* ``data/symbols.csv`` — listed-company inventory (delegated to discover_symbols)
* ``<out>/normalized/<filing_id>/`` — OOXML-normalized files per filing
* ``<out>/filings.parquet`` — provenance row per filing
* ``data/state.json`` — incremental cache for the next run

Parsing the OOXML into the tagged long-format is **not** part of this
slice — that's slice #15's parser layer. ``backfill.py`` stops at the
"normalized files + filings.parquet" boundary.

Storage discipline (CI):
  * ~120K filings × ~1 MB ≈ 120 GB of zip data — far over the GH Actions
    14 GB free disk budget. The pipeline therefore **streams**: download
    one zip → normalize → record provenance → optionally delete the zip
    before the next download. ``--cleanup-zips`` (ON by default) enforces
    this; turn it OFF for local debugging when you want to inspect raw
    zips after the fact.

Usage::

    # Smoke test: a few PTT filings, keep zips around for inspection
    uv run python scripts/backfill.py --symbols PTT --limit 3 \
        --out /tmp/backfill --no-cleanup-zips

    # Full backfill (warning: 40+ minutes per letter-shard, ~120 GB peak)
    uv run python scripts/backfill.py --all --out /tmp/backfill --cleanup-zips
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from thaifin.sources.sec_idisc.fetcher import (
    DEFAULT_DELAY_SEC,
    FetchResult,
    FilingFetcher,
    parse_filing_id,
)
from thaifin.sources.sec_idisc.normalize import (
    NormalizationError,
    normalize_to_ooxml,
    requires_libreoffice,
)
from thaifin.sources.sec_idisc.symbols import (
    walk_listed_symbols,
)

FS_NORM_URL = "https://market.sec.or.th/public/idisc/th/Viewmore/fs-norm"

# Thai → English vocab from the fs-norm rows.
_AUDIT_TH = {
    "ตรวจสอบ": "audited",  # annual filings
    "สอบทาน": "reviewed",  # quarterly filings
}
_CONSOL_TH = {
    "รวม": "consolidated",
    "เดี่ยว": "company",
}
_QUARTER_RE = re.compile(r"ไตรมาสที่\s*(\d)")
_THAI_BUDDHIST_YEAR_OFFSET = 543  # 2568 BE → 2025 CE


@dataclass(frozen=True)
class FilingRow:
    """One row parsed from a symbol's fs-norm page.

    Period encoding:
      * Annual filing → ``"YYYY"`` (Gregorian)
      * Quarterly filing → ``"YYYYQq"`` (e.g., ``"2025Q3"``)

    A duplicate version of this struct will appear in slice #15's
    ``discovery.py``. At merge time the canonical owner wins and this
    local copy is deleted.
    """

    symbol: str
    source_url: str
    period: str
    audit_basis: str  # 'audited' | 'reviewed'
    consolidation: str  # 'consolidated' | 'company'


def _parse_thai_year(raw: str) -> int | None:
    """Convert a Thai Buddhist-Era year string to Gregorian (``2568`` → ``2025``)."""
    raw = raw.strip()
    if not raw.isdigit():
        return None
    year = int(raw)
    if year > 2400:  # heuristic: BE years from 2400+
        return year - _THAI_BUDDHIST_YEAR_OFFSET
    return year


def _row_to_filing(symbol: str, cells: list[str], href: str) -> FilingRow | None:
    """Build a ``FilingRow`` from one ``<tr>``'s cell texts + link href.

    Cell layout (observed on PTT fs-norm 2026-05):
      [0] company name (Thai)
      [1] year (Buddhist Era, e.g. ``"2568"``)
      [2] audit basis (``"ตรวจสอบ"`` / ``"สอบทาน"``)
      [3] consolidation (``"รวม"`` / ``"เดี่ยว"``)
      [4] period descriptor (``"งบปี"`` / ``"ไตรมาสที่ N"``)
      [5] period-end date (``"DD/MM/YYYY"`` Buddhist Era)
      [6] (download icon — empty text)
    """
    if len(cells) < 6:
        return None
    year_ce = _parse_thai_year(cells[1])
    if year_ce is None:
        return None
    audit = _AUDIT_TH.get(cells[2].strip())
    consol = _CONSOL_TH.get(cells[3].strip())
    if not audit or not consol:
        return None
    period_desc = cells[4].strip()
    if "งบปี" in period_desc:
        period = str(year_ce)
    else:
        m = _QUARTER_RE.search(period_desc)
        if not m:
            return None
        period = f"{year_ce}Q{m.group(1)}"
    full_url = (
        href
        if href.startswith("http")
        else f"https://market.sec.or.th{href}"
    )
    return FilingRow(
        symbol=symbol,
        source_url=full_url,
        period=period,
        audit_basis=audit,
        consolidation=consol,
    )


def parse_fs_norm_html(symbol: str, html: str) -> list[FilingRow]:
    """Extract one ``FilingRow`` per zip link from a fs-norm HTML page.

    Each filing produces TWO rows in the page (consolidated + company)
    that point to the SAME zip URL. Both rows are returned; downstream
    dedup happens by ``filing_id`` when building the parquet.
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[FilingRow] = []
    for link in soup.find_all("a", href=lambda h: h and "FILEID=" in h):
        tr = link.find_parent("tr")
        if tr is None:
            continue
        cell_texts = [c.get_text(strip=True) for c in tr.find_all("td")]
        row = _row_to_filing(symbol, cell_texts, link["href"])
        if row is not None:
            out.append(row)
    return out


def discover_filings_for_symbol(
    symbol: str, client: httpx.Client
) -> list[FilingRow]:
    """Hit fs-norm for one symbol and return its filing rows."""
    resp = client.get(FS_NORM_URL, params={"searchSymbol": symbol})
    resp.raise_for_status()
    return parse_fs_norm_html(symbol, resp.text)


def _build_filings_parquet(
    rows_by_filing_id: dict[str, list[FilingRow]],
    fetch_results: dict[str, FetchResult],
    out_path: Path,
) -> Path:
    """Compose the filings.parquet from per-row provenance.

    One row per ``(filing_id, consolidation)`` pair so consumers can join
    on either axis. ``audit_basis``, ``period``, ``symbol`` are the same
    across both consolidations of one filing.
    """
    records = []
    for filing_id, rows in rows_by_filing_id.items():
        fr = fetch_results.get(filing_id)
        if fr is None:
            continue
        for r in rows:
            records.append(
                {
                    "filing_id": filing_id,
                    "symbol": r.symbol,
                    "period": r.period,
                    "audit_basis": r.audit_basis,
                    "consolidation": r.consolidation,
                    "source_url": r.source_url,
                    "source_sha256": fr.source_sha256,
                    "fetched_at": fr.fetched_at,
                }
            )
    df = pd.DataFrame(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, engine="pyarrow", index=False)
    return out_path


def _process_filings(
    filings: list[FilingRow],
    fetcher: FilingFetcher,
    normalized_root: Path,
    cleanup_zips: bool,
) -> tuple[
    dict[str, FetchResult],
    dict[str, list[FilingRow]],
    list[tuple[str, str, str]],
    int,
]:
    """Stream-process: fetch → normalize → optionally delete zip per filing.

    Returns:
      * fetch_results : ``{filing_id: FetchResult}``
      * rows_by_id    : ``{filing_id: [FilingRow, ...]}``
      * failures      : list of ``(filing_id, shape, error_message)``
      * total_bytes   : total downloaded bytes (post-skip)
    """
    import zipfile

    fetch_results: dict[str, FetchResult] = {}
    rows_by_id: dict[str, list[FilingRow]] = defaultdict(list)
    failures: list[tuple[str, str, str]] = []
    total_bytes = 0

    # Group rows by zip URL — same zip is referenced by both consolidations.
    by_url: dict[str, list[FilingRow]] = defaultdict(list)
    for r in filings:
        by_url[r.source_url].append(r)

    for url, group in by_url.items():
        fid = parse_filing_id(url)
        rows_by_id[fid].extend(group)
        try:
            fr = fetcher.fetch(url)
        except Exception as exc:
            failures.append((fid, "fetch_error", str(exc)))
            continue
        fetch_results[fid] = fr
        if fr.local_zip_path is not None and not fr.was_skipped:
            total_bytes += fr.local_zip_path.stat().st_size

        if fr.local_zip_path is None or fr.was_skipped:
            # Skipped via cache — assume previous-run normalized dir is fine.
            continue

        # Extract zip into a per-filing temp dir.
        extract_dir = normalized_root / fid / "_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(fr.local_zip_path) as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as exc:
            failures.append((fid, "bad_zip", str(exc)))
            if cleanup_zips:
                fr.local_zip_path.unlink(missing_ok=True)
            continue

        out_dir = normalized_root / fid
        # Normalize each interesting file in the extracted contents.
        for member in extract_dir.iterdir():
            if not member.is_file():
                continue
            try:
                normalize_to_ooxml(member, out_dir)
            except NormalizationError as exc:
                # Try to attribute by shape for the coverage report.
                from thaifin.sources.sec_idisc.normalize import classify_input

                try:
                    shape = classify_input(member)
                except Exception:
                    shape = "unreadable"
                failures.append((fid, shape, f"{member.name}: {exc}"))

        # Wipe the extracted intermediate; keep the normalized OOXML files.
        for member in extract_dir.iterdir():
            try:
                member.unlink()
            except OSError:
                pass
        try:
            extract_dir.rmdir()
        except OSError:
            pass

        if cleanup_zips:
            fr.local_zip_path.unlink(missing_ok=True)

    return fetch_results, rows_by_id, failures, total_bytes


def _print_coverage_report(
    symbols: list[str],
    filings: list[FilingRow],
    fetch_results: dict[str, FetchResult],
    failures: list[tuple[str, str, str]],
    total_bytes: int,
    elapsed: float,
) -> None:
    """Print the human-readable end-of-run report to stderr."""
    skipped = sum(1 for fr in fetch_results.values() if fr.was_skipped)
    fetched = sum(1 for fr in fetch_results.values() if not fr.was_skipped)
    by_symbol: Counter[str] = Counter(r.symbol for r in filings)

    failures_by_shape: Counter[str] = Counter(shape for _, shape, _ in failures)

    print("", file=sys.stderr)
    print("=== backfill coverage report ===", file=sys.stderr)
    print(f"symbols processed     : {len(symbols)}", file=sys.stderr)
    print(
        f"filings discovered    : {len(set((r.symbol, r.source_url) for r in filings))}",
        file=sys.stderr,
    )
    print(f"  fetched (downloaded): {fetched}", file=sys.stderr)
    print(f"  skipped (cache)     : {skipped}", file=sys.stderr)
    print(
        f"download volume       : {total_bytes / 1e6:.1f} MB", file=sys.stderr
    )
    print(f"wall-clock elapsed    : {elapsed:.1f} s", file=sys.stderr)

    print("", file=sys.stderr)
    print("Top 10 symbols by filing count:", file=sys.stderr)
    for sym, cnt in by_symbol.most_common(10):
        print(f"  {sym:>10} : {cnt}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Bottom 10 symbols by filing count:", file=sys.stderr)
    bottom = sorted(by_symbol.items(), key=lambda x: x[1])[:10]
    for sym, cnt in bottom:
        print(f"  {sym:>10} : {cnt}", file=sys.stderr)

    print("", file=sys.stderr)
    print(
        f"Normalization failures: {len(failures)} (by detected shape)",
        file=sys.stderr,
    )
    for shape, cnt in failures_by_shape.most_common():
        print(f"  {shape:>16} : {cnt}", file=sys.stderr)
    if failures and len(failures) <= 30:
        for fid, shape, err in failures:
            print(f"    {fid} [{shape}]: {err[:120]}", file=sys.stderr)


def _resolve_symbols(args: argparse.Namespace) -> list[str]:
    """Reconcile --all / --symbols / --symbols-file flags."""
    if args.all:
        print("Walking SEC IDISC letter pages…", file=sys.stderr)
        all_syms = walk_listed_symbols(delay=DEFAULT_DELAY_SEC)
        return [s.symbol for s in all_syms]
    if args.symbols:
        return list(args.symbols)
    if args.symbols_file:
        out: list[str] = []
        with Path(args.symbols_file).open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if "symbol" in row and row["symbol"]:
                    out.append(row["symbol"])
                elif row:
                    out.append(next(iter(row.values())))
        return out
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="One or more symbols to backfill (mutually exclusive with --all)",
    )
    parser.add_argument(
        "--symbols-file",
        help="Read symbols from a CSV (column 'symbol' or first column)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Walk every listed symbol from SEC IDISC (slow)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap number of filings per symbol (smoke-test)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/thaifin-backfill"),
        help="Working directory for zips, normalized files, parquet",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("data/state.json"),
        help="Incremental cache file (default: data/state.json)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SEC,
        help=f"Polite delay between fetches (default {DEFAULT_DELAY_SEC}s)",
    )
    parser.add_argument(
        "--cleanup-zips",
        action="store_true",
        default=True,
        help="Delete zips after normalization (default: on, required in CI)",
    )
    parser.add_argument(
        "--no-cleanup-zips",
        action="store_false",
        dest="cleanup_zips",
        help="Keep zips for local debugging",
    )
    args = parser.parse_args()

    symbols = _resolve_symbols(args)
    if not symbols:
        parser.error("specify --all, --symbols, or --symbols-file")

    if not requires_libreoffice():
        print(
            "WARNING: libreoffice not on PATH — true legacy XLS/DOC files "
            "will fail normalization. Modern OOXML-disguised files still work.",
            file=sys.stderr,
        )

    out_dir = args.out
    zips_dir = out_dir / "zips"
    norm_dir = out_dir / "normalized"
    parquet_path = out_dir / "filings.parquet"
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()

    # Phase 1: discovery — gather (symbol, url, period, audit, consolidation)
    print(
        f"Discovering filings for {len(symbols)} symbol(s)…", file=sys.stderr
    )
    all_filings: list[FilingRow] = []
    with httpx.Client(
        follow_redirects=True,
        timeout=60.0,
        headers={"User-Agent": "thaifin/2.0"},
    ) as disc_client:
        for i, sym in enumerate(symbols, 1):
            try:
                rows = discover_filings_for_symbol(sym, disc_client)
            except httpx.HTTPError as exc:
                print(f"  [{i}/{len(symbols)}] {sym}: discovery failed: {exc}", file=sys.stderr)
                continue
            if args.limit:
                # Limit by unique zip URLs, not by row count
                seen_urls: set[str] = set()
                kept: list[FilingRow] = []
                for r in rows:
                    if len(seen_urls) >= args.limit and r.source_url not in seen_urls:
                        continue
                    seen_urls.add(r.source_url)
                    kept.append(r)
                rows = kept
            all_filings.extend(rows)
            print(
                f"  [{i}/{len(symbols)}] {sym}: {len(rows)} filing rows",
                file=sys.stderr,
            )
            time.sleep(args.delay)

    # Phase 2: stream-fetch + normalize
    print(
        f"Fetching + normalizing {len(set(r.source_url for r in all_filings))} unique zips…",
        file=sys.stderr,
    )
    with FilingFetcher(
        dest_dir=zips_dir, state_path=args.state, delay=args.delay
    ) as fetcher:
        fetch_results, rows_by_id, failures, total_bytes = _process_filings(
            all_filings, fetcher, norm_dir, args.cleanup_zips
        )
        fetcher.flush_state()

    # Phase 3: provenance parquet
    _build_filings_parquet(rows_by_id, fetch_results, parquet_path)
    print(
        f"Wrote provenance parquet -> {parquet_path}", file=sys.stderr
    )

    # Phase 4: report
    elapsed = time.monotonic() - started
    _print_coverage_report(
        symbols, all_filings, fetch_results, failures, total_bytes, elapsed
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
