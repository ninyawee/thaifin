"""DuckDB-over-HTTP client for the HuggingFace-hosted thaifin dataset.

Slice #14 (tracer bullet): no caching, no enumeration of tables — single
`financial_lines.parquet` resolved by HF dataset revision.
"""

from __future__ import annotations

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
    """Minimum DuckDB-over-HTTP client.

    Two construction modes:
      - production: ``DatasetClient()`` resolves to the HF-hosted parquet at
        the revision passed to ``query``.
      - test: ``DatasetClient(parquet_url="file:///tmp/...parquet")`` pins one
        URL/path and ignores the revision argument on ``query``.
    """

    def __init__(self, parquet_url: str | None = None) -> None:
        self._parquet_url_override = parquet_url

    def _resolve_url(self, revision: str) -> str:
        if self._parquet_url_override is not None:
            return self._parquet_url_override
        return _parquet_url(revision)

    def query(self, sql: str, revision: str = "main") -> pd.DataFrame:
        """Run a DuckDB query against the resolved parquet URL.

        The SQL must reference the parquet via the placeholder ``{lines}`` —
        the client substitutes the resolved URL inside ``read_parquet(...)``.
        Example::

            client.query(
                "SELECT period, value FROM {lines} "
                "WHERE symbol = 'PTT' AND concept = 'capex'",
                revision="tracer.0",
            )
        """
        url = self._resolve_url(revision)
        rendered = sql.format(lines=f"read_parquet('{url}')")
        con = duckdb.connect()
        try:
            con.execute("INSTALL httpfs; LOAD httpfs;")
            return con.execute(rendered).fetchdf()
        finally:
            con.close()
