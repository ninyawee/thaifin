"""Process-wide active dataset revision.

The library reads from one HF dataset revision at a time. Users can pin
that revision via :func:`set_data_revision`; new ``Stock`` instances
created without an explicit ``revision=`` argument fall back to
:func:`get_data_revision`.
"""

from __future__ import annotations

DEFAULT_REVISION: str = "main"

_ACTIVE_REVISION: str = DEFAULT_REVISION


def set_data_revision(revision: str) -> None:
    """Pin the active HF dataset revision for subsequent reads.

    The pin is process-global. Per-instance overrides via
    ``Stock(..., revision=...)`` still win.
    """
    global _ACTIVE_REVISION
    if not isinstance(revision, str) or not revision:
        raise ValueError("revision must be a non-empty string")
    _ACTIVE_REVISION = revision


def get_data_revision() -> str:
    """Return the currently active HF dataset revision."""
    return _ACTIVE_REVISION


def reset_data_revision() -> None:
    """Restore the active revision to :data:`DEFAULT_REVISION`. For tests."""
    global _ACTIVE_REVISION
    _ACTIVE_REVISION = DEFAULT_REVISION
