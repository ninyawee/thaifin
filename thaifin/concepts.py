"""ConceptMapper — join raw Thai labels to curated concept IDs.

The dictionary lives in :file:`data/concepts.csv`. Reader rules:

- Lines starting with ``#`` are comments and skipped.
- The first non-comment row is the header row.
- Aliases live in the ``aliases_th`` column, pipe-separated.

Match rules (see ``data/README.md`` curation rule #4):

- Same statement only — the join key is ``(statement, label_th)`` so
  ``revenue`` (IS) will never match a balance-sheet row that happens to
  share the Thai label.
- A row matches the canonical ``label_th`` *or* any of its
  ``aliases_th``.
- Whitespace-normalised (collapse runs of whitespace, strip ends) before
  comparison; case-insensitive only for ASCII (Thai is case-less).
- Unmapped rows keep ``concept = None`` — they are *not* dropped.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Whitespace normalisation collapses runs of spaces (incl. NBSP and Thai
# spaces) so labels typed with double-spaces still match. Underscores and
# hyphens are preserved verbatim.
_WS_RE = re.compile(r"\s+", re.UNICODE)


def _normalise(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


@dataclass(frozen=True)
class ConceptEntry:
    """One row of the curated concept dictionary."""

    concept: str
    statement: str
    label_en: str
    label_th: str
    aliases_th: tuple[str, ...]
    xbrl_ref: str | None


def load_concepts(path: Path) -> list[ConceptEntry]:
    """Load ``data/concepts.csv``, skipping comment lines."""
    entries: list[ConceptEntry] = []
    with path.open("r", encoding="utf-8") as f:
        rows = (line for line in f if not line.lstrip().startswith("#"))
        reader = csv.DictReader(rows)
        for row in reader:
            aliases = tuple(
                a.strip()
                for a in (row.get("aliases_th") or "").split("|")
                if a.strip()
            )
            xbrl = row.get("xbrl_ref") or None
            entries.append(
                ConceptEntry(
                    concept=row["concept"].strip(),
                    statement=row["statement"].strip(),
                    label_en=row["label_en"].strip(),
                    label_th=row["label_th"].strip(),
                    aliases_th=aliases,
                    xbrl_ref=xbrl.strip() if xbrl else None,
                )
            )
    return entries


def build_lookup(
    entries: Iterable[ConceptEntry],
) -> dict[tuple[str, str], str]:
    """Build the ``(statement, normalised_label) → concept_id`` lookup.

    Both the canonical ``label_th`` and every alias produce a key. If two
    entries collide on the same key (shouldn't happen if the CSV is
    well-formed) the later-loaded entry wins, but we don't enforce — that's
    the validation test's job.
    """
    out: dict[tuple[str, str], str] = {}
    for entry in entries:
        keys = [entry.label_th, *entry.aliases_th]
        for raw in keys:
            normalised = _normalise(raw)
            if not normalised:
                continue
            out[(entry.statement, normalised)] = entry.concept
    return out


def apply_concepts(
    rows: Iterable[dict],
    dictionary: list[ConceptEntry] | dict[tuple[str, str], str],
) -> list[dict]:
    """Tag each row with its concept (None if no match).

    ``rows`` items must have at least ``statement`` and ``raw_label_th``;
    every other column is preserved verbatim. The function does not
    mutate inputs — each output row is a fresh dict.
    """
    if isinstance(dictionary, list):
        lookup = build_lookup(dictionary)
    else:
        lookup = dictionary

    out: list[dict] = []
    for row in rows:
        statement = row.get("statement")
        raw_label = row.get("raw_label_th") or ""
        key = (statement, _normalise(raw_label))
        new = dict(row)
        new["concept"] = lookup.get(key)
        out.append(new)
    return out


def coverage(rows: Iterable[dict]) -> tuple[int, int, float]:
    """``(mapped, total, ratio)`` over the iterable.

    ``ratio`` is ``mapped / total`` or 0 when ``total == 0``.
    """
    total = 0
    mapped = 0
    for row in rows:
        total += 1
        if row.get("concept"):
            mapped += 1
    return mapped, total, (mapped / total if total else 0.0)


__all__ = [
    "ConceptEntry",
    "apply_concepts",
    "build_lookup",
    "coverage",
    "load_concepts",
]
