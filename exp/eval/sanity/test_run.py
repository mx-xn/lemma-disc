"""Tests for the pure helper functions in run.py."""
from exp.lib.corpus import Theorem
from exp.eval.sanity.run import build_comparison, filter_by_ids, filter_theorems


def _thm(theorem_id: str) -> Theorem:
    return Theorem(theorem_id=theorem_id, lean_path="", statement_text="x = x")


# ---------------------------------------------------------------------------
# filter_by_ids
# ---------------------------------------------------------------------------

def test_filter_by_ids_subset():
    theorems = [_thm("prop_29"), _thm("prop_36"), _thm("prop_55")]
    result = filter_by_ids(theorems, ["prop_29", "prop_55"])
    assert [t.theorem_id for t in result] == ["prop_29", "prop_55"]


def test_filter_by_ids_preserves_order():
    theorems = [_thm("prop_85"), _thm("prop_29"), _thm("prop_77")]
    result = filter_by_ids(theorems, ["prop_77", "prop_29"])
    assert [t.theorem_id for t in result] == ["prop_29", "prop_77"]


def test_filter_by_ids_none_returns_all():
    theorems = [_thm("prop_29"), _thm("prop_36")]
    assert filter_by_ids(theorems, None) == theorems


def test_filter_by_ids_empty_list_returns_all():
    theorems = [_thm("prop_29"), _thm("prop_36")]
    assert filter_by_ids(theorems, []) == theorems


def test_filter_by_ids_unknown_id_ignored():
    theorems = [_thm("prop_29")]
    result = filter_by_ids(theorems, ["prop_29", "prop_999"])
    assert [t.theorem_id for t in result] == ["prop_29"]


def test_filter_by_ids_no_match_returns_empty():
    theorems = [_thm("prop_29"), _thm("prop_36")]
    assert filter_by_ids(theorems, ["prop_999"]) == []


# ---------------------------------------------------------------------------
# filter_theorems
# ---------------------------------------------------------------------------

def test_filter_keeps_matching():
    theorems = [_thm("prop_29"), _thm("prop_36"), _thm("prop_14")]
    lemma_dict = {"29": ["stmt1"], "36": ["stmt2"]}
    result = filter_theorems(theorems, lemma_dict)
    assert [t.theorem_id for t in result] == ["prop_29", "prop_36"]


def test_filter_no_match():
    theorems = [_thm("prop_14"), _thm("prop_30")]
    assert filter_theorems(theorems, {"29": ["s"]}) == []


def test_filter_preserves_order():
    ids = ["prop_85", "prop_29", "prop_77"]
    theorems = [_thm(i) for i in ids]
    lemma_dict = {"85": [], "29": [], "77": []}
    result = filter_theorems(theorems, lemma_dict)
    assert [t.theorem_id for t in result] == ids


def test_filter_ignores_non_prop_ids():
    # theorem IDs that don't match 'prop_N' should never appear in results
    theorems = [_thm("theorem_1"), _thm("prop_29")]
    lemma_dict = {"1": ["s"], "29": ["s"]}
    result = filter_theorems(theorems, lemma_dict)
    assert [t.theorem_id for t in result] == ["prop_29"]


# ---------------------------------------------------------------------------
# build_comparison
# ---------------------------------------------------------------------------

def test_build_comparison_counts():
    baseline = {"prop_29": False, "prop_36": True, "prop_55": False}
    with_lemma = {"prop_29": True, "prop_36": True, "prop_55": False}
    result = build_comparison(baseline, with_lemma, lemma_pool_size=10)
    assert result["total_theorems"] == 3
    assert result["lemma_pool_size"] == 10
    assert result["without_lemmas"] == {"solved": 1, "failed": 2}
    assert result["with_lemmas"] == {"solved": 2, "failed": 1}


def test_build_comparison_per_theorem():
    baseline = {"prop_29": False}
    with_lemma = {"prop_29": True}
    result = build_comparison(baseline, with_lemma, lemma_pool_size=5)
    assert result["per_theorem"]["prop_29"] == {
        "without_lemmas": False,
        "with_lemmas": True,
    }


def test_build_comparison_theorem_ids_sorted():
    baseline = {"prop_77": True, "prop_29": False}
    with_lemma = {"prop_77": True, "prop_29": True}
    result = build_comparison(baseline, with_lemma, lemma_pool_size=0)
    assert list(result["per_theorem"].keys()) == ["prop_29", "prop_77"]
