"""Tests for exp.eval.lib.lemma_fixer and exp.eval.lib.generalizer.

Both modules make external calls (Lean, LLM) which are stubbed here.
``batch_validate`` is monkeypatched so fix_lemmas and generalizer tests
exercise control-flow logic without a real Lean environment.

Run from the repo root:
    pytest exp/eval/test_lemma_fixer_generalizer.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest

import exp.eval.lib.lemma_fixer as fixer_mod
import exp.eval.lib.generalizer as gen_mod
from exp.eval.lib.lemma_fixer import fix_lemmas
from exp.eval.lib.generalizer import generalize_lemmas, generalize_one

_LAKE = Path("/fake/lake")
_IMPORTS = ["Mathlib"]


# ---------------------------------------------------------------------------
# Shared stubs
# ---------------------------------------------------------------------------

@dataclass
class _LLMResponse:
    text: str
    cached: bool = False


class _StubLLM:
    """Returns predetermined responses in order; empty string when exhausted."""

    def __init__(self, responses: list[str] = ()) -> None:
        self._it: Iterator[str] = iter(responses)
        self.calls: list[str] = []

    def chat(self, system: str, user: str) -> _LLMResponse:
        self.calls.append(user)
        return _LLMResponse(text=next(self._it, ""))


def _validate_returning(call_results: list[dict[int, str]]):
    """Return a mock for batch_validate that pops results from call_results."""
    results = iter(call_results)

    def _mock(stmts, lake_project, imports):
        if not stmts:
            return {}
        return next(results, {})

    return _mock


# ---------------------------------------------------------------------------
# fix_lemmas — all valid from start
# ---------------------------------------------------------------------------

def test_fix_lemmas_all_valid_no_llm_calls():
    llm = _StubLLM()
    # batch_validate returns {} → all pass on first check, loop breaks, final is no-op
    with patch.object(fixer_mod, "batch_validate", side_effect=[{}, {}]):
        result = fix_lemmas(["(n : Nat) : n = n"], llm, _LAKE, _IMPORTS)
    assert result == ["(n : Nat) : n = n"]
    assert llm.calls == []


def test_fix_lemmas_empty_input():
    llm = _StubLLM()
    with patch.object(fixer_mod, "batch_validate", return_value={}):
        result = fix_lemmas([], llm, _LAKE, _IMPORTS)
    assert result == []


# ---------------------------------------------------------------------------
# fix_lemmas — broken, fixed in loop round
# ---------------------------------------------------------------------------

def test_fix_lemmas_fixed_in_loop_round():
    """Statement broken in round 1, LLM fixes it, round 2 finds it valid."""
    llm = _StubLLM(["(n : Nat) : n + 0 = n"])  # LLM fix response
    validate_calls = [
        {0: "unknown identifier 'bad'"},  # round 1: broken
        {},                               # round 2: all pass → break
        {},                               # final pass (no-op — to_check empty)
    ]
    with patch.object(fixer_mod, "batch_validate", side_effect=validate_calls):
        result = fix_lemmas(["bad_stmt"], llm, _LAKE, _IMPORTS, max_fix_rounds=2)
    assert result == ["(n : Nat) : n + 0 = n"]


def test_fix_lemmas_fixed_in_final_pass():
    """With max_fix_rounds=1: broken, LLM fixes, final pass confirms fix."""
    llm = _StubLLM(["(n : Nat) : n + 0 = n"])
    validate_calls = [
        {0: "type mismatch"},   # round 1: broken → LLM fix
        {},                     # final pass: fixed stmt passes
    ]
    with patch.object(fixer_mod, "batch_validate", side_effect=validate_calls):
        result = fix_lemmas(["bad_stmt"], llm, _LAKE, _IMPORTS, max_fix_rounds=1)
    assert result == ["(n : Nat) : n + 0 = n"]


# ---------------------------------------------------------------------------
# fix_lemmas — unfixable statements are excluded
# ---------------------------------------------------------------------------

def test_fix_lemmas_unfixable_excluded():
    """LLM attempt doesn't resolve the error; statement excluded from result."""
    llm = _StubLLM(["still_bad"])
    validate_calls = [
        {0: "error A"},  # round 1
        {0: "error B"},  # final pass: still broken
    ]
    with patch.object(fixer_mod, "batch_validate", side_effect=validate_calls):
        result = fix_lemmas(["bad_stmt"], llm, _LAKE, _IMPORTS, max_fix_rounds=1)
    assert result == []


def test_fix_lemmas_llm_returns_empty_excluded():
    """Empty LLM response leaves statement unchanged; it fails final check → excluded."""
    llm = _StubLLM([""])  # empty fix
    validate_calls = [
        {0: "error"},   # round 1: broken
        {0: "error"},   # final: still broken (original unchanged because fix was empty)
    ]
    with patch.object(fixer_mod, "batch_validate", side_effect=validate_calls):
        result = fix_lemmas(["bad_stmt"], llm, _LAKE, _IMPORTS, max_fix_rounds=1)
    assert result == []


