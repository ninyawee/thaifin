"""Shared test config: ensure top-level ``scripts/`` is importable.

The repo's ``scripts/`` dir holds CLI entry points (tracer, aggregator,
coverage gate, publisher). Tests import them as ``from scripts.X import Y``.
Pytest auto-adds ``tests/`` to sys.path but not the repo root, so we add
it here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
