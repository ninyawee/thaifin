"""Tests for ``thaifin.sources.sec_idisc.normalize`` (slice #17).

Two fixture variants exercise the routing:
  * ``disguised_xlsx.XLS`` — OOXML behind a ``.XLS`` extension; pure-python rename
  * ``legacy_binary.XLS``  — true CFB / OLE2; requires libreoffice
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from thaifin.sources.sec_idisc.normalize import (
    SHAPE_LEGACY_BINARY,
    SHAPE_OOXML,
    LibreOfficeMissingError,
    NormalizationError,
    classify_input,
    normalize_to_ooxml,
    requires_libreoffice,
)

SAMPLE_DATA = Path(__file__).parent / "sample_data"
DISGUISED_XLS = SAMPLE_DATA / "disguised_xlsx.XLS"
DISGUISED_DOC = SAMPLE_DATA / "disguised_docx.DOC"
LEGACY_XLS = SAMPLE_DATA / "legacy_binary.XLS"
LEGACY_DOC = SAMPLE_DATA / "legacy_binary.DOC"


@pytest.fixture(autouse=True)
def _check_fixtures_present() -> None:
    for p in (DISGUISED_XLS, DISGUISED_DOC, LEGACY_XLS, LEGACY_DOC):
        if not p.exists():
            pytest.skip(f"missing fixture: {p}")


def test_classify_disguised_ooxml() -> None:
    assert classify_input(DISGUISED_XLS) == SHAPE_OOXML
    assert classify_input(DISGUISED_DOC) == SHAPE_OOXML


def test_classify_legacy_binary() -> None:
    assert classify_input(LEGACY_XLS) == SHAPE_LEGACY_BINARY
    assert classify_input(LEGACY_DOC) == SHAPE_LEGACY_BINARY


def test_normalize_disguised_xls_renames_only(tmp_path: Path) -> None:
    """OOXML-disguised files take the no-libreoffice fast path."""
    result = normalize_to_ooxml(DISGUISED_XLS, tmp_path)
    assert result.input_shape == SHAPE_OOXML
    assert result.used_libreoffice is False
    assert result.output_path.suffix == ".xlsx"
    assert result.output_path.exists()
    # OOXML rename must yield byte-identical content.
    assert (
        result.output_path.read_bytes()[:4] == DISGUISED_XLS.read_bytes()[:4]
    )
    assert result.output_path.stat().st_size == DISGUISED_XLS.stat().st_size


def test_normalize_disguised_doc_renames_only(tmp_path: Path) -> None:
    result = normalize_to_ooxml(DISGUISED_DOC, tmp_path)
    assert result.input_shape == SHAPE_OOXML
    assert result.used_libreoffice is False
    assert result.output_path.suffix == ".docx"
    assert result.output_path.exists()


@pytest.mark.skipif(
    not requires_libreoffice(), reason="libreoffice not installed"
)
def test_normalize_legacy_xls_via_libreoffice(tmp_path: Path) -> None:
    """True legacy CFB needs libreoffice → produces a real .xlsx."""
    # Copy fixture into a writable tmp dir; libreoffice writes alongside.
    src = tmp_path / "in" / LEGACY_XLS.name
    src.parent.mkdir()
    shutil.copyfile(LEGACY_XLS, src)
    out = tmp_path / "out"
    result = normalize_to_ooxml(src, out)
    assert result.used_libreoffice is True
    assert result.input_shape == SHAPE_LEGACY_BINARY
    assert result.output_path.suffix == ".xlsx"
    assert result.output_path.exists()
    # Output must be valid OOXML (zip-based).
    assert result.output_path.read_bytes()[:4] == b"PK\x03\x04"


@pytest.mark.skipif(
    not requires_libreoffice(), reason="libreoffice not installed"
)
def test_normalize_legacy_doc_via_libreoffice(tmp_path: Path) -> None:
    src = tmp_path / "in" / LEGACY_DOC.name
    src.parent.mkdir()
    shutil.copyfile(LEGACY_DOC, src)
    out = tmp_path / "out"
    result = normalize_to_ooxml(src, out)
    assert result.used_libreoffice is True
    assert result.input_shape == SHAPE_LEGACY_BINARY
    assert result.output_path.suffix == ".docx"
    assert result.output_path.read_bytes()[:4] == b"PK\x03\x04"


def test_legacy_without_libreoffice_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When libreoffice is missing, legacy normalization fails loudly."""
    monkeypatch.setattr(
        "thaifin.sources.sec_idisc.normalize.requires_libreoffice",
        lambda: False,
    )
    src = tmp_path / "in" / LEGACY_XLS.name
    src.parent.mkdir()
    shutil.copyfile(LEGACY_XLS, src)
    with pytest.raises(LibreOfficeMissingError):
        normalize_to_ooxml(src, tmp_path / "out")


def test_already_ooxml_extension_copies_as_is(tmp_path: Path) -> None:
    """A pre-normalized .xlsx is just copied to the destination."""
    src = tmp_path / "ALREADY.xlsx"
    src.write_bytes(DISGUISED_XLS.read_bytes())
    out_dir = tmp_path / "out"
    result = normalize_to_ooxml(src, out_dir)
    assert result.used_libreoffice is False
    assert result.output_path == out_dir / "ALREADY.xlsx"
    assert result.output_path.read_bytes() == src.read_bytes()


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(NormalizationError):
        normalize_to_ooxml(tmp_path / "nope.xls", tmp_path / "out")


def test_requires_libreoffice_returns_bool() -> None:
    assert isinstance(requires_libreoffice(), bool)
