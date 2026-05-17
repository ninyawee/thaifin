"""Unit tests for the tracer-bullet round-trip (slice #14).

Writes a 1-row fixture parquet matching the schema produced by
``scripts/tracer.py`` and asserts that ``DatasetClient`` round-trips it
back. No network IO.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from thaifin.data import DatasetClient

CAPEX_LABEL_TH = (
    "เงินสดจ่ายสำหรับที่ดิน อาคารและอุปกรณ์ และอสังหาริมทรัพย์เพื่อการลงทุน"
)
EXPECTED_CAPEX_VALUE = -159_512_958_954


@pytest.fixture
def fixture_parquet(tmp_path: Path) -> Path:
    """Write the same 1-row schema scripts/tracer.py would produce."""
    df = pd.DataFrame(
        [
            {
                "symbol": "PTT",
                "period": "2025",
                "statement": "CF",
                "concept": "capex",
                "raw_label_th": CAPEX_LABEL_TH,
                "value": float(EXPECTED_CAPEX_VALUE),
                "audit_basis": "audited",
                "consolidation": "consolidated",
                "filing_id": "PTT-2025-A-tracer",
            }
        ]
    )
    out = tmp_path / "financial_lines.parquet"
    df.to_parquet(out, engine="pyarrow", index=False)
    return out


def test_dataset_client_returns_capex_value(fixture_parquet: Path) -> None:
    client = DatasetClient(parquet_url=str(fixture_parquet))
    df = client.query(
        "SELECT period, value FROM {lines} "
        "WHERE symbol = 'PTT' AND concept = 'capex' "
        "AND consolidation = 'consolidated'"
    )
    assert len(df) == 1
    assert int(df["value"].iloc[0]) == EXPECTED_CAPEX_VALUE
    assert df["period"].iloc[0] == "2025"


def test_dataset_client_preserves_raw_label(fixture_parquet: Path) -> None:
    client = DatasetClient(parquet_url=str(fixture_parquet))
    df = client.query(
        "SELECT raw_label_th FROM {lines} WHERE concept = 'capex'"
    )
    assert df["raw_label_th"].iloc[0] == CAPEX_LABEL_TH


def test_stock_capex_via_dataset(
    fixture_parquet: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``stock.cash_flow_statement['capex']`` round-trips the tracer fixture.

    Replaces the v1 ``Stock.capex`` accessor (removed in v2 per
    ``docs/adr/0002``). The fixture only has an annual filing, so only
    the ``FY`` column is populated; Q1..Q4 are NaN.
    """
    from thaifin import stock as stock_module

    class _PinnedClient(DatasetClient):
        def __init__(self) -> None:  # type: ignore[override]
            super().__init__(parquet_url=str(fixture_parquet))

    monkeypatch.setattr(stock_module, "DatasetClient", _PinnedClient)

    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )

    s = stock_module.Stock("PTT", source="dataset", revision="tracer.0")
    capex_df = s.cash_flow_statement["capex"]
    assert isinstance(capex_df, pd.DataFrame)
    fy_value = capex_df.loc[pd.Period("2025", freq="Y"), "FY"]
    assert int(fy_value) == EXPECTED_CAPEX_VALUE
