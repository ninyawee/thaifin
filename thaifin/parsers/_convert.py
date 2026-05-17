"""Magic-byte sniffing + libreoffice fallback shared by parsers.

SEC IDISC filings name documents ``FOO.XLS`` / ``FOO.DOC`` regardless of
whether the bytes are legacy Microsoft CFB (``\\xD0\\xCF\\x11\\xE0``) or
modern OOXML (``PK\\x03\\x04``). We sniff the first four bytes and either
load directly or shell out to libreoffice.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

OOXML_MAGIC = b"PK\x03\x04"
CFB_MAGIC = b"\xD0\xCF\x11\xE0"


class LibreOfficeMissingError(RuntimeError):
    """Raised when a legacy file needs libreoffice but it's not installed."""


def _libreoffice_binary() -> str:
    for name in ("libreoffice", "soffice"):
        path = shutil.which(name)
        if path:
            return path
    raise LibreOfficeMissingError(
        "libreoffice (or soffice) is required to convert legacy Microsoft "
        "CFB documents but was not found on PATH. Install LibreOffice "
        "(`apt install libreoffice` or `brew install --cask libreoffice`)."
    )


def detect_format(data: bytes) -> str:
    """Return ``'ooxml'``, ``'cfb'``, or ``'unknown'`` based on magic bytes."""
    head = data[:4]
    if head[:2] == b"PK":
        return "ooxml"
    if head == CFB_MAGIC:
        return "cfb"
    return "unknown"


def _convert_via_libreoffice(
    src: Path, target_ext: str, out_dir: Path
) -> Path:
    """Run libreoffice headless to convert ``src`` to ``target_ext``.

    Returns the converted file path. Raises on conversion failure.
    """
    binary = _libreoffice_binary()
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            binary,
            "--headless",
            "--convert-to",
            target_ext,
            "--outdir",
            str(out_dir),
            str(src),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"libreoffice conversion of {src} to {target_ext} failed "
            f"(exit {proc.returncode}): {proc.stderr.strip()}"
        )
    target = out_dir / (src.stem + "." + target_ext)
    if not target.exists():
        raise RuntimeError(
            f"libreoffice reported success but {target} is missing"
        )
    return target


def ensure_xlsx(data: bytes, work_dir: Path, stem: str = "financial") -> Path:
    """Materialise ``data`` as a valid ``.xlsx`` on disk.

    OOXML inputs are dropped straight to disk under the right extension.
    CFB inputs are written to ``stem.xls`` then converted via libreoffice.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    fmt = detect_format(data)
    if fmt == "ooxml":
        out = work_dir / f"{stem}.xlsx"
        out.write_bytes(data)
        return out
    if fmt == "cfb":
        legacy = work_dir / f"{stem}.xls"
        legacy.write_bytes(data)
        return _convert_via_libreoffice(legacy, "xlsx", work_dir)
    raise ValueError(
        f"Unrecognised XLS format: magic bytes {data[:4]!r} "
        "(expected PK… for OOXML or D0 CF 11 E0 for CFB)"
    )


def ensure_docx(data: bytes, work_dir: Path, stem: str = "doc") -> Path:
    """Materialise ``data`` as a valid ``.docx`` on disk.

    OOXML inputs are dropped straight to disk under the right extension.
    CFB inputs are written to ``stem.doc`` then converted via libreoffice.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    fmt = detect_format(data)
    if fmt == "ooxml":
        out = work_dir / f"{stem}.docx"
        out.write_bytes(data)
        return out
    if fmt == "cfb":
        legacy = work_dir / f"{stem}.doc"
        legacy.write_bytes(data)
        return _convert_via_libreoffice(legacy, "docx", work_dir)
    raise ValueError(
        f"Unrecognised DOC format: magic bytes {data[:4]!r}"
    )
