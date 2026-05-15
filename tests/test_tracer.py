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
    """``Stock(...).capex`` returns a pd.Series indexed by period."""
    # Patch DatasetClient inside thaifin.stock so the no-arg construction in
    # the .capex property uses our local fixture parquet.
    from thaifin import stock as stock_module

    class _PinnedClient(DatasetClient):
        def __init__(self) -> None:  # type: ignore[override]
            super().__init__(parquet_url=str(fixture_parquet))

    monkeypatch.setattr(stock_module, "DatasetClient", _PinnedClient)

    # Stock.__init__ calls ThaiSecuritiesDataService for `info`; stub it out
    # so the test doesn't require network access.
    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )

    s = stock_module.Stock(
        "PTT", source="dataset", revision="tracer.0"
    )
    series = s.capex
    assert isinstance(series, pd.Series)
    assert int(series.iloc[0]) == EXPECTED_CAPEX_VALUE
    assert series.index.name == "period"


def test_stock_capex_live_raises() -> None:
    """``.capex`` is dataset-only; live source raises NotImplementedError."""
    from thaifin import stock as stock_module

    # Stub out network call in __init__.
    import pytest as _pytest

    class _FakeStock(stock_module.Stock):
        def __init__(self, symbol: str) -> None:
            self.symbol_upper = symbol.upper()
            self.language = "en"
            self.source = "live"
            self.revision = None
            self.info = stock_module.SecurityData.model_construct(
                symbol=symbol
            )

    with _pytest.raises(NotImplementedError):
        _ = _FakeStock("PTT").capex
