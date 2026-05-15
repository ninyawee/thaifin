"""Atomic publish of a thaifin dataset revision to HuggingFace.

Slice #18 of PRD #11. Uploads every parquet under ``--in-dir`` to the HF
dataset in a SINGLE commit (so consumers never see a half-uploaded state),
then creates a git tag ``--revision`` pointing at that commit.

Atomicity strategy:
    HfApi.upload_folder() with a single commit_message creates ONE commit
    on the main branch — there's no intermediate state where some files
    have updated and others haven't. If the upload fails partway through,
    HF rejects the whole commit. After the commit lands, we tag it.

    If tagging fails (e.g. tag already exists from a re-run), we delete the
    stale tag and re-create it — the commit on main is the source of truth.

Usage::

    python scripts/publish_revision.py \
        --in-dir final/ \
        --revision 2026.05

Required env:
    HF_TOKEN — write-scoped token for the dataset repo.

The script is idempotent: re-running with the same revision tag will
re-upload (HF deduplicates by content hash) and recreate the tag.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

DEFAULT_HF_REPO_ID = "ninyawee/thaifin-financials"

# Only upload parquet files. README/concepts.csv are committed in the source
# repo; the parquet bundle is the redistributable artifact.
DEFAULT_ALLOW_PATTERNS = ["*.parquet"]


def _require_token() -> str:
    """Read HF_TOKEN from env. Never log or echo the value."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "HF_TOKEN is not set. Run via `fnox exec -- ...` locally, or "
            "ensure the workflow exposes secrets.HF_TOKEN as the HF_TOKEN env."
        )
    return token


def upload_folder(
    api: HfApi,
    in_dir: Path,
    repo_id: str,
    revision_tag: str,
    allow_patterns: list[str],
) -> str:
    """Upload all parquets in ``in_dir`` as a single commit on main.

    Returns the commit SHA created on main. Does NOT tag — that's a
    separate step so we can roll back the tag without rolling back the
    commit (or vice versa) if needed.
    """
    if not in_dir.exists():
        raise FileNotFoundError(f"in_dir does not exist: {in_dir}")
    if not in_dir.is_dir():
        raise NotADirectoryError(f"in_dir is not a directory: {in_dir}")

    matches = []
    for pat in allow_patterns:
        matches.extend(in_dir.glob(pat))
    if not matches:
        raise FileNotFoundError(
            f"No files matching {allow_patterns} in {in_dir} — refusing to "
            f"publish an empty revision."
        )

    commit_info = api.upload_folder(
        folder_path=str(in_dir),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Publish revision {revision_tag}",
        commit_description=(
            f"Automated publish from data-build.yml.\n\n"
            f"Files: {', '.join(sorted(p.name for p in matches))}"
        ),
        allow_patterns=allow_patterns,
    )
    # commit_info is a CommitInfo object on newer huggingface_hub; older
    # releases return a URL string. Handle both.
    sha = getattr(commit_info, "oid", None) or str(commit_info)
    return sha


def tag_revision(
    api: HfApi,
    repo_id: str,
    revision_tag: str,
    sha: str | None = None,
) -> None:
    """Create (or recreate) a tag at the latest commit.

    HF doesn't allow creating a tag that already exists, so on re-run we
    delete first. The dataset repo's main branch is the source of truth;
    tags are just convenient pointers.
    """
    try:
        api.delete_tag(repo_id=repo_id, tag=revision_tag, repo_type="dataset")
    except (HfHubHTTPError, Exception):  # noqa: BLE001 - tag may not exist
        pass
    api.create_tag(
        repo_id=repo_id,
        tag=revision_tag,
        repo_type="dataset",
        revision=sha,  # None → tag latest commit on main
        tag_message=f"Revision {revision_tag}",
    )


def publish(
    in_dir: Path,
    revision: str,
    repo_id: str = DEFAULT_HF_REPO_ID,
    allow_patterns: list[str] | None = None,
    api: HfApi | None = None,
) -> str:
    """High-level publish: upload then tag. Returns the commit SHA.

    ``api`` is injectable for testing; in production we construct one with
    the HF_TOKEN from env.
    """
    patterns = allow_patterns or DEFAULT_ALLOW_PATTERNS
    api = api or HfApi(token=_require_token())
    sha = upload_folder(api, in_dir, repo_id, revision, patterns)
    tag_revision(api, repo_id, revision, sha)
    return sha


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Atomic HF publish + revision tag for thaifin dataset."
    )
    p.add_argument(
        "--in-dir",
        type=Path,
        required=True,
        help="Directory containing the final/<table>.parquet files.",
    )
    p.add_argument(
        "--revision",
        required=True,
        help="Revision tag to create (e.g. '2026.05').",
    )
    p.add_argument(
        "--repo-id",
        default=DEFAULT_HF_REPO_ID,
        help=f"HF dataset repo id (default: {DEFAULT_HF_REPO_ID}).",
    )
    p.add_argument(
        "--allow-pattern",
        action="append",
        default=None,
        help=(
            "Glob pattern(s) for files to upload, repeatable. "
            f"Default: {DEFAULT_ALLOW_PATTERNS}."
        ),
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    sha = publish(
        in_dir=args.in_dir,
        revision=args.revision,
        repo_id=args.repo_id,
        allow_patterns=args.allow_pattern,
    )
    print(
        f"Published {args.in_dir} to {args.repo_id} @ {args.revision} "
        f"(commit {sha[:8] if sha else '?'})."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
