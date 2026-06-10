"""End-to-end test for pick.py (stage 2), bypassing the LLM.

Phases exercised:
  1. Candidate loading    — load_candidates parses candidates JSON correctly
  2. Menu rendering       — _build_candidate_menu produces [L0]/[L1]/[L2] lines
  3. Preamble rendering   — _build_preamble produces valid sorry-backed Lean decls
  4. Source with preamble — _render_source inserts preamble between imports and theorem
  5. Used-lemma parsing   — _parse_used_lemmas handles indices, "none", out-of-range
  6. Lean check (no use)  — correct proof of prop_03 passes alongside preamble
  7. Lean check (uses L0) — proof of prop_03 that calls L0 directly passes

Subject theorem (prop_03):
    count n xs <= count n (xs ++ ys)

Three candidate lemmas are drawn from prop_03_lemmas.json, spanning
num_hyps 1 / 2 / 3 so the test exercises the full range the experiment cares
about.  L0 (num_hyps=1, fragment 7) is the one actually used in phase 7.

Run from the repo root:
    python -m exp.expB.test_pick
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from exp.lib.corpus import load_candidates
from exp.lib.lean_check import _render_source, check_proof
from exp.expB.stages.pick import _build_candidate_menu, _build_preamble, _parse_used_lemmas

LAKE_PROJECT = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
IMPORTS = ["LeanSrc.Examples"]
DECL = "expB_pick_prop_03"
STMT = "(n: Nat) (xs: List Nat) (ys: List Nat) : count n xs <= count n (xs ++ ys)"

# ── candidate lemmas ─────────────────────────────────────────────────────────

# L0 — fragment 7, num_hyps=1: one inductive hypothesis
CAND_0 = (
    "(n : ℕ) (ys : List ℕ) (x : ℕ) (xs : List ℕ) "
    "(ih : count n xs ≤ count n (xs ++ ys)) : "
    "count n (x :: xs) ≤ count n (x :: (xs ++ ys))"
)
# L1 — fragment 0, num_hyps=2: two hypotheses (ih, h1)
CAND_1 = (
    "(n : ℕ) (xs : List ℕ) (ys : List ℕ) (x : ℕ) "
    "(ih : count n xs ≤ count n (xs ++ ys)) "
    "(h1 : count n (x :: xs) ≤ count n (x :: xs ++ ys)) : "
    "count n xs ≤ count n (xs ++ ys)"
)
# L2 — fragment 4, num_hyps=3: three hypotheses (ih, h, h1)
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

    print(f"  entries         : {list(cset.entries.keys())}")
    print(f"  prop_03 count   : {len(cset.entries['prop_03'])}")
    print(f"  prop_03[0][:60] : {cset.entries['prop_03'][0][:60]}...")

    assert list(cset.entries.keys()) == ["prop_03", "other_thm"]
    assert len(cset.entries["prop_03"]) == 3
    assert cset.entries["prop_03"][0] == CAND_0
    assert cset.entries["prop_03"][1] == CAND_1
    assert cset.entries["prop_03"][2] == CAND_2
    assert cset.entries["other_thm"] == ["some stmt"]
    print("  ✓ PASS")


def phase2_menu_rendering() -> None:
    _sep("Phase 2 — candidate menu rendering")
    menu = _build_candidate_menu(CANDIDATES)
    print(menu)

    lines = menu.splitlines()
    assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"
    assert lines[0] == f"[L0] {CAND_0}"
    assert lines[1] == f"[L1] {CAND_1}"
    assert lines[2] == f"[L2] {CAND_2}"
    print("  ✓ PASS")


def phase3_preamble_rendering() -> None:
    _sep("Phase 3 — preamble rendering")
    preamble = _build_preamble(CANDIDATES)
    print(preamble)

    lines = preamble.splitlines()
    assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"
    assert lines[0] == f"theorem L0 {CAND_0} := by admit", repr(lines[0])
    assert lines[1] == f"theorem L1 {CAND_1} := by admit", repr(lines[1])
    assert lines[2] == f"theorem L2 {CAND_2} := by admit", repr(lines[2])
    print("  ✓ PASS")


def phase4_source_with_preamble() -> None:
    _sep("Phase 4 — source rendering with preamble")
    preamble = _build_preamble(CANDIDATES[:1])   # only L0
    source = _render_source(IMPORTS, DECL, STMT, "omega", preamble)
    print(source)

    lines = source.splitlines()
    import_idx   = next(i for i, l in enumerate(lines) if l.startswith("import "))
    preamble_idx = next(i for i, l in enumerate(lines) if l.startswith("theorem L0 "))
    target_idx   = next(i for i, l in enumerate(lines) if l.startswith(f"theorem {DECL}"))

    assert import_idx < preamble_idx < target_idx, (
        f"expected import({import_idx}) < preamble({preamble_idx}) < target({target_idx})"
    )
    assert lines[import_idx]  == "import LeanSrc.Examples"
    assert lines[preamble_idx] == f"theorem L0 {CAND_0} := by admit"
    assert lines[target_idx]  == f"theorem {DECL} {STMT} := by"
    print("  ✓ PASS")


def phase5_used_lemma_parsing() -> None:
    _sep("Phase 5 — used-lemma parsing")

    assert _parse_used_lemmas("<used_lemmas>0,2</used_lemmas>", 3) == [0, 2],       "standard indices"
    assert _parse_used_lemmas("<used_lemmas>none</used_lemmas>", 3) == [],          "none"
    assert _parse_used_lemmas("<used_lemmas></used_lemmas>", 3) == [],              "empty tag"
    assert _parse_used_lemmas("no tag here", 3) == [],                             "missing tag"
    assert _parse_used_lemmas("<used_lemmas>0,5</used_lemmas>", 3) == [0],          "out-of-range dropped"
    assert _parse_used_lemmas("<used_lemmas>2,0,2</used_lemmas>", 3) == [0, 2],     "dedup + sorted"
    assert _parse_used_lemmas("<used_lemmas>0</used_lemmas>", 3) == [0],            "single index"

    print("  all assertions passed")
    print("  ✓ PASS")


def phase6_lean_check_no_candidate_use() -> None:
    _sep("Phase 6 — check_proof with preamble, proof does not use L0..L2")
    preamble = _build_preamble(CANDIDATES)
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


def phase7_lean_check_uses_l0() -> None:
    _sep("Phase 7 — check_proof with preamble, proof calls L0 directly")
    # Admit only L0 (num_hyps=1, fragment 7) and prove prop_03 by applying it
    # in the inductive step: L0 n ys x xs ih closes the cons goal directly.
    preamble = _build_preamble([CAND_0])
    proof = "\n".join([
        "induction xs with",
        "| nil => simp [count]",
        "| cons x xs ih =>",
        "  show count n (x :: xs) ≤ count n (x :: (xs ++ ys))",
        "  exact L0 n ys x xs ih",
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
        phase2_menu_rendering()
        phase3_preamble_rendering()
        phase4_source_with_preamble()
        phase5_used_lemma_parsing()
        phase6_lean_check_no_candidate_use()
        phase7_lean_check_uses_l0()
        print(f"\n{'═' * 60}")
        print("  ALL PHASES PASSED")
        print("═" * 60)
    except AssertionError as e:
        print(f"\n  ✗ FAIL: {e}", file=sys.stderr)
        sys.exit(1)
