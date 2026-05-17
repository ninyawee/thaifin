"""Process-wide revision pin tests."""

from __future__ import annotations

import pytest

import thaifin
from thaifin.data.revision import (
    DEFAULT_REVISION,
    get_data_revision,
    reset_data_revision,
    set_data_revision,
)


@pytest.fixture(autouse=True)
def _reset_revision() -> None:
    """Each test starts and ends at the library default."""
    reset_data_revision()
    yield
    reset_data_revision()


def test_default_is_main() -> None:
    assert get_data_revision() == "main"
    assert DEFAULT_REVISION == "main"


def test_set_data_revision_updates_global() -> None:
    set_data_revision("2026.05")
    assert get_data_revision() == "2026.05"


def _spy_client_class(captured: dict[str, str]):
    """Build a ``DatasetClient`` subclass that records the revision used.

    Returns a minimal row set that satisfies the new
    ``_statement_dataframe`` query shape (period + concept + value).
    """
    from thaifin.data.client import DatasetClient

    class _SpyClient(DatasetClient):
        def query(self, sql, revision="main"):  # type: ignore[override]
            captured["revision"] = revision
            import pandas as pd

            return pd.DataFrame(
                [
                    {
                        "period": "2025",
                        "concept": "capex",
                        "value": -159_512_958_954.0,
                    }
                ]
            )

    return _SpyClient


def test_set_data_revision_propagates_to_new_stock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Stock created after a pin uses the pinned revision when fetching."""
    from thaifin import stock as stock_module

    captured: dict[str, str] = {}
    monkeypatch.setattr(stock_module, "DatasetClient", _spy_client_class(captured))
    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )

    set_data_revision("pinned-rev")
    s = stock_module.Stock("PTT", source="dataset")
    _ = s.cash_flow_statement
    assert captured["revision"] == "pinned-rev"


def test_per_instance_revision_overrides_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thaifin import stock as stock_module

    captured: dict[str, str] = {}
    monkeypatch.setattr(stock_module, "DatasetClient", _spy_client_class(captured))
    monkeypatch.setattr(
        stock_module.ThaiSecuritiesDataService,
        "get_stock",
        lambda self, symbol, language="en": stock_module.SecurityData.model_construct(
            symbol=symbol
        ),
    )

    set_data_revision("pin-A")
    s = stock_module.Stock("PTT", source="dataset", revision="explicit-B")
    _ = s.cash_flow_statement
    assert captured["revision"] == "explicit-B"


def test_set_data_revision_rejects_empty() -> None:
    with pytest.raises(ValueError):
        set_data_revision("")


def test_top_level_reexports() -> None:
    """``thaifin.set_data_revision`` and ``get_data_revision`` are exposed."""
    thaifin.set_data_revision("v")
    assert thaifin.get_data_revision() == "v"
