"""Offline-mode tests for ``thaifin.download_dataset``.

We don't actually hit HuggingFace here — instead we monkeypatch
``snapshot_download`` to drop a parquet into the target directory, then
verify the same DuckDB query works after disabling HTTP at the socket
layer.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pandas as pd
import pytest

import thaifin
from thaifin.data import DatasetClient, cache_dir_for, download_dataset
from thaifin.data import download as download_module


@pytest.fixture
def fake_parquet_bytes(tmp_path: Path) -> bytes:
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
    p = tmp_path / "_seed.parquet"
    df.to_parquet(p, engine="pyarrow", index=False)
    return p.read_bytes()


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    DatasetClient.clear_cache()


def test_download_dataset_writes_to_default_cache_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_parquet_bytes: bytes,
) -> None:
    """download_dataset honors THAIFIN_CACHE_DIR and creates the revision dir."""
    monkeypatch.setenv("THAIFIN_CACHE_DIR", str(tmp_path / "cache"))

    def _fake_snapshot_download(
        repo_id: str,
        repo_type: str,
        revision: str,
        local_dir: str,
        allow_patterns,
        token,
    ) -> str:
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        (Path(local_dir) / "financial_lines.parquet").write_bytes(
            fake_parquet_bytes
        )
        return local_dir

    monkeypatch.setattr(
        "huggingface_hub.snapshot_download", _fake_snapshot_download
    )

    out = download_dataset(revision="2026.05")

    assert out == tmp_path / "cache" / "2026.05"
    assert (out / "financial_lines.parquet").exists()


def test_query_works_with_network_disabled_after_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_parquet_bytes: bytes,
) -> None:
    """Once a revision is downloaded, queries work with sockets blocked."""
    monkeypatch.setenv("THAIFIN_CACHE_DIR", str(tmp_path / "cache"))

    target = cache_dir_for("offline-test")
    target.mkdir(parents=True, exist_ok=True)
    (target / "financial_lines.parquet").write_bytes(fake_parquet_bytes)

    # Block all outbound socket creation -> any HTTP attempt would fail.
    def _no_network(*args, **kwargs):  # pragma: no cover - guard
        raise OSError("network disabled by test")

    monkeypatch.setattr(socket, "socket", _no_network)

    client = DatasetClient(local_cache_dir=target)
    df = client.query(
        "SELECT period, value FROM {lines} WHERE concept = 'capex'",
        revision="offline-test",
    )
    assert len(df) == 1
    assert df["period"].iloc[0] == "2025"


def test_download_uses_active_revision_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Omitting ``revision`` falls back to ``get_data_revision()``."""
    monkeypatch.setenv("THAIFIN_CACHE_DIR", str(tmp_path))
    captured: dict[str, str] = {}

    def _spy(repo_id, repo_type, revision, local_dir, allow_patterns, token):
        captured["revision"] = revision
        captured["local_dir"] = local_dir
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        return local_dir

    monkeypatch.setattr("huggingface_hub.snapshot_download", _spy)

    thaifin.set_data_revision("pin-from-test")
    try:
        download_dataset()
    finally:
        from thaifin.data.revision import reset_data_revision

        reset_data_revision()

    assert captured["revision"] == "pin-from-test"
    assert captured["local_dir"].endswith("pin-from-test")


def test_default_cache_root_picks_up_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THAIFIN_CACHE_DIR", "/tmp/thaifin-test")
    assert download_module._default_cache_root() == Path("/tmp/thaifin-test")
    monkeypatch.delenv("THAIFIN_CACHE_DIR")
    assert download_module._default_cache_root() == Path.home() / ".cache" / "thaifin"
