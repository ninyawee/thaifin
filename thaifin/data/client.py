"""DuckDB-over-HTTP client for the HuggingFace-hosted thaifin dataset.

Slice #14 introduced the tracer round-trip. Slice #16 adds:
  - Session-level memoization via ``functools.lru_cache`` keyed on
    ``(sql, revision)``. Two identical queries within one process result
    in exactly one HTTP round-trip.
  - Local-cache routing: if ``download_dataset(revision=...)`` has been
    called (or the user constructs a client with ``local_cache_dir=...``),
    queries read from the on-disk parquet instead of the HF URL.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

DATASET_REPO = "ninyawee/thaifin-financials"


def _parquet_url(revision: str, table: str = "financial_lines") -> str:
    """Compose the HF resolve URL for a table at a given revision.

    `revision` is any git ref the HF repo recognizes — branch, tag, or sha.
    For local file paths or arbitrary URLs (used in tests), the caller passes
    the URL through `DatasetClient(parquet_url=...)` instead.
    """
    return (
        f"https://huggingface.co/datasets/{DATASET_REPO}"
        f"/resolve/{revision}/{table}.parquet"
    )


class DatasetClient:
    """DuckDB-over-HTTP client with session memoization and offline support.

    Three construction modes (most-specific wins):
      - ``DatasetClient(parquet_url="file:///tmp/...parquet")`` pins one
        URL/path and ignores ``revision``. Used by tests.
      - ``DatasetClient(local_cache_dir=Path("/.../<revision>"))`` reads
        ``financial_lines.parquet`` from a local directory (typical after
        ``download_dataset()``).
      - ``DatasetClient()`` resolves to the HF-hosted parquet at the
        revision passed to ``query``.
    """

    def __init__(
        self,
        parquet_url: str | None = None,
        local_cache_dir: Path | None = None,
    ) -> None:
        self._parquet_url_override = parquet_url
        self._local_cache_dir = local_cache_dir

    def _resolve_url(self, revision: str, table: str = "financial_lines") -> str:
        if self._parquet_url_override is not None:
            return self._parquet_url_override
        if self._local_cache_dir is not None:
            local = Path(self._local_cache_dir) / f"{table}.parquet"
            if local.exists():
                return str(local)
        return _parquet_url(revision, table)

    def query(self, sql: str, revision: str = "main") -> pd.DataFrame:
        """Run a DuckDB query against the resolved parquet URL.

        The SQL must reference the parquet via the placeholder ``{lines}`` —
        the client substitutes the resolved URL inside ``read_parquet(...)``.
        Results are memoized per ``(sql, revision)`` for the lifetime of
        the process; clear with :func:`clear_cache`.
        """
        url = self._resolve_url(revision)
        return _cached_query(sql, url).copy()

    @staticmethod
    def clear_cache() -> None:
        """Drop the session memoization. Mainly for tests."""
        _cached_query.cache_clear()

    @staticmethod
    def cache_info():  # pragma: no cover - thin pass-through
        """Expose lru_cache stats (hits/misses/maxsize/currsize)."""
        return _cached_query.cache_info()


@lru_cache(maxsize=128)
def _cached_query(sql: str, url: str) -> pd.DataFrame:
    """Execute a query against a resolved parquet URL. Memoized per process.

    Cache key is ``(sql, url)``; ``url`` already encodes the revision (or
    points at a local cache file), so this matches the spec's
    ``(sql, revision)`` semantics without leaking the revision string when
    a ``parquet_url`` override or local cache is in play.
    """
    rendered = sql.format(lines=f"read_parquet('{url}')")
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        return con.execute(rendered).fetchdf()
    finally:
        con.close()
