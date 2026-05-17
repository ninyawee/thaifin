"""Format normalization for legacy SEC IDISC filing files.

A SEC IDISC filing zip contains files named ``FINANCIAL_STATEMENTS.XLS``,
``NOTES.DOC``, and ``AUDITOR_REPORT.DOC``. The extension is misleading —
the file may actually be:

1. **OOXML disguised as ``.XLS`` / ``.DOC``** (modern filings, post-~2024)
   Magic bytes ``PK\\x03\\x04``. We just rename to ``.xlsx``/``.docx``.

2. **True legacy binary** (``.xls`` BIFF or ``.doc`` CFB)
   Magic bytes ``\\xD0\\xCF\\x11\\xE0`` (CFB / OLE2). Need libreoffice.

3. **Already-OOXML** (rare; ``.xlsx``/``.docx`` extension). Copy as-is.

The downstream parser sees only OOXML files. This module isolates the
shell-out to libreoffice so the rest of the pipeline stays pure-python.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

LIBREOFFICE_CMD = "libreoffice"
LIBREOFFICE_TIMEOUT_SEC = 30
LIBREOFFICE_INSTALL_HINT = (
    "libreoffice is required to normalize legacy .XLS/.DOC files.\n"
    "Install it on Debian/Ubuntu:  sudo apt-get install -y libreoffice\n"
    "Install it on macOS:          brew install --cask libreoffice\n"
    "Then ensure `libreoffice` is on PATH."
)

# Magic bytes
_OOXML_MAGIC = b"PK\x03\x04"  # zip-based formats: xlsx, docx
_CFB_MAGIC = b"\xd0\xcf\x11\xe0"  # OLE2 / CFB: legacy xls, doc

# File-shape labels surfaced by ``classify_input``. Used by coverage
# reporting in ``backfill.py`` so a normalization failure can be
# attributed to the right input variant.
SHAPE_OOXML = "ooxml"
SHAPE_LEGACY_BINARY = "legacy_binary"
SHAPE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of one normalization."""

    input_path: Path
    output_path: Path
    input_shape: str
    used_libreoffice: bool


class NormalizationError(RuntimeError):
    """Raised when a file cannot be normalized to OOXML."""


class LibreOfficeMissingError(NormalizationError):
    """Raised when libreoffice is required but not on PATH."""


def requires_libreoffice() -> bool:
    """Return True iff the libreoffice binary is on PATH."""
    return shutil.which(LIBREOFFICE_CMD) is not None


def _read_magic(path: Path, n: int = 8) -> bytes:
    """Read the first ``n`` bytes of ``path``; tolerate short files."""
    with path.open("rb") as fh:
        return fh.read(n)


def classify_input(path: Path) -> str:
    """Inspect magic bytes and return one of the ``SHAPE_*`` constants.

    Decides routing in ``normalize_to_ooxml``: ``SHAPE_OOXML`` skips
    libreoffice; ``SHAPE_LEGACY_BINARY`` requires it; ``SHAPE_UNKNOWN``
    falls back to libreoffice with a warning trail.
    """
    head = _read_magic(path)
    if head.startswith(_OOXML_MAGIC):
        return SHAPE_OOXML
    if head.startswith(_CFB_MAGIC):
        return SHAPE_LEGACY_BINARY
    return SHAPE_UNKNOWN


def _target_extension(input_path: Path) -> str:
    """Pick ``.xlsx`` for spreadsheet inputs, ``.docx`` for word inputs.

    Falls back to ``.xlsx`` when the extension is ambiguous — most SEC
    filings are FINANCIAL_STATEMENTS.XLS so this is the safer default.
    """
    suffix = input_path.suffix.lower()
    if suffix in {".doc", ".docx"}:
        return ".docx"
    return ".xlsx"


def normalize_to_ooxml(input_path: Path, out_dir: Path) -> NormalizationResult:
    """Produce an OOXML file in ``out_dir`` for ``input_path``.

    Routing:
      * OOXML magic bytes → copy/rename to OOXML extension
      * CFB magic bytes → libreoffice headless conversion
      * Unknown magic bytes → libreoffice with a single retry
      * Already-OOXML extension (``.xlsx``/``.docx``) → copy as-is

    On libreoffice unavailability, raises ``LibreOfficeMissingError`` with
    actionable install instructions; on conversion failure, raises
    ``NormalizationError`` with stderr context.
    """
    if not input_path.exists():
        raise NormalizationError(f"input file does not exist: {input_path}")
    out_dir.mkdir(parents=True, exist_ok=True)

    target_ext = _target_extension(input_path)
    target_path = out_dir / (input_path.stem + target_ext)

    # Already-OOXML extension: trust it, copy as-is.
    if input_path.suffix.lower() in {".xlsx", ".docx"}:
        if input_path.resolve() != target_path.resolve():
            shutil.copyfile(input_path, target_path)
        return NormalizationResult(
            input_path=input_path,
            output_path=target_path,
            input_shape=SHAPE_OOXML,
            used_libreoffice=False,
        )

    shape = classify_input(input_path)
    if shape == SHAPE_OOXML:
        # Disguised OOXML — just rename.
        shutil.copyfile(input_path, target_path)
        return NormalizationResult(
            input_path=input_path,
            output_path=target_path,
            input_shape=SHAPE_OOXML,
            used_libreoffice=False,
        )

    # Legacy binary or unknown — needs libreoffice.
    if not requires_libreoffice():
        raise LibreOfficeMissingError(LIBREOFFICE_INSTALL_HINT)
    return _convert_with_libreoffice(input_path, out_dir, shape)


def _convert_with_libreoffice(
    input_path: Path, out_dir: Path, shape: str
) -> NormalizationResult:
    """Run libreoffice headless conversion with a single retry on failure.

    libreoffice headless occasionally hangs on a busy machine — guarded
    by a 30 s timeout. One retry, then bubble the error.
    """
    target_ext = _target_extension(input_path)
    convert_to = target_ext.lstrip(".")  # 'xlsx' or 'docx'
    last_err: str | None = None
    for attempt in (1, 2):
        try:
            proc = subprocess.run(
                [
                    LIBREOFFICE_CMD,
                    "--headless",
                    "--convert-to",
                    convert_to,
                    "--outdir",
                    str(out_dir),
                    str(input_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=LIBREOFFICE_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired as exc:
            last_err = f"timeout after {LIBREOFFICE_TIMEOUT_SEC}s (attempt {attempt}): {exc}"
            continue
        if proc.returncode == 0:
            target_path = out_dir / (input_path.stem + target_ext)
            if not target_path.exists():
                last_err = (
                    f"libreoffice returned 0 but {target_path} missing; "
                    f"stdout={proc.stdout!r}"
                )
                continue
            return NormalizationResult(
                input_path=input_path,
                output_path=target_path,
                input_shape=shape,
                used_libreoffice=True,
            )
        last_err = (
            f"libreoffice exit {proc.returncode} (attempt {attempt}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    raise NormalizationError(
        f"libreoffice conversion failed for {input_path}: {last_err}"
    )
