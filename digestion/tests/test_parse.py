"""Unit tests for _parse_obligations. No Lean / LeanDojo required."""
import sys
import unittest.mock as mock

for _m in [
    "lean_dojo_v2", "lean_dojo_v2.lean_dojo",
    "lean_dojo_v2.lean_dojo.data_extraction",
    "lean_dojo_v2.lean_dojo.data_extraction.ast",
    "lean_dojo_v2.lean_dojo.data_extraction.traced_data",
    "lean_dojo_v2.lean_dojo.data_extraction.trace",
]:
    sys.modules.setdefault(_m, mock.MagicMock())

from digestion.extractor import _parse_obligations  # noqa: E402


def test_empty_string():
    assert _parse_obligations("") == []


def test_no_goals():
    assert _parse_obligations("no goals") == []
    assert _parse_obligations("  no goals  ") == []


def test_single_goal_no_hyps():
    r = _parse_obligations("⊢ True")
    assert len(r) == 1
    assert r[0].goal == "True"
    assert r[0].hypotheses == []


def test_single_goal_with_hyps():
    state = "h : Nat\n⊢ h > 0"
    r = _parse_obligations(state)
    assert len(r) == 1
    assert r[0].goal == "h > 0"
    assert len(r[0].hypotheses) == 1
    assert r[0].hypotheses[0].name == "h"
    assert r[0].hypotheses[0].type == "Nat"


def test_multiple_hyps():
    state = "h1 : Nat\nh2 : h1 > 0\n⊢ h1 ≠ 0"
    r = _parse_obligations(state)
    assert len(r) == 1
    assert r[0].goal == "h1 ≠ 0"
    assert [h.name for h in r[0].hypotheses] == ["h1", "h2"]
    assert r[0].hypotheses[1].type == "h1 > 0"


def test_two_goals():
    state = "h1 : P\n⊢ P\n\nh2 : Q\n⊢ Q"
    r = _parse_obligations(state)
    assert len(r) == 2
    assert r[0].goal == "P"
    assert r[0].hypotheses[0].name == "h1"
    assert r[1].goal == "Q"
    assert r[1].hypotheses[0].name == "h2"


def test_goal_with_unicode():
    state = "α : Type\n⊢ α → α"
    r = _parse_obligations(state)
    assert len(r) == 1
    assert r[0].goal == "α → α"
    assert r[0].hypotheses[0].name == "α"


def test_induction_step_with_ih():
    # IH contains nested " : " inside quantifiers; partition must split only at the first one.
    # "n1 n2 : ℕ" is a multi-var declaration: parser yields a single hypothesis with name "n1 n2".
    state = (
        "n : ℕ\n"
        "ih : ∀ m < n, ∀ (l : PairList), len_pairlist l = m → Even m\n"
        "n1 n2 : ℕ\n"
        "l2 : PairList\n"
        "hl : len_pairlist l2 + 2 = n\n"
        "⊢ Even n"
    )
    r = _parse_obligations(state)
    assert len(r) == 1
    obl = r[0]
    assert obl.goal == "Even n"
    assert len(obl.hypotheses) == 6
    assert [h.name for h in obl.hypotheses] == ["n", "ih", "n1", "n2", "l2", "hl"]
    assert obl.hypotheses[1].type == "∀ m < n, ∀ (l : PairList), len_pairlist l = m → Even m"
    assert obl.hypotheses[2].type == "ℕ"
    assert obl.hypotheses[3].type == "ℕ"
    assert obl.hypotheses[5].type == "len_pairlist l2 + 2 = n"


def test_subtype_hypothesis():
    # E1: hypothesis whose type contains " : " inside braces — partition must not split there.
    state = "h : { x : α // P x }\n⊢ ∃ y, y ∈ h.val"
    r = _parse_obligations(state)
    assert len(r) == 1
    assert r[0].hypotheses[0].name == "h"
    assert r[0].hypotheses[0].type == "{ x : α // P x }"
    assert r[0].goal == "∃ y, y ∈ h.val"


def test_let_bound_hypothesis_strips_value():
    # `have h' : T := <value>` and `have h' : T :=` (truncated value) both surface in
    # Lean's pretty-printer; only the type should survive into our Hypothesis.
    state = (
        "h' : xs.length = ys.length := by simp\n"
        "hbig : Nat :=\n"
        "⊢ True"
    )
    r = _parse_obligations(state)
    assert len(r) == 1
    assert [h.name for h in r[0].hypotheses] == ["h'", "hbig"]
    assert r[0].hypotheses[0].type == "xs.length = ys.length"
    assert r[0].hypotheses[1].type == "Nat"


def test_list_map_drop_ih():
    # Universe-polymorphic type, function type with →, IH with qualified dotted names.
    # The IH type also contains " : " inside its quantifier binder.
    state = (
        "α : Type u_1\n"
        "f : α → α\n"
        "x : α\n"
        "xs : List α\n"
        "ih : ∀ (n : ℕ), List.drop n (List.map f xs) = List.map f (List.drop n xs)\n"
        "⊢ List.drop 0 (List.map f (x :: xs)) = List.map f (List.drop 0 (x :: xs))"
    )
    r = _parse_obligations(state)
    assert len(r) == 1
    obl = r[0]
    assert obl.goal == "List.drop 0 (List.map f (x :: xs)) = List.map f (List.drop 0 (x :: xs))"
    assert len(obl.hypotheses) == 5
    assert [h.name for h in obl.hypotheses] == ["α", "f", "x", "xs", "ih"]
    assert obl.hypotheses[0].type == "Type u_1"
    assert obl.hypotheses[1].type == "α → α"
    assert obl.hypotheses[4].type == "∀ (n : ℕ), List.drop n (List.map f xs) = List.map f (List.drop n xs)"
