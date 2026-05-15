"""Live smoke test against the published HF dataset (slice #14).

Hits ``ninyawee/thaifin-financials`` at revision ``tracer.0`` and asserts
that ``Stock("PTT", source="dataset", revision="tracer.0").capex`` returns
the expected PTT FY2025 consolidated CapEx value.

Network-bound; lives under ``tests/public_internet_tests/`` per repo
convention so it doesn't run in the default unit-test pass.
"""

from __future__ import annotations

import pytest

from thaifin import Stock

EXPECTED_CAPEX_VALUE = -159_512_958_954


def test_stock_capex_round_trips_through_hf() -> None:
    s = Stock("PTT", source="dataset", revision="tracer.0")
    series = s.capex
    assert len(series) >= 1
    # The tracer parquet has exactly one row.
    assert int(series.iloc[0]) == EXPECTED_CAPEX_VALUE


def test_stock_capex_dataset_client_query_directly() -> None:
    """Direct DuckDB-over-HTTP query against HF parquet."""
    from thaifin.data import DatasetClient

    client = DatasetClient()
    df = client.query(
        "SELECT period, value, raw_label_th FROM {lines} "
        "WHERE symbol = 'PTT' AND concept = 'capex' "
        "AND consolidation = 'consolidated'",
        revision="tracer.0",
    )
    assert len(df) == 1
    assert int(df["value"].iloc[0]) == EXPECTED_CAPEX_VALUE
    assert "เงินสดจ่ายสำหรับที่ดิน" in df["raw_label_th"].iloc[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
