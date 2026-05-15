"""Unit tests for ``scripts/publish_revision.py``.

Mocks ``huggingface_hub.HfApi`` so we can verify the upload + tag call
shapes without touching the real HF service. Network IO and credentials
are never used here.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from scripts import publish_revision


def _make_final_dir(tmp_path: Path) -> Path:
    """Build a `final/` dir with a couple of dummy parquet files."""
    final = tmp_path / "final"
    final.mkdir()
    # Real parquet bytes are not required — upload_folder is mocked. We
    # write small files just so the existence + glob check succeeds.
    (final / "financial_lines.parquet").write_bytes(b"dummy-parquet-1")
    (final / "concepts.parquet").write_bytes(b"dummy-parquet-2")
    (final / "auditor_reports.parquet").write_bytes(b"dummy-parquet-3")
    # A non-parquet file that should be filtered by allow_patterns.
    (final / "README.md").write_text("not uploaded")
    return final


def _fake_api() -> MagicMock:
    api = MagicMock()
    api.upload_folder.return_value = SimpleNamespace(oid="abc123def456")
    api.create_tag.return_value = None
    api.delete_tag.return_value = None
    return api


def test_upload_folder_passes_correct_args(tmp_path: Path) -> None:
    final = _make_final_dir(tmp_path)
    api = _fake_api()

    sha = publish_revision.upload_folder(
        api,
        in_dir=final,
        repo_id="ninyawee/thaifin-financials",
        revision_tag="2026.05",
        allow_patterns=["*.parquet"],
    )

    assert sha == "abc123def456"
    api.upload_folder.assert_called_once()
    kwargs = api.upload_folder.call_args.kwargs
    assert kwargs["folder_path"] == str(final)
    assert kwargs["repo_id"] == "ninyawee/thaifin-financials"
    assert kwargs["repo_type"] == "dataset"
    assert kwargs["allow_patterns"] == ["*.parquet"]
    assert "2026.05" in kwargs["commit_message"]


def test_upload_folder_refuses_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="No files matching"):
        publish_revision.upload_folder(
            _fake_api(),
            in_dir=empty,
            repo_id="x/y",
            revision_tag="2026.05",
            allow_patterns=["*.parquet"],
        )


def test_upload_folder_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        publish_revision.upload_folder(
            _fake_api(),
            in_dir=tmp_path / "does-not-exist",
            repo_id="x/y",
            revision_tag="2026.05",
            allow_patterns=["*.parquet"],
        )


def test_tag_revision_creates_tag_after_deleting_stale() -> None:
    api = _fake_api()
    publish_revision.tag_revision(api, "x/y", "2026.05", sha="abc")
    api.delete_tag.assert_called_once_with(
        repo_id="x/y", tag="2026.05", repo_type="dataset"
    )
    api.create_tag.assert_called_once()
    kwargs = api.create_tag.call_args.kwargs
    assert kwargs["repo_id"] == "x/y"
    assert kwargs["tag"] == "2026.05"
    assert kwargs["repo_type"] == "dataset"
    assert kwargs["revision"] == "abc"


def test_tag_revision_tolerates_missing_existing_tag() -> None:
    """delete_tag failures (tag doesn't exist) must not abort tag creation."""
    api = _fake_api()
    api.delete_tag.side_effect = Exception("404 tag not found")
    # Should NOT raise.
    publish_revision.tag_revision(api, "x/y", "2026.05", sha=None)
    api.create_tag.assert_called_once()


def test_publish_high_level_calls_both_steps(tmp_path: Path) -> None:
    final = _make_final_dir(tmp_path)
    api = _fake_api()

    sha = publish_revision.publish(
        in_dir=final,
        revision="2026.05",
        repo_id="ninyawee/thaifin-financials",
        api=api,
    )

    assert sha == "abc123def456"
    api.upload_folder.assert_called_once()
    # Tag flow: delete_tag (best effort) then create_tag.
    api.delete_tag.assert_called_once()
    api.create_tag.assert_called_once()


def test_require_token_raises_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        publish_revision._require_token()


def test_require_token_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test_token_xxx")
    assert publish_revision._require_token() == "hf_test_token_xxx"


def test_main_invokes_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end CLI test, with the high-level publish() patched."""
    final = _make_final_dir(tmp_path)

    captured = {}

    def fake_publish(**kwargs):
        captured.update(kwargs)
        return "deadbeef0000"

    monkeypatch.setattr(publish_revision, "publish", fake_publish)

    rc = publish_revision.main(
        [
            "--in-dir",
            str(final),
            "--revision",
            "2026.05",
            "--repo-id",
            "test/repo",
        ]
    )
    assert rc == 0
    assert captured["in_dir"] == final
    assert captured["revision"] == "2026.05"
    assert captured["repo_id"] == "test/repo"
