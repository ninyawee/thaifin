"""Build the thaifin dataset for one symbol end-to-end.

Slice #15 scope: ``--symbol PTT`` only. Walks the SEC IDISC fs-norm page
for the symbol, downloads each filing zip, parses XLS/DOC components,
applies the concept dictionary, writes five parquets, and (unless
``--no-upload``) pushes the bundle to HuggingFace as ``v0.ptt``.

Run with::

    fnox exec -- uv run python scripts/build_dataset.py --symbol PTT

The script is idempotent: zip downloads are content-addressed by sha256,
re-running uploads identical parquets and re-creates the HF tag.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from thaifin.concepts import (
    apply_concepts,
    coverage,
    load_concepts,
)
from thaifin.parsers.auditor_report import parse_auditor_report, row_to_record as auditor_to_record
from thaifin.parsers.financial_statements import (
    parse_financial_statements,
    rows_to_records,
)
from thaifin.parsers.notes import parse_notes, row_to_record as notes_to_record
from thaifin.sources.sec_idisc import (
    FilingManifestEntry,
    discover_filings,
    filings_to_records,
)

HF_REPO_ID = "ninyawee/thaifin-financials"
HF_REVISION_TAG = "v0.ptt"

logger = logging.getLogger("thaifin.build_dataset")


# --- Filing fetch ----------------------------------------------------------


def _fetch_zip(client: httpx.Client, url: str) -> bytes:
    """Download a filing zip; raise on non-200."""
    resp = client.get(url)
    resp.raise_for_status()
    return resp.content


def _open_zip(blob: bytes) -> dict[str, bytes]:
    """Return ``{filename: bytes}`` for the three files we care about.

    Filenames are uppercased on lookup since some older filings vary case.
    Returns an empty dict if the zip doesn't contain a recognised
    ``FINANCIAL_STATEMENTS.*`` member (pre-2010 ad-hoc layouts).
    """
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            upper = name.upper()
            if (
                upper.startswith("FINANCIAL_STATEMENTS.")
                or upper.startswith("AUDITOR_REPORT.")
                or upper.startswith("NOTES.")
            ):
                out[upper] = zf.read(name)
    return out


def _pick(members: dict[str, bytes], prefix: str) -> bytes | None:
    for name, data in members.items():
        if name.startswith(prefix):
            return data
    return None


# --- Parquet writers -------------------------------------------------------


_FIN_LINES_COLUMNS = [
    "symbol",
    "period",
    "statement",
    "concept",
    "raw_label_th",
    "value",
    "audit_basis",
    "consolidation",
    "filing_id",
]


def _write_financial_lines(records: list[dict], out: Path) -> None:
    df = pd.DataFrame(records, columns=_FIN_LINES_COLUMNS)
    df.to_parquet(out, engine="pyarrow", index=False)


def _write_auditor_reports(records: list[dict], out: Path) -> None:
    df = pd.DataFrame(
        records,
        columns=[
            "filing_id",
            "symbol",
            "period",
            "audit_basis",
            "opinion_type",
            "going_concern_emphasis",
            "auditor_firm",
            "signing_date",
            "signing_partner",
            "raw_text_md",
        ],
    )
    df.to_parquet(out, engine="pyarrow", index=False)


def _write_notes(records: list[dict], out: Path) -> None:
    df = pd.DataFrame(records, columns=["filing_id", "symbol", "period", "raw_text_md"])
    df.to_parquet(out, engine="pyarrow", index=False)


def _write_filings(records: list[dict], out: Path) -> None:
    """Write the filings provenance table.

    A filing zip contains both consolidation modes (consolidated / company),
    so the per-row consolidation distinction lives in ``financial_lines``,
    not here. ``audit_basis`` is the only filing-level audit attribute.
    """
    df = pd.DataFrame(
        records,
        columns=[
            "filing_id",
            "symbol",
            "period",
            "audit_basis",
            "source_url",
            "source_sha256",
            "fetched_at",
        ],
    )
    df.to_parquet(out, engine="pyarrow", index=False)


def _write_concepts(concepts_csv: Path, out: Path) -> None:
    """Re-emit concepts.csv as parquet at build time."""
    entries = load_concepts(concepts_csv)
    df = pd.DataFrame(
        [
            {
                "concept": e.concept,
                "statement": e.statement,
                "label_en": e.label_en,
                "label_th": e.label_th,
                "aliases_th": list(e.aliases_th),
                "xbrl_ref": e.xbrl_ref,
            }
            for e in entries
        ]
    )
    df.to_parquet(out, engine="pyarrow", index=False)


# --- HuggingFace push ------------------------------------------------------


def _publish(out_dir: Path) -> None:
    """Upload all five parquets and tag the commit as ``v0.ptt``."""
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "HF_TOKEN not set; run via "
            "`fnox exec -- uv run python scripts/build_dataset.py …`"
        )
    api = HfApi(token=token)

    files = [
        "financial_lines.parquet",
        "concepts.parquet",
        "auditor_reports.parquet",
        "notes_text.parquet",
        "filings.parquet",
    ]
    for name in files:
        path = out_dir / name
        if not path.exists():
            raise FileNotFoundError(f"missing artefact: {path}")
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=name,
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            commit_message=f"v0.ptt: {name}",
        )

    try:
        api.delete_tag(
            repo_id=HF_REPO_ID, tag=HF_REVISION_TAG, repo_type="dataset"
        )
    except Exception:
        pass
    api.create_tag(
        repo_id=HF_REPO_ID,
        tag=HF_REVISION_TAG,
        repo_type="dataset",
        tag_message="thaifin v0 dataset (PTT only)",
    )


# --- Per-filing pipeline ---------------------------------------------------


def _process_filing(
    entry: FilingManifestEntry,
    blob: bytes,
) -> tuple[
    list[dict],  # financial_lines records
    dict | None,  # auditor_reports record
    dict | None,  # notes record
    dict,  # filings provenance record
    str | None,  # error reason if any (None on success)
]:
    """Run all three parsers for one filing. Returns rows + provenance.

    Errors are returned as a string in the last position rather than raised
    so the build can continue across other filings. Counts of skips end up
    in the run summary.
    """
    sha = hashlib.sha256(blob).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()
    provenance = {
        "filing_id": entry.filing_id,
        "symbol": entry.symbol,
        "period": entry.period,
        "audit_basis": entry.audit_basis,
        "source_url": entry.source_url,
        "source_sha256": sha,
        "fetched_at": fetched_at,
    }

    try:
        members = _open_zip(blob)
    except zipfile.BadZipFile as e:
        return [], None, None, provenance, f"bad-zip: {e}"

    fin_data = _pick(members, "FINANCIAL_STATEMENTS.")
    if fin_data is None:
        return (
            [],
            None,
            None,
            provenance,
            "missing-financial-statements (pre-2010 ad-hoc layout?)",
        )

    try:
        fin_rows = parse_financial_statements(
            fin_data,
            filing_id=entry.filing_id,
            period=entry.period,
            audit_basis=entry.audit_basis,
            symbol=entry.symbol,
        )
    except Exception as e:  # pragma: no cover - defensive
        return [], None, None, provenance, f"financial-parse: {e}"

    fin_records = rows_to_records(fin_rows)

    audit_data = _pick(members, "AUDITOR_REPORT.")
    audit_record: dict | None = None
    if audit_data is not None:
        try:
            audit_row = parse_auditor_report(
                audit_data,
                filing_id=entry.filing_id,
                symbol=entry.symbol,
                period=entry.period,
                audit_basis=entry.audit_basis,
            )
            audit_record = auditor_to_record(audit_row)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(
                "auditor-parse failed for %s: %s", entry.filing_id, e
            )

    notes_data = _pick(members, "NOTES.")
    notes_record: dict | None = None
    if notes_data is not None:
        try:
            notes_row = parse_notes(
                notes_data,
                filing_id=entry.filing_id,
                symbol=entry.symbol,
                period=entry.period,
            )
            notes_record = notes_to_record(notes_row)
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(
                "notes-parse failed for %s: %s", entry.filing_id, e
            )

    return fin_records, audit_record, notes_record, provenance, None


# --- Orchestration ---------------------------------------------------------


def build(
    symbol: str,
    out_dir: Path,
    *,
    limit: int | None = None,
    upload: bool = True,
    cache_dir: Path | None = None,
    cache_only: bool = False,
    fetch_timeout: float = 30.0,
) -> dict:
    """Run the full pipeline for ``symbol`` and return a summary dict.

    When ``cache_only`` is True, filings missing from ``cache_dir`` are
    skipped (logged with reason ``cache-miss``) rather than re-downloaded.
    Useful for resuming a partial backfill or running offline.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[1/6] discover filings for %s", symbol)
    with httpx.Client(follow_redirects=True, timeout=60.0) as discovery_client:
        entries = discover_filings(symbol, client=discovery_client)
    if limit is not None:
        entries = entries[:limit]
    logger.info("    %d unique filings", len(entries))

    fin_records: list[dict] = []
    audit_records: list[dict] = []
    notes_records: list[dict] = []
    provenance_rows: list[dict] = []
    skipped: list[dict] = []

    logger.info("[2/6] fetch + parse")
    with httpx.Client(
        follow_redirects=True,
        timeout=fetch_timeout,
        headers={"User-Agent": "thaifin/2.0"},
    ) as fetch_client:
        for i, entry in enumerate(entries, 1):
            logger.info(
                "    (%d/%d) %s %s %s",
                i,
                len(entries),
                entry.filing_id,
                entry.period,
                entry.audit_basis,
            )
            blob: bytes | None = None
            if cache_dir is not None:
                cache_path = cache_dir / f"{entry.filing_id}.zip"
                if cache_path.exists():
                    blob = cache_path.read_bytes()
                elif cache_only:
                    skipped.append(
                        {"filing_id": entry.filing_id, "reason": "cache-miss"}
                    )
                    logger.warning("    skipped: cache-miss")
                    continue
                else:
                    try:
                        blob = _fetch_zip(fetch_client, entry.source_url)
                    except httpx.HTTPError as e:
                        skipped.append(
                            {
                                "filing_id": entry.filing_id,
                                "reason": f"fetch-error: {e}",
                            }
                        )
                        logger.warning("    skipped: fetch-error: %s", e)
                        continue
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(blob)
            else:
                try:
                    blob = _fetch_zip(fetch_client, entry.source_url)
                except httpx.HTTPError as e:
                    skipped.append(
                        {
                            "filing_id": entry.filing_id,
                            "reason": f"fetch-error: {e}",
                        }
                    )
                    logger.warning("    skipped: fetch-error: %s", e)
                    continue
            assert blob is not None  # narrow type for mypy
            fin, aud, notes, prov, err = _process_filing(entry, blob)
            provenance_rows.append(prov)
            if err is not None:
                skipped.append({"filing_id": entry.filing_id, "reason": err})
                logger.warning("    skipped: %s", err)
                continue
            fin_records.extend(fin)
            if aud is not None:
                audit_records.append(aud)
            if notes is not None:
                notes_records.append(notes)

    logger.info("[3/6] apply concepts")
    concepts_csv = Path(__file__).resolve().parents[1] / "data" / "concepts.csv"
    concept_entries = load_concepts(concepts_csv)
    fin_records = apply_concepts(fin_records, concept_entries)
    mapped, total, ratio = coverage(fin_records)
    logger.info(
        "    concept coverage: %d/%d = %.1f%%", mapped, total, 100 * ratio
    )

    logger.info("[4/6] write parquets to %s", out_dir)
    _write_financial_lines(fin_records, out_dir / "financial_lines.parquet")
    _write_auditor_reports(audit_records, out_dir / "auditor_reports.parquet")
    _write_notes(notes_records, out_dir / "notes_text.parquet")
    _write_filings(provenance_rows, out_dir / "filings.parquet")
    _write_concepts(concepts_csv, out_dir / "concepts.parquet")

    summary = {
        "symbol": symbol,
        "filings_total": len(entries),
        "filings_parsed": len(entries) - len(skipped),
        "filings_skipped": len(skipped),
        "skipped_details": skipped,
        "financial_lines_total": len(fin_records),
        "financial_lines_mapped": mapped,
        "concept_coverage_ratio": ratio,
        "auditor_reports_total": len(audit_records),
        "notes_total": len(notes_records),
        "top_unmapped": Counter(
            r["raw_label_th"] for r in fin_records if r["concept"] is None
        ).most_common(10),
    }

    logger.info("[5/6] summary: %s", json.dumps({k: v for k, v in summary.items() if k != "skipped_details"}, ensure_ascii=False, indent=2))

    if upload:
        logger.info("[6/6] upload to HF as %s", HF_REVISION_TAG)
        _publish(out_dir)
    else:
        logger.info("[6/6] --no-upload set; skipping HF push")

    return summary


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="Ticker, e.g. PTT")
    parser.add_argument(
        "--out",
        default="/tmp/thaifin-build",
        help="Output dir for parquets",
    )
    parser.add_argument(
        "--cache",
        default="/tmp/thaifin-build/zips",
        help="Cache dir for zip downloads",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max number of filings"
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip HuggingFace upload",
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Skip filings missing from cache (no network for zip fetch)",
    )
    parser.add_argument(
        "--fetch-timeout",
        type=float,
        default=30.0,
        help="Per-zip HTTP timeout in seconds (default: 30)",
    )
    args = parser.parse_args()

    _setup_logging()
    summary = build(
        symbol=args.symbol,
        out_dir=Path(args.out),
        cache_dir=Path(args.cache) if args.cache else None,
        limit=args.limit,
        upload=not args.no_upload,
        cache_only=args.cache_only,
        fetch_timeout=args.fetch_timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
