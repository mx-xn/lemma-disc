"""End-to-end test for solo.py (stage 3), bypassing the LLM.

Phases exercised:
  1. Candidate loading     — load_candidates parses candidates JSON correctly
  2. Candidate selection   — _select_candidates filters by num_hyps and caps at num_lemmas
  3. Hint preamble         — _build_hint_preamble produces admitted Lean decls (no indent)
  4. Hint block            — _build_hint_block produces indented lines for the prompt
  5. Source with preamble  — _render_source inserts preamble between imports and theorem
  6. Lean check (no use)   — correct proof of prop_03 passes alongside hint preamble
  7. Lean check (uses h0)  — proof that calls solo_hint_0 directly passes

Subject theorem (prop_03):
    count n xs <= count n (xs ++ ys)

Three candidate lemmas drawn from prop_03_lemmas.json, spanning
num_hyps 1 / 2 / 3 so the test exercises the full filter range.
CAND_0 (num_hyps=1, fragment 7) is the one actually applied in phase 7.

Run from the repo root:
    python -m exp.expB.test_solo
"""
from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from exp.lib.corpus import load_candidates
from exp.lib.lean_check import _render_source, check_proof
from exp.expB.stages.solo import _build_hint_block, _build_hint_preamble, _select_candidates

LAKE_PROJECT = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
IMPORTS = ["LeanSrc.Examples"]
DECL = "expB_solo_prop_03"
STMT = "(n: Nat) (xs: List Nat) (ys: List Nat) : count n xs <= count n (xs ++ ys)"

# ── candidate lemmas (fragments 7 / 0 / 4 from prop_03_lemmas.json) ──────────

# CAND_0 — fragment 7, num_hyps=1: one inductive hypothesis
CAND_0 = (
    "(n : ℕ) (ys : List ℕ) (x : ℕ) (xs : List ℕ) "
    "(ih : count n xs ≤ count n (xs ++ ys)) : "
    "count n (x :: xs) ≤ count n (x :: (xs ++ ys))"
)
# CAND_1 — fragment 0, num_hyps=2: two prop hypotheses (ih, h1)
CAND_1 = (
    "(n : ℕ) (xs : List ℕ) (ys : List ℕ) (x : ℕ) "
    "(ih : count n xs ≤ count n (xs ++ ys)) "
    "(h1 : count n (x :: xs) ≤ count n (x :: xs ++ ys)) : "
    "count n xs ≤ count n (xs ++ ys)"
)
# CAND_2 — fragment 4, num_hyps=3: three prop hypotheses (ih, h, h1)
CAND_2 = (
    "(n : ℕ) (ys : List ℕ) (x : ℕ) (xs : List ℕ) "
    "(ih : count n xs ≤ count n (xs ++ ys)) "
    "(h : ¬n = x) "
    "(h1 : count n xs ≤ count n (xs ++ ys)) : "
    "count n (x :: xs) ≤ count n (x :: xs ++ ys)"
)
CANDIDATES = [CAND_0, CAND_1, CAND_2]


# ── helpers ───────────────────────────────────────────────────────────────────

def _sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── phases ────────────────────────────────────────────────────────────────────

