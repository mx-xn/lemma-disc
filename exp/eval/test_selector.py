"""Tests for exp.eval.lib.selector.

Run from the repo root:
    pytest exp/eval/test_selector.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exp.eval.lib.lemma_registry import LemmaEntry, LemmaRegistry
from exp.eval.lib.selector import _llm_rank, select


# ---------------------------------------------------------------------------
# LLM stub
# ---------------------------------------------------------------------------

@dataclass
class _LLMResponse:
    text: str
    cached: bool = False


class _StubLLM:
    def __init__(self, response: str = "") -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def chat(self, system: str, user: str) -> _LLMResponse:
        self.calls.append((system, user))
        return _LLMResponse(text=self._response)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registry_from(entries: list[tuple[str, float, float, float]]) -> LemmaRegistry:
    """Build a registry from (statement, extraction_freq, success_cited, attempted_cited)."""
    reg = LemmaRegistry()
    for stmt, ef, sc, ac in entries:
        key = stmt.strip()
        reg._entries[key] = LemmaEntry(
            statement=key,
            extraction_freq=int(ef),
            success_cited=int(sc),
            attempted_cited=int(ac),
        )
    return reg


_LAKE = Path("/fake/lake")
_IMPORTS = ["Mathlib"]

# Statements with known num_hyps values:
#   0 hyps: (n : Nat) : n + 0 = n      — Nat is a type, not a Prop
#   1 hyp:  (h : a = b) : b = a        — one propositional hypothesis
#   2 hyps: (h1 : a = b) (h2 : b = c) : a = c
S0 = "(n : Nat) : n + 0 = n"
S1 = "(h : a = b) : b = a"
S2 = "(h1 : a = b) (h2 : b = c) : a = c"


# ---------------------------------------------------------------------------
# select — empty registry
# ---------------------------------------------------------------------------

def test_select_empty_registry():
    reg = LemmaRegistry()
    result = select(reg, max_n=5, max_hyps=2, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert result == []


# ---------------------------------------------------------------------------
# select — max_hyps filtering
# ---------------------------------------------------------------------------

def test_select_filters_by_max_hyps():
    reg = _registry_from([
        (S0, 1, 0, 0),   # 0 hyps — should pass max_hyps=1
        (S1, 1, 0, 0),   # 1 hyp  — should pass max_hyps=1
        (S2, 1, 0, 0),   # 2 hyps — should be excluded
    ])
    result = select(reg, max_n=10, max_hyps=1, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert S2 not in result
    assert S0 in result
    assert S1 in result


def test_select_max_hyps_zero_excludes_all_prop_hyps():
    reg = _registry_from([(S1, 1, 0, 0), (S0, 1, 0, 0)])
    result = select(reg, max_n=10, max_hyps=0, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert S1 not in result
    assert S0 in result


# ---------------------------------------------------------------------------
# select — score-based ordering
# ---------------------------------------------------------------------------

def test_select_sorted_by_score_descending():
    # success_cited=2 → score 2.0; success_cited=0 → score ~0.35 (log1p(1)*0.5)
    high = S0
    low  = S1
    reg = _registry_from([
        (low,  1, 0, 0),   # lower score
        (high, 0, 2, 0),   # higher score
    ])
    result = select(reg, max_n=2, max_hyps=5, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert result[0] == high
    assert result[1] == low


# ---------------------------------------------------------------------------
# select — max_n truncation
# ---------------------------------------------------------------------------

def test_select_truncates_to_max_n():
    reg = _registry_from([(S0, 0, i, 0) for i in range(5)])
    # Five distinct statements would be needed; simulate with one score-varied entry per statement
    # Instead, use a registry with 3 entries and max_n=2
    reg2 = LemmaRegistry()
    stmts = [
        "(a : Nat) : a = a",
        "(b : Nat) : b + 0 = b",
        "(c : Nat) : 0 + c = c",
    ]
    for i, s in enumerate(stmts):
        reg2._entries[s] = LemmaEntry(statement=s, extraction_freq=1, success_cited=i)
    result = select(reg2, max_n=2, max_hyps=5, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert len(result) == 2


def test_select_returns_all_when_fewer_than_max_n():
    reg = _registry_from([(S0, 1, 0, 0), (S1, 1, 0, 0)])
    result = select(reg, max_n=10, max_hyps=5, llm=_StubLLM(), lake_project=_LAKE, imports=_IMPORTS)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# select — LLM is not called when top fills max_n
# ---------------------------------------------------------------------------

def test_select_does_not_call_llm_when_top_full():
    llm = _StubLLM()
    reg = LemmaRegistry()
    for i in range(5):
        s = f"(n : Nat) : n + {i} = n + {i}"
        reg._entries[s] = LemmaEntry(statement=s, extraction_freq=1)
    select(reg, max_n=5, max_hyps=5, llm=llm, lake_project=_LAKE, imports=_IMPORTS)
    assert llm.calls == []


# ---------------------------------------------------------------------------
# _llm_rank — parsing and mutation guard
# ---------------------------------------------------------------------------

def test_llm_rank_returns_statements_in_order():
    entries = [
        LemmaEntry(statement=S0),
        LemmaEntry(statement=S1),
        LemmaEntry(statement=S2),
    ]
    llm = _StubLLM("2\n0\n1")
    result = _llm_rank(entries, llm, imports=_IMPORTS)
    assert result == [S2, S0, S1]


def test_llm_rank_ignores_out_of_bounds():
    entries = [LemmaEntry(statement=S0)]
    llm = _StubLLM("0\n99")
    result = _llm_rank(entries, llm, imports=_IMPORTS)
    assert result == [S0]


def test_llm_rank_deduplicates_indices():
    entries = [LemmaEntry(statement=S0), LemmaEntry(statement=S1)]
    llm = _StubLLM("0\n0\n1")
    result = _llm_rank(entries, llm, imports=_IMPORTS)
    assert result == [S0, S1]


def test_llm_rank_ignores_non_integer_lines():
    entries = [LemmaEntry(statement=S0), LemmaEntry(statement=S1)]
    llm = _StubLLM("Sure!\n0\nL1\n1\n")
    result = _llm_rank(entries, llm, imports=_IMPORTS)
    assert result == [S0, S1]


def test_llm_rank_empty_response():
    entries = [LemmaEntry(statement=S0)]
    llm = _StubLLM("")
    result = _llm_rank(entries, llm, imports=_IMPORTS)
    assert result == []


def test_llm_rank_candidates_appear_in_prompt():
    entries = [LemmaEntry(statement=S0), LemmaEntry(statement=S1)]
    llm = _StubLLM("0")
    _llm_rank(entries, llm, imports=["Mathlib", "Init"])
    assert len(llm.calls) == 1
    _, user_prompt = llm.calls[0]
    assert "L0:" in user_prompt
    assert "L1:" in user_prompt
    assert S0 in user_prompt
    assert S1 in user_prompt
    assert "Mathlib" in user_prompt
