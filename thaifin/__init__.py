"""thaifin — Thai listed-company fundamentals as a library + dataset.

Top-level surface:
  - :class:`Stock`, :class:`Stocks` — symbol-scoped accessors.
  - :func:`download_dataset` — bulk-fetch a revision for offline use.
  - :func:`set_data_revision`, :func:`get_data_revision` — pin the active
    HF dataset revision process-wide.
  - :func:`financial_lines`, :func:`concepts`, :func:`auditor_reports`,
    :func:`notes_text` — power-user LazyFrames over the active revision.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from thaifin.data import (
    DATASET_REPO,
    DEFAULT_REVISION,
    DatasetClient,
    cache_dir_for,
    download_dataset,
    get_data_revision,
    set_data_revision,
)
from thaifin.stock import Stock
from thaifin.stocks import Stocks

if TYPE_CHECKING:  # pragma: no cover - type-only imports
    import polars as pl


def _resolve_table(table: str, revision: str | None) -> str:
    """Resolve to a local cache path if downloaded; else the HF URL.

    Polars' ``scan_parquet`` accepts both local paths and HTTPS URLs.
    """
    rev = revision if revision is not None else get_data_revision()
    local = cache_dir_for(rev) / f"{table}.parquet"
    if local.exists():
        return str(local)
    return (
        f"https://huggingface.co/datasets/{DATASET_REPO}"
        f"/resolve/{rev}/{table}.parquet"
    )


def financial_lines(revision: str | None = None) -> "pl.LazyFrame":
    """Return a Polars LazyFrame over ``financial_lines.parquet``.

    The plan is lazy — no IO happens until ``.collect()`` is called.
    Routes through the local cache when available.
    """
    import polars as pl

    return pl.scan_parquet(_resolve_table("financial_lines", revision))


def concepts(revision: str | None = None) -> "pl.LazyFrame":
    """Return a Polars LazyFrame over ``concepts.parquet``.

    Columns: ``concept``, ``statement``, ``label_en``, ``label_th``,
    ``aliases_th``, ``xbrl_ref``.
    """
    import polars as pl

    return pl.scan_parquet(_resolve_table("concepts", revision))


def auditor_reports(revision: str | None = None) -> "pl.LazyFrame":
    """Return a Polars LazyFrame over ``auditor_reports.parquet``."""
    import polars as pl

    return pl.scan_parquet(_resolve_table("auditor_reports", revision))


def notes_text(revision: str | None = None) -> "pl.LazyFrame":
    """Return a Polars LazyFrame over ``notes_text.parquet``."""
    import polars as pl

    return pl.scan_parquet(_resolve_table("notes_text", revision))


__all__ = [
    "DEFAULT_REVISION",
    "DatasetClient",
    "Stock",
    "Stocks",
    "auditor_reports",
    "concepts",
    "download_dataset",
    "financial_lines",
    "get_data_revision",
    "notes_text",
    "set_data_revision",
]