def phase1_candidate_loading() -> None:
    _sep("Phase 1 — candidate loading")
    raw = {"prop_03": CANDIDATES, "other_thm": ["some stmt"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(raw, f)
        tmp = Path(f.name)
    try:
        cset = load_candidates(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    print(f"  entries          : {list(cset.entries.keys())}")
    print(f"  prop_03 count    : {len(cset.entries['prop_03'])}")
    print(f"  prop_03[0][:60]  : {cset.entries['prop_03'][0][:60]}...")

    assert list(cset.entries.keys()) == ["prop_03", "other_thm"]
    assert len(cset.entries["prop_03"]) == 3
    assert cset.entries["prop_03"][0] == CAND_0
    assert cset.entries["prop_03"][1] == CAND_1
    assert cset.entries["prop_03"][2] == CAND_2
    assert cset.entries["other_thm"] == ["some stmt"]
    print("  ✓ PASS")


def phase2_candidate_selection() -> None:
    _sep("Phase 2 — candidate selection (num_hyps filter + num_lemmas cap)")
    rng = random.Random(0)

    # no filter, no cap — all three returned
    result = _select_candidates(CANDIDATES, None, None, rng)
    print(f"  no filter    : {len(result)} candidates")
    assert result == CANDIDATES, f"expected all 3, got {result}"

    # filter num_hyps=1 — only CAND_0
    result = _select_candidates(CANDIDATES, 1, None, rng)
    print(f"  num_hyps=1   : {len(result)} candidate(s)")
    assert result == [CAND_0], f"expected [CAND_0], got {result}"

    # filter num_hyps=2 — only CAND_1
    result = _select_candidates(CANDIDATES, 2, None, rng)
    print(f"  num_hyps=2   : {len(result)} candidate(s)")
    assert result == [CAND_1], f"expected [CAND_1], got {result}"

    # filter num_hyps=3 — only CAND_2
    result = _select_candidates(CANDIDATES, 3, None, rng)
    print(f"  num_hyps=3   : {len(result)} candidate(s)")
    assert result == [CAND_2], f"expected [CAND_2], got {result}"

    # filter num_hyps that matches nothing — empty
    result = _select_candidates(CANDIDATES, 99, None, rng)
    print(f"  num_hyps=99  : {len(result)} candidate(s)")
    assert result == [], f"expected [], got {result}"

    # no filter, cap at 2 — sample of 2 from 3
    result = _select_candidates(CANDIDATES, None, 2, random.Random(42))
    print(f"  num_lemmas=2 : {len(result)} candidate(s)")
    assert len(result) == 2
    assert all(r in CANDIDATES for r in result)

    # no filter, cap larger than available — all three returned
    result = _select_candidates(CANDIDATES, None, 10, rng)
    print(f"  num_lemmas=10: {len(result)} candidate(s)")
    assert result == CANDIDATES

    # filter + cap: num_hyps=1 gives 1 candidate, cap=2 → still 1
    result = _select_candidates(CANDIDATES, 1, 2, rng)
    print(f"  num_hyps=1, num_lemmas=2: {len(result)} candidate(s)")
    assert result == [CAND_0]

    print("  ✓ PASS")


def phase3_hint_preamble() -> None:
    _sep("Phase 3 — hint preamble rendering (_build_hint_preamble)")
    preamble = _build_hint_preamble([CAND_0, CAND_1])
    print(preamble)

    lines = preamble.splitlines()
    assert len(lines) == 2, f"expected 2 lines, got {len(lines)}"
    assert lines[0] == f"theorem solo_hint_0 {CAND_0} := by admit", repr(lines[0])
    assert lines[1] == f"theorem solo_hint_1 {CAND_1} := by admit", repr(lines[1])
    print("  ✓ PASS")


def phase4_hint_block() -> None:
    _sep("Phase 4 — hint block rendering (_build_hint_block, for prompt)")
    block = _build_hint_block([CAND_0, CAND_1, CAND_2])
    print(block)

    lines = block.splitlines()
    assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"
    assert lines[0] == f"    theorem solo_hint_0 {CAND_0} := by admit", repr(lines[0])
    assert lines[1] == f"    theorem solo_hint_1 {CAND_1} := by admit", repr(lines[1])
    assert lines[2] == f"    theorem solo_hint_2 {CAND_2} := by admit", repr(lines[2])
    print("  ✓ PASS")


def phase5_source_with_preamble() -> None:
    _sep("Phase 5 — source rendering with hint preamble")
    preamble = _build_hint_preamble([CAND_0])
    source = _render_source(IMPORTS, DECL, STMT, "omega", preamble)
    print(source)

    lines = source.splitlines()
    import_idx   = next(i for i, l in enumerate(lines) if l.startswith("import "))
    preamble_idx = next(i for i, l in enumerate(lines) if l.startswith("theorem solo_hint_0 "))
    target_idx   = next(i for i, l in enumerate(lines) if l.startswith(f"theorem {DECL}"))

    assert import_idx < preamble_idx < target_idx, (
        f"expected import({import_idx}) < preamble({preamble_idx}) < target({target_idx})"
    )
    assert lines[import_idx]   == "import LeanSrc.Examples"
    assert lines[preamble_idx] == f"theorem solo_hint_0 {CAND_0} := by admit"
    assert lines[target_idx]   == f"theorem {DECL} {STMT} := by"
    print("  ✓ PASS")


def phase6_lean_check_no_hint_use() -> None:
    _sep("Phase 6 — check_proof with hint preamble, proof does not call solo_hint_0")
    preamble = _build_hint_preamble([CAND_0])
    proof = "\n".join([
        "induction xs with",
        "| nil => simp [count]",
        "| cons x xs ih =>",
        "  show count n (x :: xs) ≤ count n (x :: (xs ++ ys))",
        "  simp only [count]",
        "  split_ifs with h",
        "  · omega",
        "  · exact ih",
    ])
    result = check_proof(
        STMT, proof,
        lake_project=LAKE_PROJECT,
        imports=IMPORTS,
        decl_name=DECL,
        preamble=preamble,
    )
    print(f"  ok         : {result.ok}")
    print(f"  error_text : {result.error_text!r}")

    assert result.ok is True, f"Expected ok=True, got: {result.error_text}"
    assert result.error_text == ""
    print("  ✓ PASS")


def phase7_lean_check_uses_solo_hint_0() -> None:
    _sep("Phase 7 — check_proof with hint preamble, proof calls solo_hint_0 directly")
    # CAND_0 (fragment 7) closes the cons case exactly:
    #   solo_hint_0 n ys x xs ih : count n (x::xs) ≤ count n (x::(xs++ys))
    preamble = _build_hint_preamble([CAND_0])
    proof = "\n".join([
        "induction xs with",
        "| nil => simp [count]",
        "| cons x xs ih =>",
        "  show count n (x :: xs) ≤ count n (x :: (xs ++ ys))",
        "  exact solo_hint_0 n ys x xs ih",
    ])
    result = check_proof(
        STMT, proof,
        lake_project=LAKE_PROJECT,
        imports=IMPORTS,
        decl_name=DECL,
        preamble=preamble,
    )
    print(f"  ok         : {result.ok}")
    print(f"  error_text : {result.error_text!r}")

    assert result.ok is True, f"Expected ok=True, got: {result.error_text}"
    assert result.error_text == ""
    print("  ✓ PASS")


# ── runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        phase1_candidate_loading()
        phase2_candidate_selection()
        phase3_hint_preamble()
        phase4_hint_block()
        phase5_source_with_preamble()
        phase6_lean_check_no_hint_use()
        phase7_lean_check_uses_solo_hint_0()
        print(f"\n{'═' * 60}")
        print("  ALL PHASES PASSED")
        print("═" * 60)
    except AssertionError as e:
        print(f"\n  ✗ FAIL: {e}", file=sys.stderr)
        sys.exit(1)
