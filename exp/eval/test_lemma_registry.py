"""Tests for exp.eval.lib.lemma_registry.

Run from the repo root:
    pytest exp/eval/test_lemma_registry.py
"""
from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from exp.eval.lib.lemma_registry import LemmaEntry, LemmaRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _Attempt:
    used_indices: list[int]


@dataclass
class _Result:
    ok: bool
    attempts: list[_Attempt]


# ---------------------------------------------------------------------------
# LemmaEntry.score
# ---------------------------------------------------------------------------

def test_score_zero():
    e = LemmaEntry(statement="s")
    assert e.score() == 0.0


def test_score_formula():
    e = LemmaEntry(statement="s", extraction_freq=2, success_cited=1, attempted_cited=3)
    expected = 1.0 + 3 * 0.2 + math.log1p(2) * 0.5
    assert abs(e.score() - expected) < 1e-12


# ---------------------------------------------------------------------------
# add_extracted — deduplication and freq counting
# ---------------------------------------------------------------------------

def test_add_extracted_new_entry():
    reg = LemmaRegistry()
    reg.add_extracted(["(a : Nat) : a = a"])
    entries = reg.entries()
    assert len(entries) == 1
    assert entries[0].statement == "(a : Nat) : a = a"
    assert entries[0].extraction_freq == 1


def test_add_extracted_dedup_by_strip():
    """Whitespace-padded duplicates collapse to one entry with freq=2."""
    reg = LemmaRegistry()
    reg.add_extracted(["  (a : Nat) : a = a  ", "(a : Nat) : a = a"])
    entries = reg.entries()
    assert len(entries) == 1
    assert entries[0].extraction_freq == 2


def test_add_extracted_across_calls():
    """Freq accumulates correctly across multiple add_extracted calls."""
    reg = LemmaRegistry()
    reg.add_extracted(["(h : P) : P"])
    reg.add_extracted(["(h : P) : P"])
    assert reg.entries()[0].extraction_freq == 2


def test_add_extracted_skips_empty():
    reg = LemmaRegistry()
    reg.add_extracted(["", "   ", "(h : P) : P"])
    assert len(reg.entries()) == 1


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def test_json_roundtrip():
    reg = LemmaRegistry()
    reg.add_extracted(["(a : Nat) : a = a", "(h : P) : P"])
    reg._entries["(a : Nat) : a = a"].success_cited = 3
    reg._entries["(h : P) : P"].attempted_cited = 7

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sub" / "lemma_registry.json"
        reg.save(path)
        assert path.exists()
        reg2 = LemmaRegistry.load_or_empty(path)

    by_stmt = {e.statement: e for e in reg2.entries()}
    assert len(by_stmt) == 2
    assert by_stmt["(a : Nat) : a = a"].success_cited == 3
    assert by_stmt["(a : Nat) : a = a"].extraction_freq == 1
    assert by_stmt["(h : P) : P"].attempted_cited == 7


def test_load_or_empty_missing_file():
    reg = LemmaRegistry.load_or_empty(Path("/nonexistent/does_not_exist.json"))
    assert reg.entries() == []


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------

def test_record_usage_success_cited():
    pool = ["(a : Nat) : a = a", "(h : P) : P", "(n : Nat) : n + 0 = n"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=True, attempts=[_Attempt(used_indices=[0, 2])]),
    }
    reg.record_usage(results, pool)

    by_stmt = {e.statement: e for e in reg.entries()}
    assert by_stmt[pool[0]].success_cited == 1
    assert by_stmt[pool[1]].success_cited == 0   # not used
    assert by_stmt[pool[2]].success_cited == 1


def test_record_usage_attempted_cited():
    pool = ["(a : Nat) : a = a"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=False, attempts=[_Attempt(used_indices=[0])]),
    }
    reg.record_usage(results, pool)
    e = reg.entries()[0]
    assert e.attempted_cited == 1
    assert e.success_cited == 0


def test_record_usage_dedup_across_attempts():
    """Same index appearing in multiple fix-loop attempts counts once per theorem."""
    pool = ["(h : P) : P"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=True, attempts=[
            _Attempt(used_indices=[0]),
            _Attempt(used_indices=[0]),
        ]),
    }
    reg.record_usage(results, pool)
    assert reg.entries()[0].success_cited == 1  # not 2


def test_record_usage_multiple_theorems():
    """Each theorem contributes independently to cited counts."""
    pool = ["(h : P) : P"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=True, attempts=[_Attempt(used_indices=[0])]),
        "thm2": _Result(ok=False, attempts=[_Attempt(used_indices=[0])]),
    }
    reg.record_usage(results, pool)
    e = reg.entries()[0]
    assert e.success_cited == 1
    assert e.attempted_cited == 1


def test_record_usage_empty_indices():
    """Attempt with no used indices → no update."""
    pool = ["(h : P) : P"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=True, attempts=[_Attempt(used_indices=[])]),
    }
    reg.record_usage(results, pool)
    assert reg.entries()[0].success_cited == 0


def test_record_usage_out_of_bounds_index():
    """Index beyond pool length is silently ignored."""
    pool = ["(h : P) : P"]
    reg = LemmaRegistry()
    reg.add_extracted(pool)

    results = {
        "thm1": _Result(ok=True, attempts=[_Attempt(used_indices=[99])]),
    }
    reg.record_usage(results, pool)
    assert reg.entries()[0].success_cited == 0


def test_record_usage_index_not_in_registry():
    """Pool entry not in registry (e.g. lemma wasn't add_extracted) is silently skipped."""
    pool = ["(h : P) : P", "(a : Nat) : a = a"]
    reg = LemmaRegistry()
    reg.add_extracted(["(h : P) : P"])  # only first is registered

    results = {
        "thm1": _Result(ok=True, attempts=[_Attempt(used_indices=[0, 1])]),
    }
    reg.record_usage(results, pool)  # index 1 points to unregistered stmt
    assert reg.entries()[0].success_cited == 1
    assert len(reg.entries()) == 1