# ---------------------------------------------------------------------------
# fix_lemmas — mix of valid and broken statements
# ---------------------------------------------------------------------------

def test_fix_lemmas_mix_valid_and_broken():
    """Valid statements are kept; broken-then-fixed ones are also returned."""
    llm = _StubLLM(["fixed_stmt"])
    validate_calls = [
        {1: "error"},  # round 1: index 0 passes, index 1 broken → LLM fix
        {},            # round 2: all pass → break
        {},            # final: to_check empty
    ]
    with patch.object(fixer_mod, "batch_validate", side_effect=validate_calls):
        result = fix_lemmas(["good_stmt", "bad_stmt"], llm, _LAKE, _IMPORTS, max_fix_rounds=2)
    assert "good_stmt" in result
    assert "fixed_stmt" in result
    assert len(result) == 2


def test_fix_lemmas_valid_not_rechecked_after_confirmed():
    """Once a statement is marked valid it is excluded from subsequent to_check dicts."""
    # We track the indices passed to batch_validate
    call_log: list[set[int]] = []

    def _track(stmts, lake_project, imports):
        call_log.append(set(stmts.keys()))
        if not stmts:
            return {}
        # First non-empty call: index 0 passes, index 1 broken
        if 0 in stmts and 1 in stmts:
            return {1: "err"}
        # Second call: only index 1 checked, fix works
        return {}

    llm = _StubLLM(["fixed"])
    with patch.object(fixer_mod, "batch_validate", side_effect=_track):
        result = fix_lemmas(["good", "bad"], llm, _LAKE, _IMPORTS, max_fix_rounds=2)

    # Round 1 checked both; round 2 / final should only see index 1
    assert call_log[0] == {0, 1}
    for subsequent in call_log[1:]:
        assert 0 not in subsequent  # confirmed-valid index 0 never rechecked


# ---------------------------------------------------------------------------
# fix_lemmas — early break saves validate calls
# ---------------------------------------------------------------------------

def test_fix_lemmas_early_break_calls_validate_once():
    """If round 1 passes everything, the loop breaks and the final pass is a no-op."""
    call_count = 0

    def _count(stmts, lake_project, imports):
        nonlocal call_count
        if not stmts:
            return {}
        call_count += 1
        return {}

    llm = _StubLLM()
    with patch.object(fixer_mod, "batch_validate", side_effect=_count):
        fix_lemmas(["(n : Nat) : n = n"], llm, _LAKE, _IMPORTS, max_fix_rounds=3)

    assert call_count == 1  # only the first loop iteration, final pass is empty


# ---------------------------------------------------------------------------
# generalize_one — valid generalization used
# ---------------------------------------------------------------------------

def test_generalize_one_valid_uses_generalized():
    llm = _StubLLM(["(p q : Prop) : p /\\ (p -> q) -> q"])
    with patch.object(gen_mod, "batch_validate", return_value={}):
        result = generalize_one("(n : Nat) : n * 2 > 0 /\\ (n * 2 > 0 -> True) -> True",
                                llm, _LAKE, _IMPORTS)
    assert result == "(p q : Prop) : p /\\ (p -> q) -> q"


def test_generalize_one_invalid_falls_back_to_original():
    original = "(n : Nat) : n + 0 = n"
    llm = _StubLLM(["bad generalization"])
    with patch.object(gen_mod, "batch_validate", return_value={0: "type error"}):
        result = generalize_one(original, llm, _LAKE, _IMPORTS)
    assert result == original


def test_generalize_one_empty_llm_falls_back():
    original = "(n : Nat) : n = n"
    llm = _StubLLM([""])  # empty response
    # batch_validate should not be called (empty generalized string short-circuits)
    with patch.object(gen_mod, "batch_validate") as mock_bv:
        result = generalize_one(original, llm, _LAKE, _IMPORTS)
    assert result == original
    mock_bv.assert_not_called()


# ---------------------------------------------------------------------------
# generalize_lemmas — applies to all statements
# ---------------------------------------------------------------------------

def test_generalize_lemmas_applies_to_all():
    stmts = ["(n : Nat) : n = n", "(m : Nat) : m + 0 = m"]
    responses = ["(a : Type) : a = a", ""]  # second one is empty → fallback
    llm = _StubLLM(responses)

    validate_side_effects = [
        {},            # first: valid → use generalized
        # second LLM response is empty, batch_validate not called for it
    ]
    with patch.object(gen_mod, "batch_validate", side_effect=validate_side_effects):
        result = generalize_lemmas(stmts, llm, _LAKE, _IMPORTS)

    assert result[0] == "(a : Type) : a = a"   # generalized
    assert result[1] == "(m : Nat) : m + 0 = m"  # fallback


def test_generalize_lemmas_empty_input():
    llm = _StubLLM()
    with patch.object(gen_mod, "batch_validate", return_value={}):
        result = generalize_lemmas([], llm, _LAKE, _IMPORTS)
    assert result == []
