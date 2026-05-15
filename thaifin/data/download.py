"""Offline-mode helper: bulk-fetch a dataset revision to local disk.

After ``download_dataset(revision="2026.05")`` returns, subsequent
``DatasetClient`` calls for the same revision route to the on-disk
parquet (no HTTP), so the library works with the network disabled.
"""

from __future__ import annotations

import os
from pathlib import Path

from thaifin.data.client import DATASET_REPO
from thaifin.data.revision import get_data_revision


def _default_cache_root() -> Path:
    """Resolve the cache root, honoring ``THAIFIN_CACHE_DIR`` if set."""
    override = os.environ.get("THAIFIN_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "thaifin"


def cache_dir_for(revision: str, cache_dir: Path | None = None) -> Path:
    """Return the on-disk directory used to mirror ``revision``.

    Used by :class:`DatasetClient` to locate a previously-downloaded
    revision without re-running the HF download.
    """
    root = Path(cache_dir).expanduser() if cache_dir is not None else _default_cache_root()
    return root / revision


def download_dataset(
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Mirror an HF dataset revision to local disk and return its path.

    Args:
        revision: HF dataset revision (tag/branch/sha). Defaults to the
            currently-active revision (see :func:`get_data_revision`).
        cache_dir: Override the cache root. Defaults to ``$THAIFIN_CACHE_DIR``
            if set, else ``~/.cache/thaifin``. The returned path is
            ``<cache_dir>/<revision>/`` regardless.

    Returns:
        Local directory containing the downloaded parquet files.

    Notes:
        - Uses ``HF_TOKEN`` from the environment when present; the public
          dataset works without one.
        - Imports ``huggingface_hub`` lazily so the rest of the library is
          usable even if the user hasn't installed it.
    """
    rev = revision if revision is not None else get_data_revision()
    target = cache_dir_for(rev, cache_dir)
    target.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    token = os.environ.get("HF_TOKEN")
    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        revision=rev,
        local_dir=str(target),
        allow_patterns=["*.parquet"],
        token=token,
    )
    return target
