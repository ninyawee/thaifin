"""Tests for the ``Stock(source=...)`` toggle and deprecation warning."""

from __future__ import annotations

import warnings

import pytest

from thaifin import stock as stock_module
from thaifin.stock import Stock


@pytest.fixture(autouse=True)
def _stub_thai_securities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid real ThaiSecuritiesData HTTP calls in __init__."""
    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )


def test_default_source_emits_deprecation_warning() -> None:
    with pytest.warns(DeprecationWarning, match=r"v3\.0"):
        s = Stock("PTT")
    assert s.source == "dataset"


def test_explicit_dataset_source_silent() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        s = Stock("PTT", source="dataset")
    assert s.source == "dataset"


def test_explicit_live_source_silent_and_preserved() -> None:
    """source='live' must be honored exactly and emit no warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        s = Stock("PTT", source="live")
    assert s.source == "live"


def test_capex_on_live_raises_not_implemented() -> None:
    """The v1 live path doesn't have a CapEx surface; .capex must error."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        s = Stock("PTT", source="live")
    with pytest.raises(NotImplementedError):
        _ = s.capex
