"""Session-memoization tests for ``DatasetClient``.

The cache key is ``(sql, resolved_url)`` where ``resolved_url`` already
encodes the revision. Identical query + revision -> exactly one parquet
read. Verified by counting calls to the underlying DuckDB execute path.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from thaifin.data import DatasetClient
from thaifin.data import client as client_module


@pytest.fixture
def fixture_parquet(tmp_path: Path) -> Path:
    """Tiny parquet so DuckDB has something to read."""
    df = pd.DataFrame(
        [
            {
                "symbol": "PTT",
                "period": "2025",
                "concept": "capex",
                "consolidation": "consolidated",
                "value": -159_512_958_954.0,
            }
        ]
    )
    out = tmp_path / "financial_lines.parquet"
    df.to_parquet(out, engine="pyarrow", index=False)
    return out


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Each test starts with an empty session cache."""
    DatasetClient.clear_cache()


def test_query_results_are_memoized(fixture_parquet: Path) -> None:
    """Two identical queries -> exactly one underlying parquet read."""
    sql = (
        "SELECT period, value FROM {lines} "
        "WHERE symbol = 'PTT' AND concept = 'capex'"
    )
    client = DatasetClient(parquet_url=str(fixture_parquet))

    info_before = client_module._cached_query.cache_info()
    df1 = client.query(sql)
    df2 = client.query(sql)
    info_after = client_module._cached_query.cache_info()

    assert df1.equals(df2)
    # one miss (first call), one hit (second call)
    assert info_after.misses - info_before.misses == 1
    assert info_after.hits - info_before.hits == 1


def test_different_revision_misses_cache(fixture_parquet: Path) -> None:
    """Same SQL but different resolved URL -> separate cache entries."""
    sql = "SELECT period FROM {lines}"
    client_a = DatasetClient(parquet_url=str(fixture_parquet))
    client_a.query(sql)
    info_after_a = client_module._cached_query.cache_info()

    # Same payload, different filename -> distinct resolved URL -> cache miss.
    other_path = fixture_parquet.parent / "other.parquet"
    other_path.write_bytes(fixture_parquet.read_bytes())
    client_b = DatasetClient(parquet_url=str(other_path))
    client_b.query(sql)
    info_after_b = client_module._cached_query.cache_info()

    assert info_after_b.misses - info_after_a.misses == 1


def test_clear_cache_resets_state(fixture_parquet: Path) -> None:
    sql = "SELECT period FROM {lines}"
    client = DatasetClient(parquet_url=str(fixture_parquet))
    client.query(sql)
    assert client_module._cached_query.cache_info().currsize >= 1
    DatasetClient.clear_cache()
    assert client_module._cached_query.cache_info().currsize == 0


def test_returned_dataframe_is_independent_copy(
    fixture_parquet: Path,
) -> None:
    """Mutating a returned df must not poison the cached entry."""
    sql = "SELECT period, value FROM {lines}"
    client = DatasetClient(parquet_url=str(fixture_parquet))

    df1 = client.query(sql)
    df1.loc[0, "value"] = 0.0

    df2 = client.query(sql)
    assert df2.loc[0, "value"] != 0.0


def test_local_cache_dir_routing(fixture_parquet: Path, tmp_path: Path) -> None:
    """If ``local_cache_dir/<table>.parquet`` exists, it wins over HF URL."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "financial_lines.parquet").write_bytes(
        fixture_parquet.read_bytes()
    )

    client = DatasetClient(local_cache_dir=cache_dir)
    df = client.query(
        "SELECT period, value FROM {lines} WHERE concept = 'capex'",
        revision="never-fetched",
    )
    assert len(df) == 1
    assert df["period"].iloc[0] == "2025"
