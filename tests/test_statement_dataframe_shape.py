"""Shape and derivation tests for the v2 statement DataFrames.

Covers the decisions in ``docs/adr/0002``:

  - Flow statements (IS, CF) emit ``Q1..Q4, FY`` per concept with
    standalone-quarter values derived from YTD-as-stored.
  - Stock statements (BS, EQ) emit ``Q1..Q3, FY`` per concept (no Q4).
  - Missing YTD inputs propagate as NaN; no gap-filling.
  - Row index is ``PeriodIndex(freq='Y')``; columns are a
    ``MultiIndex(['concept', 'period_type'])`` in canonical order.

Uses a small parquet fixture rather than the live HF dataset.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thaifin import stock as stock_module
from thaifin.data import DatasetClient
from thaifin.stock import Stock


@pytest.fixture(autouse=True)
def _stub_thai_securities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid real ThaiSecuritiesData HTTP calls in ``__init__``."""
    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )


@pytest.fixture(autouse=True)
def _clear_dataset_cache() -> None:
    DatasetClient.clear_cache()


@pytest.fixture
def fixture_parquet(tmp_path: Path) -> Path:
    """One symbol, four years, both a flow (CF/capex) and a stock (BS/cash).

    Years chosen to exercise: full coverage, current-year-without-FY,
    and a missing-intermediate-quarter gap.
    """
    rows: list[dict] = []

    def _add(period: str, statement: str, concept: str, value: float) -> None:
        rows.append(
            {
                "symbol": "PTT",
                "period": period,
                "statement": statement,
                "concept": concept,
                "consolidation": "consolidated",
                "value": value,
            }
        )

    # 2024 — full coverage, flow concept (capex on CF)
    _add("2024Q1", "CF", "capex", -100.0)
    _add("2024Q2", "CF", "capex", -250.0)
    _add("2024Q3", "CF", "capex", -400.0)
    _add("2024", "CF", "capex", -500.0)

    # 2025 — Q1/Q2/Q3 only, no FY yet
    _add("2025Q1", "CF", "capex", -50.0)
    _add("2025Q2", "CF", "capex", -110.0)
    _add("2025Q3", "CF", "capex", -180.0)

    # 2008 — Q2 missing, Q3 + FY present
    _add("2008Q1", "CF", "capex", -30.0)
    _add("2008Q3", "CF", "capex", -90.0)
    _add("2008", "CF", "capex", -130.0)

    # BS stock concept on the same symbol — 2024 only, full coverage
    _add("2024Q1", "BS", "cash", 100.0)
    _add("2024Q2", "BS", "cash", 120.0)
    _add("2024Q3", "BS", "cash", 140.0)
    _add("2024", "BS", "cash", 160.0)

    df = pd.DataFrame(rows)
    out = tmp_path / "financial_lines.parquet"
    df.to_parquet(out, engine="pyarrow", index=False)
    return out


@pytest.fixture
def stock_against(monkeypatch: pytest.MonkeyPatch, fixture_parquet: Path):
    """Route ``DatasetClient()`` (no args) to the fixture parquet.

    The production code constructs ``DatasetClient()`` inline; we patch
    the class so the default-construction path resolves to our fixture
    URL regardless of revision.
    """
    real_init = DatasetClient.__init__

    def _patched_init(self, parquet_url=None, local_cache_dir=None) -> None:
        real_init(
            self,
            parquet_url=parquet_url or str(fixture_parquet),
            local_cache_dir=local_cache_dir,
        )

    monkeypatch.setattr(DatasetClient, "__init__", _patched_init)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return Stock("PTT", source="dataset", revision="fixture")


def test_cash_flow_statement_has_five_period_types(stock_against) -> None:
    df = stock_against.cash_flow_statement
    assert isinstance(df.columns, pd.MultiIndex)
    assert df.columns.names == ["concept", "period_type"]
    capex_period_types = [pt for c, pt in df.columns if c == "capex"]
    assert capex_period_types == ["Q1", "Q2", "Q3", "Q4", "FY"]


def test_balance_sheet_has_four_period_types_no_q4(stock_against) -> None:
    df = stock_against.balance_sheet
    cash_period_types = [pt for c, pt in df.columns if c == "cash"]
    assert cash_period_types == ["Q1", "Q2", "Q3", "FY"]
    assert "Q4" not in cash_period_types


def test_flow_standalone_derivation_full_year(stock_against) -> None:
    """2024 has Q1..Q3 YTD + FY all present; standalone derivation is exact."""
    df = stock_against.cash_flow_statement
    row = df.loc[pd.Period("2024", freq="Y"), "capex"]
    assert row["Q1"] == pytest.approx(-100.0)
    assert row["Q2"] == pytest.approx(-150.0)
    assert row["Q3"] == pytest.approx(-150.0)
    assert row["Q4"] == pytest.approx(-100.0)
    assert row["FY"] == pytest.approx(-500.0)
    # Standalone Q1..Q4 must sum to FY when all inputs present.
    assert row[["Q1", "Q2", "Q3", "Q4"]].sum() == pytest.approx(row["FY"])


def test_flow_partial_year_q4_and_fy_are_nan(stock_against) -> None:
    """2025 has Q1..Q3 YTD but no FY — Q4 and FY both NaN."""
    df = stock_against.cash_flow_statement
    row = df.loc[pd.Period("2025", freq="Y"), "capex"]
    assert row["Q1"] == pytest.approx(-50.0)
    assert row["Q2"] == pytest.approx(-60.0)
    assert row["Q3"] == pytest.approx(-70.0)
    assert np.isnan(row["Q4"])
    assert np.isnan(row["FY"])


def test_flow_gap_propagates_nan(stock_against) -> None:
    """2008 has Q1 + Q3 + FY but no Q2 — Q2 and Q3 standalone both NaN."""
    df = stock_against.cash_flow_statement
    row = df.loc[pd.Period("2008", freq="Y"), "capex"]
    assert row["Q1"] == pytest.approx(-30.0)
    assert np.isnan(row["Q2"]), "missing Q2_YTD ⇒ Q2 standalone NaN"
    assert np.isnan(row["Q3"]), "missing Q2_YTD ⇒ Q3 standalone NaN (chain break)"
    assert row["Q4"] == pytest.approx(-40.0), "Q4 = FY - Q3_YTD still computable"
    assert row["FY"] == pytest.approx(-130.0)


def test_stock_snapshots_unchanged(stock_against) -> None:
    """Stock concepts pass per-filing snapshots through unchanged."""
    df = stock_against.balance_sheet
    row = df.loc[pd.Period("2024", freq="Y"), "cash"]
    assert row["Q1"] == pytest.approx(100.0)
    assert row["Q2"] == pytest.approx(120.0)
    assert row["Q3"] == pytest.approx(140.0)
    assert row["FY"] == pytest.approx(160.0)


def test_index_is_yearly_period_index(stock_against) -> None:
    df = stock_against.cash_flow_statement
    assert isinstance(df.index, pd.PeriodIndex)
    assert df.index.freqstr == "Y-DEC"
    assert df.index.name == "year"


def test_single_concept_slice_is_3a_shape(stock_against) -> None:
    """``df['capex']`` returns the year × {Q1..FY} shape from (3a)."""
    df = stock_against.cash_flow_statement
    capex = df["capex"]
    assert list(capex.columns) == ["Q1", "Q2", "Q3", "Q4", "FY"]
    assert isinstance(capex.index, pd.PeriodIndex)
