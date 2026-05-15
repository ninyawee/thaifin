"""Tests for ``thaifin.concepts`` (ConceptMapper).

Covers:
- canonical label match
- alias match
- statement-scoped matching (cross-statement collisions are NOT joined)
- whitespace normalisation
- unmapped rows preserve ``concept = None``
- the real ``data/concepts.csv`` parses cleanly
"""

from __future__ import annotations

from pathlib import Path

import pytest

from thaifin.concepts import (
    ConceptEntry,
    apply_concepts,
    build_lookup,
    coverage,
    load_concepts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONCEPTS_CSV = REPO_ROOT / "data" / "concepts.csv"


@pytest.fixture
def synth_dictionary() -> list[ConceptEntry]:
    return [
        ConceptEntry(
            concept="revenue",
            statement="IS",
            label_en="Revenue",
            label_th="รายได้จากการขายและการให้บริการ",
            aliases_th=("รายได้รวม",),
            xbrl_ref="ifrs-full:Revenue",
        ),
        ConceptEntry(
            concept="cash",
            statement="BS",
            label_en="Cash",
            label_th="เงินสดและรายการเทียบเท่าเงินสด",
            aliases_th=(),
            xbrl_ref=None,
        ),
        # Same Thai label "X" appears in both BS and CF — the mapper must
        # respect the statement scope so there's no cross-statement leak.
        ConceptEntry(
            concept="bs_x",
            statement="BS",
            label_en="X-on-BS",
            label_th="X",
            aliases_th=(),
            xbrl_ref=None,
        ),
        ConceptEntry(
            concept="cf_x",
            statement="CF",
            label_en="X-on-CF",
            label_th="X",
            aliases_th=(),
            xbrl_ref=None,
        ),
    ]


def test_canonical_label_matches(synth_dictionary):
    rows = [
        {"statement": "IS", "raw_label_th": "รายได้จากการขายและการให้บริการ"},
    ]
    out = apply_concepts(rows, synth_dictionary)
    assert out[0]["concept"] == "revenue"


def test_alias_matches(synth_dictionary):
    rows = [{"statement": "IS", "raw_label_th": "รายได้รวม"}]
    out = apply_concepts(rows, synth_dictionary)
    assert out[0]["concept"] == "revenue"


def test_unmapped_keeps_none(synth_dictionary):
    rows = [{"statement": "BS", "raw_label_th": "ไม่มีในพจนานุกรม"}]
    out = apply_concepts(rows, synth_dictionary)
    assert out[0]["concept"] is None


def test_statement_scope_isolates_collisions(synth_dictionary):
    rows = [
        {"statement": "BS", "raw_label_th": "X"},
        {"statement": "CF", "raw_label_th": "X"},
        {"statement": "IS", "raw_label_th": "X"},  # not in dict for IS
    ]
    out = apply_concepts(rows, synth_dictionary)
    assert out[0]["concept"] == "bs_x"
    assert out[1]["concept"] == "cf_x"
    assert out[2]["concept"] is None


def test_whitespace_normalised_match(synth_dictionary):
    rows = [
        {
            "statement": "BS",
            "raw_label_th": "  เงินสดและรายการเทียบเท่าเงินสด  ",
        }
    ]
    out = apply_concepts(rows, synth_dictionary)
    assert out[0]["concept"] == "cash"


def test_apply_concepts_does_not_mutate_input(synth_dictionary):
    rows = [{"statement": "IS", "raw_label_th": "รายได้รวม", "value": 10}]
    out = apply_concepts(rows, synth_dictionary)
    assert "concept" not in rows[0]
    assert out[0]["value"] == 10
    assert out[0] is not rows[0]


def test_build_lookup_keys(synth_dictionary):
    lookup = build_lookup(synth_dictionary)
    assert lookup[("IS", "รายได้จากการขายและการให้บริการ")] == "revenue"
    assert lookup[("IS", "รายได้รวม")] == "revenue"
    assert lookup[("BS", "X")] == "bs_x"
    assert lookup[("CF", "X")] == "cf_x"


def test_coverage_helper(synth_dictionary):
    rows = [
        {"statement": "IS", "raw_label_th": "รายได้รวม"},
        {"statement": "IS", "raw_label_th": "ไม่ตรง"},
        {"statement": "IS", "raw_label_th": "รายได้จากการขายและการให้บริการ"},
    ]
    out = apply_concepts(rows, synth_dictionary)
    mapped, total, ratio = coverage(out)
    assert mapped == 2
    assert total == 3
    assert pytest.approx(ratio) == 2 / 3


# --- Real concepts.csv smoke check ----------------------------------------


def test_real_csv_loads():
    entries = load_concepts(CONCEPTS_CSV)
    assert len(entries) >= 26
    statements = {e.statement for e in entries}
    assert statements <= {"BS", "IS", "CF", "EQ"}
    # No duplicate concept IDs.
    ids = [e.concept for e in entries]
    assert len(ids) == len(set(ids))


def test_real_csv_has_capex_anchor():
    entries = load_concepts(CONCEPTS_CSV)
    capex = [e for e in entries if e.concept == "capex"]
    assert len(capex) == 1
    assert capex[0].statement == "CF"
    assert "เงินสดจ่าย" in capex[0].label_th
