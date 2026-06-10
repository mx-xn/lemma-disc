"""End-to-end dry-run of run() with the LLM and Lean checker stubbed out.

Patches:
  - LLM class (in both baseline.py and run.py) → FakeLLM whose .chat()
    returns a fixed <lean4_proof> response without any API call.
  - check_proof (in both prover.py and prove.py) → returns CheckResult(ok=True)
    so no Lean subprocess is spawned.

Run with:
    pytest exp/eval/sanity/test_integration.py -v
"""
from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from exp.lib.lean_check import CheckResult
from exp.lib.llm import LLMResponse

_FAKE_RESPONSE = LLMResponse(
    text="<lean4_proof>\nsorry\n</lean4_proof>",
    cached=True,
)
_FAKE_CHECK_OK = CheckResult(ok=True, error_text="")
_FAKE_CHECK_FAIL = CheckResult(ok=False, error_text="unknown tactic 'sorry'")


class FakeLLM:
    """Drop-in for exp.lib.llm.LLM — never touches the network."""

    def __init__(self, **kwargs):
        pass  # swallow model=, cache_dir=, etc.

    def chat(self, system: str, user: str) -> LLMResponse:
        return _FAKE_RESPONSE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_one_theorem(tmp_path: Path):
    """Write a minimal 1-theorem theorems.json and a matching Lemmas.lean."""
    lake_project = str(
        Path(__file__).resolve().parents[3]
        / "data" / "input" / "MiniCodePropsLeanSrc"
    )
    theorems_data = {
        "lake_project": lake_project,
        "imports": ["LeanSrc.Definitions"],
        "theorems": [
            {
                "theorem_id": "prop_29",
                "lean_path": "LeanSrc/Properties.lean",
                "statement_text": "(x: Nat) (xs: List Nat) : x ∈ ins1 x xs",
                "local_ctx": "",
            }
        ],
    }
    theorems_path = tmp_path / "theorems.json"
    theorems_path.write_text(json.dumps(theorems_data, indent=2))

    lemmas_path = tmp_path / "Lemmas.lean"
    lemmas_path.write_text(
        "lemma l1_prop_29 (x: Nat) (xs: List Nat) : x ∈ xs := by sorry\n"
    )

    return theorems_path, lemmas_path, tmp_path / "output"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_with_stubs(theorems_path, lemmas_path, output_dir, *, check_ok: bool = True):
    """Call run() with all expensive operations patched out."""
    from exp.eval.sanity.run import run

    fake_check = _FAKE_CHECK_OK if check_ok else _FAKE_CHECK_FAIL

    patches = [
        patch("exp.eval.stages.baseline.LLM", FakeLLM),
        patch("exp.eval.sanity.run.LLM", FakeLLM),
        patch("exp.lib.prover.check_proof", return_value=fake_check),
        patch("exp.eval.stages.prove.check_proof", return_value=fake_check),
    ]
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        run(
            theorems_path=theorems_path,
            lemmas_path=lemmas_path,
            output_dir=output_dir,
            llm_model="fake-model",
            max_attempts=1,
            num_workers=1,
            force=True,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_output_files_created(fixture_one_theorem):
    theorems_path, lemmas_path, output_dir = fixture_one_theorem
    _run_with_stubs(theorems_path, lemmas_path, output_dir)

    assert (output_dir / "comparison.json").exists()
    assert (output_dir / "theorems_sanity.json").exists()
    assert (output_dir / "without_lemmas" / "01_baseline.json").exists()
    assert (output_dir / "with_lemmas" / "prove_results.json").exists()


def test_comparison_structure(fixture_one_theorem):
    theorems_path, lemmas_path, output_dir = fixture_one_theorem
    _run_with_stubs(theorems_path, lemmas_path, output_dir)

    comp = json.loads((output_dir / "comparison.json").read_text())
    assert comp["total_theorems"] == 1
    assert comp["lemma_pool_size"] == 1
    assert "prop_29" in comp["per_theorem"]
    assert "without_lemmas" in comp["per_theorem"]["prop_29"]
    assert "with_lemmas" in comp["per_theorem"]["prop_29"]


def test_check_ok_both_conditions_solved(fixture_one_theorem):
    """When check_proof always succeeds, both conditions should show solved."""
    theorems_path, lemmas_path, output_dir = fixture_one_theorem
    _run_with_stubs(theorems_path, lemmas_path, output_dir, check_ok=True)

    comp = json.loads((output_dir / "comparison.json").read_text())
    assert comp["without_lemmas"]["solved"] == 1
    assert comp["with_lemmas"]["solved"] == 1


def test_check_fail_both_conditions_failed(fixture_one_theorem):
    """When check_proof always fails, both conditions should show failed."""
    theorems_path, lemmas_path, output_dir = fixture_one_theorem
    _run_with_stubs(theorems_path, lemmas_path, output_dir, check_ok=False)

    comp = json.loads((output_dir / "comparison.json").read_text())
    assert comp["without_lemmas"]["failed"] == 1
    assert comp["with_lemmas"]["failed"] == 1


def test_filtered_theorems_json(fixture_one_theorem):
    """theorems_sanity.json should contain only the matched theorem."""
    theorems_path, lemmas_path, output_dir = fixture_one_theorem
    _run_with_stubs(theorems_path, lemmas_path, output_dir)

    filtered = json.loads((output_dir / "theorems_sanity.json").read_text())
    assert len(filtered["theorems"]) == 1
    assert filtered["theorems"][0]["theorem_id"] == "prop_29"
