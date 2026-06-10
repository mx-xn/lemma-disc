"""Unit tests for _compute_U and _compute_pi. No Lean / LeanDojo required."""
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

from digestion.extractor import _compute_U, _compute_pi  # noqa: E402
from digestion.models import Hypothesis  # noqa: E402


# ── _compute_U ──────────────────────────────────────────────────────────────

def _fake_tt(tactic: str) -> mock.MagicMock:
    tt = mock.MagicMock()
    tt.tactic = tactic
    # traverse_preorder does nothing → AST path yields nothing, only regex runs.
    tt.ast.traverse_preorder = lambda fn, node_cls: None
    return tt


def test_compute_U_empty_hyps():
    assert _compute_U(_fake_tt("exact h"), set()) == []


def test_compute_U_no_match():
    tt = _fake_tt("exact rfl")
    assert _compute_U(tt, {"h1", "h2"}) == []


def test_compute_U_regex_fallback():
    # AST traverse does nothing; regex should pick up h1.
    tt = _fake_tt("rw [h1]")
    assert _compute_U(tt, {"h1", "h2"}) == ["h1"]


def test_compute_U_consume_all_simp_all():
    tt = _fake_tt("simp_all")
    assert set(_compute_U(tt, {"h1", "h2"})) == {"h1", "h2"}


def test_compute_U_consume_all_assumption():
    tt = _fake_tt("assumption")
    assert set(_compute_U(tt, {"h", "g"})) == {"h", "g"}


def test_compute_U_consume_all_simp_star():
    tt = _fake_tt("simp [*, h1]")
    assert set(_compute_U(tt, {"h1", "h2"})) == {"h1", "h2"}


def test_compute_U_sorted():
    tt = _fake_tt("exact ⟨hb, ha⟩")
    result = _compute_U(tt, {"ha", "hb"})
    assert result == sorted(result)


def test_compute_U_dot_notation():
    # E6: dot-notation reference missed by AST; regex fallback must catch it.
    tt = _fake_tt("exact h.left")
    assert _compute_U(tt, {"h", "g"}) == ["h"]


def test_compute_U_subscript_no_false_positive():
    # E7: h₁ and h are both in context; tactic only uses h₁.
    # \bh\b would falsely match the h inside h₁ — the Lean-aware boundary must prevent this.
    tt = _fake_tt("exact h₁")
    result = _compute_U(tt, {"h", "h₁"})
    assert result == ["h₁"]


def test_compute_U_subscript_both_used():
    # Variant: tactic uses both h and h₁ explicitly.
    tt = _fake_tt("exact ⟨h, h₁⟩")
    result = _compute_U(tt, {"h", "h₁"})
    assert set(result) == {"h", "h₁"}


def test_compute_U_prime_no_false_positive():
    # E7 variant: h' and h both in context; tactic only uses h'.
    tt = _fake_tt("exact h'")
    result = _compute_U(tt, {"h", "h'"})
    assert result == ["h'"]


def test_compute_U_consume_all_trivial():
    # E8: trivial is a consume-all tactic.
    tt = _fake_tt("trivial")
    assert set(_compute_U(tt, {"h1", "h2"})) == {"h1", "h2"}


def test_compute_U_consume_all_omega():
    # E8: omega is a consume-all tactic.
    tt = _fake_tt("omega")
    assert set(_compute_U(tt, {"h", "n"})) == {"h", "n"}


def test_compute_U_consume_all_simp_star_not_first():
    # E9: star is not the first element in the simp list.
    tt = _fake_tt("simp [h1, *, h2]")
    assert set(_compute_U(tt, {"h1", "h2", "h3"})) == {"h1", "h2", "h3"}


def test_compute_U_rw_reverse_arrow():
    # E10: rw [← h] — the ← is non-ASCII but h should still be detected.
    tt = _fake_tt("rw [← h]")
    assert _compute_U(tt, {"h", "g"}) == ["h"]


# ── _compute_pi ─────────────────────────────────────────────────────────────

def _hyps(*pairs) -> list[Hypothesis]:
    return [Hypothesis(name=n, type=t) for n, t in pairs]


def test_pi_passthrough():
    ih = _hyps(("h", "Nat"))
    oh = _hyps(("h", "Nat"))
    pi = _compute_pi(ih, oh, [])
    assert pi == {"h": ["h"]}


def test_pi_multiple_passthroughs():
    ih = _hyps(("a", "Nat"), ("b", "Bool"))
    oh = _hyps(("a", "Nat"), ("b", "Bool"))
    pi = _compute_pi(ih, oh, [])
    assert pi == {"a": ["a"], "b": ["b"]}


def test_pi_new_hyp_type_reference():
    ih = _hyps(("h1", "Nat"), ("h2", "Nat"))
    oh = _hyps(("h3", "h1 + h2 = 5"))
    pi = _compute_pi(ih, oh, ["h1"])
    # h1 and h2 both appear in the type
    assert set(pi["h3"]) == {"h1", "h2"}


def test_pi_new_hyp_fallback_to_U():
    ih = _hyps(("h1", "Nat"), ("h2", "Nat"))
    oh = _hyps(("h3", "True"))  # type references no input hyp
    U = ["h1"]
    pi = _compute_pi(ih, oh, U)
    assert pi["h3"] == ["h1"]


def test_pi_empty_U_fallback_gives_empty():
    ih = _hyps(("h", "Nat"))
    oh = _hyps(("h2", "True"))
    pi = _compute_pi(ih, oh, [])
    assert pi["h2"] == []


def test_pi_totality():
    # Every key in output context must appear in the result.
    ih = _hyps(("a", "P"), ("b", "Q"))
    oh = _hyps(("a", "P"), ("c", "P ∧ Q"))
    pi = _compute_pi(ih, oh, ["a", "b"])
    assert set(pi.keys()) == {"a", "c"}


def test_pi_same_name_different_type_is_new():
    # Name matches but type changed → not a passthrough; falls back to U.
    ih = _hyps(("h", "Nat"))
    oh = _hyps(("h", "Int"))  # same name, different type
    pi = _compute_pi(ih, oh, ["h"])
    # Type "Int" references no input hyp by regex, so falls back to U=["h"].
    assert "h" in pi
    assert pi["h"] == ["h"]
