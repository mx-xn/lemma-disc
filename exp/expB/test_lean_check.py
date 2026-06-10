"""End-to-end test for lean_check.py phases, bypassing the LLM.

Phases exercised:
  1. Corpus loading   — load_theorems parses input/theorems.json correctly
  2. Source rendering — _render_source produces the expected .lean text
  3. Lean execution   — check_proof with a correct proof → ok=True
  4. Error path       — check_proof with a wrong proof  → ok=False + formatted error
  5. Sorry detection  — check_proof with sorry          → ok=False, "proof contains sorry"

Run from the repo root:
    python -m exp.expB.test_lean_check
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── resolve paths relative to this file ──────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_THEOREMS_JSON = _HERE / "input" / "theorems.json"

# ensure the repo root is on sys.path so the package can be imported directly
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from exp.lib.corpus import load_theorems
from exp.lib.lean_check import _render_source, check_proof

LAKE_PROJECT = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
IMPORTS = ["Mathlib"]
DECL = "expB_dummy_add_comm"
STMT = "(n m : Nat) : n + m = m + n"


# ─────────────────────────────────────────────────────────────────────────────

def _sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


def phase1_corpus_loading() -> None:
    _sep("Phase 1 — corpus loading")
    tset = load_theorems(_THEOREMS_JSON)
    print(f"  lake_project : {tset.lake_project}")
    print(f"  imports      : {tset.imports}")
    print(f"  theorems     : {len(tset.theorems)} theorem(s)")
    thm = tset.theorems[0]
    print(f"  theorem_id   : {thm.theorem_id}")
    print(f"  statement    : {thm.statement_text}")

    assert tset.lake_project is not None
    assert tset.imports == ["Mathlib"]
    assert len(tset.theorems) == 1
    assert thm.theorem_id == "dummy_add_comm"
    assert thm.statement_text == STMT
    print("  ✓ PASS")


def phase2_source_rendering() -> None:
    _sep("Phase 2 — source rendering (_render_source)")
    source = _render_source(IMPORTS, DECL, STMT, "omega")
    print(source)

    assert "import Mathlib" in source
    assert f"theorem {DECL}" in source
    assert STMT in source
    assert "omega" in source
    print("  ✓ PASS")


def phase3_correct_proof() -> None:
    _sep("Phase 3 — check_proof with correct proof ('omega')")
    result = check_proof(
        STMT, "omega",
        lake_project=LAKE_PROJECT,
        imports=IMPORTS,
        decl_name=DECL,
    )
    print(f"  ok         : {result.ok}")
    print(f"  error_text : {result.error_text!r}")

    assert result.ok is True, f"Expected ok=True, got error: {result.error_text}"
    assert result.error_text == ""
    print("  ✓ PASS")


def phase4_wrong_proof() -> None:
    _sep("Phase 4 — check_proof with wrong proof ('rfl')")
    result = check_proof(
        STMT, "rfl",
        lake_project=LAKE_PROJECT,
        imports=IMPORTS,
        decl_name=DECL,
    )
    print(f"  ok         : {result.ok}")
    print(f"  error_text :\n{result.error_text}")

    assert result.ok is False
    assert result.error_text != ""
    print("  ✓ PASS")


def phase5_sorry_proof() -> None:
    _sep("Phase 5 — check_proof with 'sorry'")
    result = check_proof(
        STMT, "sorry",
        lake_project=LAKE_PROJECT,
        imports=IMPORTS,
        decl_name=DECL,
    )
    print(f"  ok         : {result.ok}")
    print(f"  error_text : {result.error_text!r}")

    assert result.ok is False
    assert result.error_text == "proof contains sorry"
    print("  ✓ PASS")


if __name__ == "__main__":
    try:
        phase1_corpus_loading()
        phase2_source_rendering()
        phase3_correct_proof()
        phase4_wrong_proof()
        phase5_sorry_proof()
        print(f"\n{'═' * 60}")
        print("  ALL PHASES PASSED")
        print('═' * 60)
    except AssertionError as e:
        print(f"\n  ✗ FAIL: {e}", file=sys.stderr)
        sys.exit(1)
