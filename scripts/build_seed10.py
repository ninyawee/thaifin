"""Build the seed-10 dataset: PTT (from HF v0.ptt.11) + 9 SET100 symbols.

For each of the 9 new symbols, runs the per-symbol pipeline from
``scripts.build_dataset`` (no upload), then concatenates the per-symbol
parquets with the existing PTT parquets pulled from
``hf.co/datasets/ninyawee/thaifin-financials @ v0.ptt.11`` and uploads a
single 10-symbol bundle as revision ``v0.seed10``.

Usage::

    fnox exec -- uv run python scripts/build_seed10.py \\
        --out /tmp/seed10 --upload-revision v0.seed10

Coverage report + top-20 unmapped raw labels across the 9 NEW symbols are
printed to stdout at the end. The PTT parquets are concatenated verbatim
from the v0.ptt.11 release — we do NOT re-parse PTT here.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

# Force IPv4-only DNS — market.sec.or.th publishes an AAAA record but the
# IPv6 endpoint is unreachable from many networks (60s SYN-SENT timeouts per
# new connection). Patch getaddrinfo before any HTTP layer initialises.
_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(*args, **kwargs):  # type: ignore[no-untyped-def]
    res = _original_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET] or res


socket.getaddrinfo = _ipv4_only_getaddrinfo  # type: ignore[assignment]


# Patch httpx.Client to send a browser User-Agent by default. SEC IDISC's
# WAF rejects ``python-httpx/*`` and ``thaifin/2.0`` requests after a low
# request volume, returning a "Request Rejected" stub page (HTTP 200 with
# ~250-byte body) — discovery silently sees 0 filings.
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
import httpx as _httpx_mod  # noqa: E402

_orig_httpx_client_init = _httpx_mod.Client.__init__
_orig_httpx_client_get = _httpx_mod.Client.get


def _patched_httpx_client_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    headers = kwargs.get("headers") or {}
    if isinstance(headers, dict):
        headers = dict(headers)
    else:
        headers = dict(headers.items())
    # Override UA whether the caller set one or not — `thaifin/2.0` triggers
    # the WAF too.
    headers["User-Agent"] = _BROWSER_UA
    headers.setdefault(
        "Accept",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    )
    headers.setdefault("Accept-Language", "th-TH,th;q=0.9,en;q=0.8")
    kwargs["headers"] = headers
    _orig_httpx_client_init(self, *args, **kwargs)


# Polite per-request delay against the SEC IDISC host. The WAF rate-limit
# triggers after a few hundred fast requests; a small inter-request delay
# keeps us under it.
_SEC_HOST = "market.sec.or.th"
_SEC_REQUEST_DELAY = float(os.environ.get("SEC_REQUEST_DELAY", "0.5"))
import time as _time_mod  # noqa: E402

_last_sec_request_at: float = 0.0


def _patched_httpx_client_get(self, url, *args, **kwargs):  # type: ignore[no-untyped-def]
    global _last_sec_request_at
    if _SEC_HOST in str(url):
        elapsed = _time_mod.monotonic() - _last_sec_request_at
        if elapsed < _SEC_REQUEST_DELAY:
            _time_mod.sleep(_SEC_REQUEST_DELAY - elapsed)
        _last_sec_request_at = _time_mod.monotonic()
    return _orig_httpx_client_get(self, url, *args, **kwargs)


_httpx_mod.Client.__init__ = _patched_httpx_client_init  # type: ignore[assignment]
_httpx_mod.Client.get = _patched_httpx_client_get  # type: ignore[assignment]

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Make scripts/ importable as a sibling package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_dataset  # noqa: E402

SEED_SYMBOLS = ["BBL", "SCB", "KBANK", "CPALL", "SCC", "AOT", "ADVANC", "CPN", "BDMS"]
PTT_REVISION = "v0.ptt.11"
HF_REPO_ID = "ninyawee/thaifin-financials"
DEFAULT_REVISION = "v0.seed10"

TABLES = ("financial_lines", "auditor_reports", "notes_text", "filings")

logger = logging.getLogger("thaifin.build_seed10")


# --- PTT pull from HF -------------------------------------------------------


def _download_ptt(out_dir: Path) -> dict[str, Path]:
    """Pull every PTT-revision parquet from HF and stash under ``out_dir``."""
    from huggingface_hub import hf_hub_download

    ptt_dir = out_dir / "ptt"
    ptt_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table in TABLES:
        local = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=f"{table}.parquet",
            repo_type="dataset",
            revision=PTT_REVISION,
            local_dir=str(ptt_dir),
        )
        paths[table] = Path(local)
        logger.info("    fetched PTT %s -> %s", table, paths[table])
    return paths


# --- Per-symbol build -------------------------------------------------------


def _build_symbol(
    symbol: str,
    out_root: Path,
    cache_root: Path,
    fetch_timeout: float,
) -> tuple[Path, dict]:
    """Run ``build_dataset.build`` for one symbol; return (parquet_dir, summary)."""
    sym_out = out_root / symbol
    sym_cache = cache_root / symbol
    sym_out.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    try:
        summary = build_dataset.build(
            symbol=symbol,
            out_dir=sym_out,
            cache_dir=sym_cache,
            limit=None,
            upload=False,
            cache_only=False,
            fetch_timeout=fetch_timeout,
        )
    except Exception as e:
        elapsed = time.monotonic() - started
        logger.error(
            "    BUILD FAILED for %s after %.1fs: %s",
            symbol,
            elapsed,
            e,
        )
        traceback.print_exc()
        return sym_out, {
            "symbol": symbol,
            "filings_total": 0,
            "filings_parsed": 0,
            "filings_skipped": 0,
            "financial_lines_total": 0,
            "financial_lines_mapped": 0,
            "concept_coverage_ratio": 0.0,
            "auditor_reports_total": 0,
            "notes_total": 0,
            "build_error": str(e),
        }
    elapsed = time.monotonic() - started
    summary["elapsed_sec"] = round(elapsed, 1)
    logger.info(
        "    DONE %s: %d filings, %d rows, %.1f%% mapped, %.1fs",
        symbol,
        summary["filings_total"],
        summary["financial_lines_total"],
        100 * summary["concept_coverage_ratio"],
        elapsed,
    )

    # Free disk: drop the cached zips once parsing succeeded.
    try:
        for p in sym_cache.glob("*.zip"):
            p.unlink(missing_ok=True)
    except OSError:
        pass

    return sym_out, summary


# --- Concatenation ----------------------------------------------------------


def _concat_table(
    table: str,
    sym_dirs: list[Path],
    ptt_path: Path,
    final_dir: Path,
) -> int:
    """Concat per-symbol parquets + PTT parquet into final/<table>.parquet."""
    tables: list[pa.Table] = []
    base_schema: pa.Schema | None = None
    for sd in sym_dirs:
        p = sd / f"{table}.parquet"
        if not p.exists():
            logger.warning("    %s missing %s, skipping", sd.name, table)
            continue
        t = pq.read_table(p)
        if t.num_rows == 0:
            logger.info("    %s/%s empty (0 rows)", sd.name, table)
            continue
        if base_schema is None:
            base_schema = t.schema
        elif not t.schema.equals(base_schema):
            # Cast to base schema if column sets match — datatype coercion only.
            try:
                t = t.cast(base_schema)
            except Exception as e:
                logger.warning(
                    "    schema mismatch on %s/%s: %s — skipping",
                    sd.name,
                    table,
                    e,
                )
                continue
        tables.append(t)

    # PTT (from HF) goes last; align schema if necessary.
    ptt_table = pq.read_table(ptt_path)
    if base_schema is None:
        base_schema = ptt_table.schema
    elif not ptt_table.schema.equals(base_schema):
        try:
            ptt_table = ptt_table.cast(base_schema)
        except Exception as e:
            logger.warning(
                "    PTT %s schema cast failed: %s — using PTT schema as base",
                table,
                e,
            )
            # Re-cast everything to PTT's schema.
            base_schema = ptt_table.schema
            recast: list[pa.Table] = []
            for t in tables:
                try:
                    recast.append(t.cast(base_schema))
                except Exception:
                    pass
            tables = recast
    tables.append(ptt_table)

    combined = pa.concat_tables(tables)
    out_path = final_dir / f"{table}.parquet"
    pq.write_table(combined, out_path)
    logger.info(
        "    [%s] -> %d rows (%.2f MB)",
        table,
        combined.num_rows,
        out_path.stat().st_size / 1e6,
    )
    return combined.num_rows


def _emit_concepts(final_dir: Path) -> int:
    """Re-emit concepts.csv as concepts.parquet for the build."""
    concepts_csv = Path(__file__).resolve().parents[1] / "data" / "concepts.csv"
    build_dataset._write_concepts(concepts_csv, final_dir / "concepts.parquet")
    rows = pq.read_metadata(final_dir / "concepts.parquet").num_rows
    logger.info("    [concepts] -> %d rows", rows)
    return rows


# --- Reporting --------------------------------------------------------------


def _coverage_report(
    summaries: list[dict],
    final_dir: Path,
    ptt_path: Path,
) -> str:
    """Build a per-symbol coverage table + global totals (10 symbols).

    PTT row counts come from the v0.ptt.11 parquet (we don't re-parse PTT).
    """
    import duckdb

    con = duckdb.connect()

    fl_path = final_dir / "financial_lines.parquet"
    per_symbol_rows: list[dict] = []

    # PTT row from HF parquet.
    rec = con.execute(
        """
        SELECT
          COUNT(*) AS n_rows,
          COUNT(*) FILTER (WHERE concept IS NOT NULL) AS n_mapped,
          COUNT(DISTINCT filing_id) AS n_filings
        FROM read_parquet(?)
        WHERE symbol = 'PTT'
        """,
        [str(fl_path)],
    ).fetchone()
    per_symbol_rows.append(
        {
            "symbol": "PTT",
            "n_filings": rec[2],
            "n_rows": rec[0],
            "n_mapped": rec[1],
            "pct_mapped": (rec[1] / rec[0] * 100) if rec[0] else 0.0,
        }
    )

    # 9 new symbols from summaries.
    for s in summaries:
        per_symbol_rows.append(
            {
                "symbol": s["symbol"],
                "n_filings": s["filings_total"],
                "n_rows": s["financial_lines_total"],
                "n_mapped": s["financial_lines_mapped"],
                "pct_mapped": (
                    s["financial_lines_mapped"]
                    / s["financial_lines_total"]
                    * 100
                )
                if s["financial_lines_total"]
                else 0.0,
            }
        )

    # Totals.
    total = con.execute(
        """
        SELECT
          COUNT(*) AS n_rows,
          COUNT(*) FILTER (WHERE concept IS NOT NULL) AS n_mapped,
          COUNT(DISTINCT filing_id) AS n_filings
        FROM read_parquet(?)
        """,
        [str(fl_path)],
    ).fetchone()
    per_symbol_rows.append(
        {
            "symbol": "TOTAL",
            "n_filings": total[2],
            "n_rows": total[0],
            "n_mapped": total[1],
            "pct_mapped": (total[1] / total[0] * 100) if total[0] else 0.0,
        }
    )

    lines = ["", "=== Coverage report (10 symbols) ===", ""]
    lines.append(
        f"{'Symbol':<8} | {'n_filings':>10} | {'n_rows':>10} | {'n_mapped':>10} | {'pct_mapped':>10}"
    )
    lines.append("-" * 64)
    for row in per_symbol_rows:
        lines.append(
            f"{row['symbol']:<8} | {row['n_filings']:>10} | "
            f"{row['n_rows']:>10} | {row['n_mapped']:>10} | "
            f"{row['pct_mapped']:>9.2f}%"
        )
    return "\n".join(lines)


def _top_unmapped(final_dir: Path) -> list[tuple[str, int]]:
    """Top-20 unmapped raw labels across the 9 NEW symbols (exclude PTT)."""
    import duckdb

    con = duckdb.connect()
    rows = con.execute(
        """
        SELECT raw_label_th, COUNT(*) AS n
        FROM read_parquet(?)
        WHERE concept IS NULL AND symbol != 'PTT'
        GROUP BY raw_label_th
        ORDER BY n DESC
        LIMIT 20
        """,
        [str(final_dir / "financial_lines.parquet")],
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


# --- Main -------------------------------------------------------------------


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/seed10"),
        help="Working dir; per-symbol + final/ parquets land here.",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=SEED_SYMBOLS,
        help=f"Symbols to add (default: {' '.join(SEED_SYMBOLS)})",
    )
    parser.add_argument(
        "--upload-revision",
        default=DEFAULT_REVISION,
        help=f"HF revision tag (default: {DEFAULT_REVISION})",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip HuggingFace publish (local build only).",
    )
    parser.add_argument(
        "--fetch-timeout",
        type=float,
        default=60.0,
        help="Per-zip HTTP timeout (default: 60s).",
    )
    parser.add_argument(
        "--skip-symbols",
        nargs="*",
        default=[],
        help="Symbols to skip (already built / known failures).",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Reuse already-built per-symbol parquets if present (skip build).",
    )
    args = parser.parse_args()

    _setup_logging()
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    per_sym_dir = out_dir / "per_symbol"
    per_sym_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "zips"
    cache_dir.mkdir(parents=True, exist_ok=True)
    final_dir = out_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== seed-10 build ===")
    logger.info("symbols (new): %s", args.symbols)
    logger.info("skip-symbols : %s", args.skip_symbols)
    logger.info("upload to    : %s @ %s", HF_REPO_ID, args.upload_revision)

    summaries: list[dict] = []
    sym_dirs: list[Path] = []

    def _reuse(sym: str) -> bool:
        """Read the per-symbol parquet from a previous run and append a summary."""
        d = per_sym_dir / sym
        if not (d / "financial_lines.parquet").exists():
            return False
        sym_dirs.append(d)
        t = pq.read_table(d / "financial_lines.parquet")
        df = t.to_pandas()
        n_rows = len(df)
        n_mapped = int(df["concept"].notna().sum()) if n_rows else 0
        n_filings = int(df["filing_id"].nunique()) if n_rows else 0
        # filings.parquet has every filing for the symbol (including 0-row ones)
        if (d / "filings.parquet").exists():
            ft = pq.read_table(d / "filings.parquet")
            n_filings = max(n_filings, ft.num_rows)
        summaries.append(
            {
                "symbol": sym,
                "filings_total": n_filings,
                "filings_parsed": n_filings,
                "filings_skipped": 0,
                "financial_lines_total": n_rows,
                "financial_lines_mapped": n_mapped,
                "concept_coverage_ratio": (n_mapped / n_rows) if n_rows else 0.0,
                "auditor_reports_total": pq.read_metadata(
                    d / "auditor_reports.parquet"
                ).num_rows
                if (d / "auditor_reports.parquet").exists()
                else 0,
                "notes_total": pq.read_metadata(d / "notes_text.parquet").num_rows
                if (d / "notes_text.parquet").exists()
                else 0,
                "reused": True,
            }
        )
        return True

    for i, sym in enumerate(args.symbols, 1):
        if sym in args.skip_symbols:
            logger.info(
                "[%d/%d] %s SKIP (per --skip-symbols)", i, len(args.symbols), sym
            )
            _reuse(sym)
            continue
        if args.reuse_existing and _reuse(sym):
            logger.info(
                "[%d/%d] %s REUSE existing per-symbol parquets",
                i,
                len(args.symbols),
                sym,
            )
            continue
        logger.info("[%d/%d] %s build", i, len(args.symbols), sym)
        sym_out, summary = _build_symbol(
            symbol=sym,
            out_root=per_sym_dir,
            cache_root=cache_dir,
            fetch_timeout=args.fetch_timeout,
        )
        sym_dirs.append(sym_out)
        summaries.append(summary)

    # Pull PTT parquets from HF.
    logger.info("[ptt] download from HF @ %s", PTT_REVISION)
    ptt_paths = _download_ptt(out_dir)

    # Concatenate.
    logger.info("[concat] writing final/<table>.parquet")
    final_counts: dict[str, int] = {}
    for table in TABLES:
        final_counts[table] = _concat_table(
            table, sym_dirs, ptt_paths[table], final_dir
        )
    final_counts["concepts"] = _emit_concepts(final_dir)

    # Reports.
    report = _coverage_report(summaries, final_dir, ptt_paths["financial_lines"])
    print(report)
    print()
    print("=== Top-20 unmapped raw labels (9 new symbols, excludes PTT) ===")
    for label, n in _top_unmapped(final_dir):
        print(f"  {n:>6}  {label}")
    print()

    # Persist summaries for the report.
    (out_dir / "build_summary.json").write_text(
        json.dumps(
            {
                "symbols": [s["symbol"] for s in summaries],
                "summaries": summaries,
                "final_counts": final_counts,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # Publish.
    if args.no_upload:
        logger.info("[publish] --no-upload set, skipping HF push")
        return 0

    token = os.environ.get("HF_TOKEN")
    if not token:
        logger.error("HF_TOKEN not set; run via `fnox exec -- ...`")
        return 2

    from huggingface_hub import HfApi
    from huggingface_hub.utils import HfHubHTTPError

    logger.info("[publish] uploading %s -> %s @ %s", final_dir, HF_REPO_ID, args.upload_revision)
    api = HfApi(token=token)
    commit_info = api.upload_folder(
        folder_path=str(final_dir),
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        commit_message=f"Publish revision {args.upload_revision} (PTT + 9 SET100)",
        allow_patterns=["*.parquet"],
    )
    sha = getattr(commit_info, "oid", None) or str(commit_info)

    # Tag.
    try:
        api.delete_tag(repo_id=HF_REPO_ID, tag=args.upload_revision, repo_type="dataset")
    except (HfHubHTTPError, Exception):
        pass
    api.create_tag(
        repo_id=HF_REPO_ID,
        tag=args.upload_revision,
        repo_type="dataset",
        revision=sha,
        tag_message=f"Revision {args.upload_revision}",
    )
    logger.info("[publish] committed %s, tagged %s", (sha or "?")[:8], args.upload_revision)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
