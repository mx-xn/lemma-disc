"""Tests for exp.eval.stages.extract and exp.eval.stages.prove.

Covers the pure, LLM/Lean-free logic:
  - _indent edge cases
  - _extract_failing_line_content: caret-line parsing from lean_check error format
  - _admit_patch: proof body patching, fallback to None when no patch possible
  - build_corpus: sorry vs proof-body selection, admit-patching, indentation,
    local_ctx, file naming
  - _build_hint_preamble / _build_hint_block: empty, single, multi
  - _render_first / _render_fix: placeholder substitution and proof-body indentation
  - prove_round: JSON schema includes raw_response (monkeypatched, no LLM/Lean)

Run from the repo root:
    pytest exp/eval/test_stages.py
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from exp.eval.stages import prove as prove_mod
from exp.eval.stages.extract import (
    _admit_patch,
    _extract_failing_line_content,
    _indent,
    build_corpus,
)
from exp.eval.stages.prove import (
    Attempt,
    RoundResult,
    _build_hint_block,
    _build_hint_preamble,
    _extract_used_indices,
    _render_first,
    _render_fix,
)
from exp.lib.corpus import Theorem


# ---------------------------------------------------------------------------
# Stub result types (duck-typed; build_corpus uses Any internally)
# ---------------------------------------------------------------------------

@dataclass
class _FakeAttempt:
    proof_body: str
    error_text: str = ""


@dataclass
class _FakeResult:
    ok: bool
    attempts: list[_FakeAttempt] = field(default_factory=list)
    final_error: str = ""


def _thm(theorem_id: str, statement_text: str, local_ctx: str = "") -> Theorem:
    return Theorem(
        theorem_id=theorem_id,
        lean_path="",
        statement_text=statement_text,
        local_ctx=local_ctx,
    )


# ===========================================================================
# _indent
# ===========================================================================

class TestIndent:
    def test_single_line(self):
        assert _indent("exact h") == "  exact h"

    def test_multiline_each_line_prefixed(self):
        assert _indent("intro h\nexact h") == "  intro h\n  exact h"

    def test_empty_string_returns_sorry(self):
        assert _indent("") == "  sorry"

    def test_whitespace_only_returns_sorry(self):
        assert _indent("   ") == "  sorry"

    def test_newline_only_returns_sorry(self):
        assert _indent("\n") == "  sorry"

    def test_mixed_whitespace_only_returns_sorry(self):
        assert _indent("  \n  \n  ") == "  sorry"

    def test_empty_line_in_middle_padded_not_dropped(self):
        # An empty line inside a proof body should become "  " (just the pad),
        # preserving structure so Lean can parse multi-case proofs.
        result = _indent("case l =>\n  rfl\n\ncase r =>\n  rfl")
        lines = result.splitlines()
        assert lines[2] == "  "  # empty line becomes pad-only, not skipped

    def test_custom_spaces(self):
        assert _indent("simp", spaces=4) == "    simp"

    def test_trailing_newline_not_doubled(self):
        # "exact h\n".splitlines() == ["exact h"], so no phantom empty line appended.
        result = _indent("exact h\n")
        assert result == "  exact h"


# ===========================================================================
# _extract_failing_line_content
# ===========================================================================

def _snippet_error(prev_tactic: str, failing_tactic: str, *, col_offset: int = 2) -> str:
    """Build a lean_check.format_error-style block for a single failing line.

    col_offset is the column within the source line where the caret sits
    (default 2 = after the 2-space proof-body indent that render_source adds).
    """
    return (
        f"location:\n"
        f"    {prev_tactic}\n"
        f"    {failing_tactic}\n"
        f"    {' ' * col_offset}^\n"
        f"error: failed to synthesize"
    )


class TestExtractFailingLineContent:
    def test_empty_error_text_returns_empty(self):
        assert _extract_failing_line_content("") == []

    def test_no_caret_lines_returns_empty(self):
        assert _extract_failing_line_content("some error text\nno location markers") == []

    def test_single_error_extracts_failing_tactic(self):
        # proof body line "simp [h]" is rendered as "  simp [h]" in source,
        # appearing in the snippet as "    " + "  simp [h]"
        error = _snippet_error("  intro h", "  simp [h]")
        result = _extract_failing_line_content(error)
        assert result == ["simp [h]"]

    def test_multiple_errors_all_extracted_in_order(self):
        block1 = _snippet_error("  intro h", "  simp [h]")
        block2 = _snippet_error("  simp [h]", "  exact bad_lemma")
        error = block1 + "\n\n" + block2
        result = _extract_failing_line_content(error)
        assert result == ["simp [h]", "exact bad_lemma"]

    def test_duplicates_deduplicated_first_occurrence_kept(self):
        block = _snippet_error("  intro h", "  simp [h]")
        error = block + "\n\n" + block
        result = _extract_failing_line_content(error)
        assert result == ["simp [h]"]

    def test_deeply_indented_tactic_stripped_correctly(self):
        # "    simp" is 4-space indented in the proof body → 6-space in source
        # → 10-space in snippet; caret at col_offset=4
        error = _snippet_error("    case a =>", "    simp [h]", col_offset=4)
        result = _extract_failing_line_content(error)
        assert result == ["simp [h]"]

    def test_caret_with_extra_spaces_still_matches(self):
        # caret offset of 8 → 8 trailing spaces before ^ in the caret line
        error = _snippet_error("  intro n", "  omega", col_offset=8)
        result = _extract_failing_line_content(error)
        assert result == ["omega"]


# ===========================================================================
# _admit_patch
# ===========================================================================

class TestAdmitPatch:
    def test_empty_error_text_returns_none(self):
        assert _admit_patch("simp [h]", "") is None

    def test_proof_contains_sorry_returns_none(self):
        assert _admit_patch("sorry", "proof contains sorry") is None

    def test_proof_contains_admit_returns_none(self):
        assert _admit_patch("admit", "proof contains admit") is None

    def test_no_caret_lines_returns_none(self):
        assert _admit_patch("simp [h]", "unknown error text") is None

    def test_no_matching_line_in_proof_body_returns_none(self):
        error = _snippet_error("  intro h", "  simp [h]")
        # proof body does not contain "simp [h]"
        assert _admit_patch("intro h\nexact rfl", error) is None

    def test_matching_line_replaced_with_admit(self):
        error = _snippet_error("  intro h", "  simp [h]")
        result = _admit_patch("intro h\nsimp [h]", error)
        assert result == "intro h\nadmit"

    def test_indentation_preserved_in_patched_line(self):
        # proof body line has 4-space indent; in source it's 6-space; in snippet 10-space
        error = _snippet_error("    case a =>", "    simp [h]", col_offset=4)
        result = _admit_patch("  case a =>\n    simp [h]", error)
        assert result == "  case a =>\n    admit"

    def test_multiple_failing_lines_all_replaced(self):
        block1 = _snippet_error("  intro h", "  simp [h]")
        block2 = _snippet_error("  simp [h]", "  exact bad")
        error = block1 + "\n\n" + block2
        result = _admit_patch("simp [h]\nexact bad\nother_tactic", error)
        assert result == "admit\nadmit\nother_tactic"

    def test_non_failing_lines_unchanged(self):
        error = _snippet_error("  intro h", "  simp [h]")
        result = _admit_patch("intro h\nsimp [h]\nexact rfl", error)
        assert result is not None
        lines = result.splitlines()
        assert lines[0] == "intro h"
        assert lines[1] == "admit"
        assert lines[2] == "exact rfl"


# ===========================================================================
# build_corpus — admit-patching for unsolved theorems
# ===========================================================================

class TestBuildCorpusAdmitPatch:
    def _err(self, tactic: str) -> str:
        return _snippet_error("  intro h", f"  {tactic}")

    def test_unsolved_with_error_info_uses_admit_patched_body(self):
        thm = _thm("prop_10", "(n : Nat) : n = n")
        result = _FakeResult(
            ok=False,
            attempts=[_FakeAttempt("intro h\nsimp [wrong]")],
            final_error=self._err("simp [wrong]"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_10": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_10.lean").read_text()
        assert "admit" in content
        assert "intro h" in content
        assert "simp [wrong]" not in content

    def test_unsolved_no_error_info_falls_back_to_sorry(self):
        thm = _thm("prop_11", "(n : Nat) : n = n")
        result = _FakeResult(
            ok=False,
            attempts=[_FakeAttempt("simp [wrong]")],
            final_error="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_11": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_11.lean").read_text()
        assert "sorry" in content
        assert "simp [wrong]" not in content

    def test_unsolved_proof_contains_sorry_error_falls_back_to_sorry(self):
        thm = _thm("prop_12", "(n : Nat) : n = n")
        result = _FakeResult(
            ok=False,
            attempts=[_FakeAttempt("intro h\nsorry")],
            final_error="proof contains sorry",
        )
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_12": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_12.lean").read_text()
        assert "sorry" in content

    def test_admit_patch_preserves_non_failing_tactics(self):
        thm = _thm("prop_13", "(n : Nat) : n = n")
        result = _FakeResult(
            ok=False,
            attempts=[_FakeAttempt("intro n\nexact bad_lemma")],
            final_error=self._err("exact bad_lemma"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_13": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_13.lean").read_text()
        assert "intro n" in content
        assert "admit" in content
        assert "exact bad_lemma" not in content


# ===========================================================================
# build_corpus — sorry vs proof-body selection
# ===========================================================================

class TestBuildCorpusSorryVsProofBody:
    def test_solved_theorem_uses_proof_body(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        result = _FakeResult(ok=True, attempts=[_FakeAttempt("rfl")])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_01": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        assert "rfl" in content
        assert "sorry" not in content

    def test_theorem_absent_from_results_uses_sorry(self):
        thm = _thm("prop_02", "(n : Nat) : n = n")
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_02.lean").read_text()
        assert "sorry" in content

    def test_ok_false_no_error_info_falls_back_to_sorry(self):
        """ok=False with no error info: fallback is sorry, not the failed proof body."""
        thm = _thm("prop_03", "(n : Nat) : n = n")
        result = _FakeResult(ok=False, attempts=[_FakeAttempt("wrong_tactic")])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_03": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_03.lean").read_text()
        assert "sorry" in content
        assert "wrong_tactic" not in content

    def test_ok_true_empty_attempts_uses_sorry_no_crash(self):
        """result.ok=True with attempts=[] must not crash and must yield sorry."""
        thm = _thm("prop_04", "(n : Nat) : n = n")
        result = _FakeResult(ok=True, attempts=[])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_04": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_04.lean").read_text()
        assert "sorry" in content

    def test_uses_last_attempt_not_first(self):
        """Multiple attempts in a solved theorem: only the last proof body is used."""
        thm = _thm("prop_05", "(n : Nat) : n = n")
        result = _FakeResult(ok=True, attempts=[
            _FakeAttempt("first_wrong"),
            _FakeAttempt("second_correct"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_05": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_05.lean").read_text()
        assert "second_correct" in content
        assert "first_wrong" not in content


# ===========================================================================
# build_corpus — indentation of proof body
# ===========================================================================

class TestBuildCorpusIndentation:
    def test_sorry_is_2_space_indented(self):
        thm = _thm("prop_06", "(n : Nat) : n = n")
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_06.lean").read_text()
        lines = content.splitlines()
        by_idx = next(i for i, l in enumerate(lines) if ":= by" in l)
        assert lines[by_idx + 1] == "  sorry", (
            f"Expected '  sorry' after ':= by', got {lines[by_idx + 1]!r}"
        )

    def test_single_line_proof_2_space_indented(self):
        thm = _thm("prop_07", "(n : Nat) : n = n")
        result = _FakeResult(ok=True, attempts=[_FakeAttempt("rfl")])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_07": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_07.lean").read_text()
        lines = content.splitlines()
        by_idx = next(i for i, l in enumerate(lines) if ":= by" in l)
        assert lines[by_idx + 1] == "  rfl", (
            f"Expected '  rfl' after ':= by', got {lines[by_idx + 1]!r}"
        )

    def test_multiline_proof_every_line_2_space_indented(self):
        thm = _thm("prop_08", "(n m : Nat) : n + m = m + n")
        result = _FakeResult(ok=True, attempts=[
            _FakeAttempt("intro n m\nexact Nat.add_comm n m")
        ])
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({"prop_08": result}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_08.lean").read_text()
        lines = content.splitlines()
        by_idx = next(i for i, l in enumerate(lines) if ":= by" in l)
        proof_lines = [l for l in lines[by_idx + 1:] if l.strip()]
        assert proof_lines == ["  intro n m", "  exact Nat.add_comm n m"], proof_lines


# ===========================================================================
# build_corpus — file structure and naming
# ===========================================================================

class TestBuildCorpusStructure:
    def test_file_named_by_theorem_id(self):
        thm = _thm("my_thm_42", "(n : Nat) : n = n")
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            assert (cdir / "my_thm_42.lean").exists()

    def test_corpus_is_subdir_of_work_dir(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "round_01"
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], work_dir)
            assert cdir == work_dir / "corpus"
            assert cdir.is_dir()

    def test_imports_each_on_own_line(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        imports = ["Mathlib", "Init.Data.Nat.Basic"]
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), imports, Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        assert "import Mathlib" in content
        assert "import Init.Data.Nat.Basic" in content
        # Both must appear on separate lines
        lines = content.splitlines()
        assert any(l == "import Mathlib" for l in lines)
        assert any(l == "import Init.Data.Nat.Basic" for l in lines)

    def test_theorem_declaration_present(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        assert "theorem prop_01 (n : Nat) : n = n := by" in content

    def test_with_local_ctx_appears_before_theorem(self):
        ctx = "def helper : Nat := 42"
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx=ctx)
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        assert ctx in content
        assert content.index(ctx) < content.index("theorem prop_01")

    def test_local_ctx_separated_from_theorem_by_blank_line(self):
        ctx = "def helper : Nat := 42"
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx=ctx)
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        # The two must be separated by at least one blank line
        between = content[content.index(ctx) + len(ctx): content.index("theorem prop_01")]
        assert "\n\n" in between, f"Expected blank line between local_ctx and theorem, got {between!r}"

    def test_whitespace_only_local_ctx_not_included(self):
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx="   \n  ")
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus({}, [thm], Path("/x"), ["Mathlib"], Path(tmp))
            content = (cdir / "prop_01.lean").read_text()
        # The only non-empty content before theorem should be the import
        before_thm = content[: content.index("theorem prop_01")]
        non_empty_before = [l for l in before_thm.splitlines() if l.strip()]
        assert all(l.startswith("import ") for l in non_empty_before), (
            f"Unexpected non-import lines before theorem: {non_empty_before}"
        )

    def test_multiple_theorems_one_file_each(self):
        thms = [_thm("thm_a", "(a : Nat) : a = a"), _thm("thm_b", "(b : Nat) : b = b")]
        results = {"thm_a": _FakeResult(ok=True, attempts=[_FakeAttempt("rfl")])}
        with tempfile.TemporaryDirectory() as tmp:
            cdir = build_corpus(results, thms, Path("/x"), ["Mathlib"], Path(tmp))
            ca = (cdir / "thm_a.lean").read_text()
            cb = (cdir / "thm_b.lean").read_text()
        assert "rfl" in ca and "sorry" not in ca
        assert "sorry" in cb and "rfl" not in cb


# ===========================================================================
# _build_hint_preamble
# ===========================================================================

class TestHintPreamble:
    def test_empty_pool_returns_empty_string(self):
        assert _build_hint_preamble([]) == ""

    def test_single_lemma(self):
        result = _build_hint_preamble(["(h : P) : P"])
        assert result == "theorem lemma_hint_0 (h : P) : P := by admit"

    def test_multiple_lemmas_numbered_consecutively(self):
        stmts = ["(h : P) : P", "(h : Q) : Q", "(h : R) : R"]
        result = _build_hint_preamble(stmts)
        lines = result.splitlines()
        assert len(lines) == 3
        assert "lemma_hint_0" in lines[0] and stmts[0] in lines[0]
        assert "lemma_hint_1" in lines[1] and stmts[1] in lines[1]
        assert "lemma_hint_2" in lines[2] and stmts[2] in lines[2]

    def test_all_lines_end_with_by_admit(self):
        result = _build_hint_preamble(["(h : P) : P", "(h : Q) : Q"])
        for line in result.splitlines():
            assert line.endswith(":= by admit"), line


# ===========================================================================
# _build_hint_block
# ===========================================================================

class TestHintBlock:
    def test_empty_pool_returns_empty_string(self):
        assert _build_hint_block([]) == ""

    def test_single_lemma_4_space_indent(self):
        result = _build_hint_block(["(h : P) : P"])
        assert result.startswith("    ")
        assert "lemma_hint_0" in result
        assert "(h : P) : P" in result

    def test_all_lines_4_space_indented(self):
        result = _build_hint_block(["(h : P) : P", "(h : Q) : Q"])
        for line in result.splitlines():
            assert line.startswith("    "), f"Line not 4-space indented: {line!r}"

    def test_preamble_has_no_indent_block_has_indent(self):
        """Preamble and block are distinct: preamble has no leading spaces."""
        stmts = ["(h : P) : P"]
        preamble = _build_hint_preamble(stmts)
        block = _build_hint_block(stmts)
        assert not preamble.startswith(" ")
        assert block.startswith("    ")


# ===========================================================================
# _render_first — placeholder substitution
# ===========================================================================

class TestRenderFirst:
    def test_no_placeholder_tokens_remain(self):
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx="-- some ctx")
        result = _render_first(thm, ["Mathlib"], ["(h : P) : P"])
        for token in ("<<imports>>", "<<local_ctx>>", "<<statement>>", "<<hints>>"):
            assert token not in result, f"Unreplaced token {token!r} found in rendered prompt"

    def test_imports_appear(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        result = _render_first(thm, ["Mathlib", "Init"], [])
        assert "Mathlib" in result
        assert "Init" in result

    def test_statement_appears(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        result = _render_first(thm, ["Mathlib"], [])
        assert "(n : Nat) : n = n" in result

    def test_local_ctx_appears(self):
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx="def foo := 1")
        result = _render_first(thm, ["Mathlib"], [])
        assert "def foo := 1" in result

    def test_hints_appear_as_numbered_theorems(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        result = _render_first(thm, ["Mathlib"], ["(h : P) : P", "(h : Q) : Q"])
        assert "lemma_hint_0" in result
        assert "lemma_hint_1" in result

    def test_empty_pool_no_hint_stubs_in_output(self):
        # No admitted hint *declarations* (theorem lemma_hint_N ... := by admit) when pool is empty.
        thm = _thm("prop_01", "(n : Nat) : n = n")
        result = _render_first(thm, ["Mathlib"], [])
        assert "theorem lemma_hint_" not in result


# ===========================================================================
# _render_fix — placeholder substitution and proof body indentation
# ===========================================================================

class TestRenderFix:
    def test_no_placeholder_tokens_remain(self):
        thm = _thm("prop_01", "(n : Nat) : n = n", local_ctx="-- ctx")
        last = Attempt(proof_body="rfl", ok=False, error_text="type mismatch")
        result = _render_fix(thm, ["Mathlib"], ["(h : P) : P"], last)
        for token in ("<<imports>>", "<<local_ctx>>", "<<statement>>", "<<hints>>",
                      "<<proof_body>>", "<<error>>"):
            assert token not in result, f"Unreplaced token {token!r} in rendered fix prompt"

    def test_error_text_appears(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        last = Attempt(proof_body="rfl", ok=False, error_text="type mismatch at line 3")
        result = _render_fix(thm, ["Mathlib"], [], last)
        assert "type mismatch at line 3" in result

    def test_proof_body_lines_are_2_space_indented(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        last = Attempt(proof_body="intro h\nexact h", ok=False, error_text="err")
        result = _render_fix(thm, ["Mathlib"], [], last)
        assert "  intro h" in result
        assert "  exact h" in result

    def test_empty_proof_body_does_not_crash(self):
        """Empty proof body: splitlines() returns [], fallback to [''] → one indented blank line."""
        thm = _thm("prop_01", "(n : Nat) : n = n")
        last = Attempt(proof_body="", ok=False, error_text="err")
        result = _render_fix(thm, ["Mathlib"], [], last)
        # Should not raise; the <<proof_body>> token should be replaced.
        assert "<<proof_body>>" not in result

    def test_hints_appear_in_fix_prompt(self):
        thm = _thm("prop_01", "(n : Nat) : n = n")
        last = Attempt(proof_body="rfl", ok=False, error_text="err")
        result = _render_fix(thm, ["Mathlib"], ["(h : P) : P"], last)
        assert "lemma_hint_0" in result


# ===========================================================================
# _extract_used_indices
# ===========================================================================

class TestExtractUsedIndices:
    def test_empty_proof_returns_empty(self):
        assert _extract_used_indices("", 5) == []

    def test_no_hints_in_proof(self):
        assert _extract_used_indices("exact rfl", 5) == []

    def test_single_hint(self):
        assert _extract_used_indices("exact lemma_hint_2 h", 5) == [2]

    def test_multiple_hints_sorted(self):
        assert _extract_used_indices("apply lemma_hint_2\nexact lemma_hint_0 rfl", 5) == [0, 2]

    def test_duplicate_appearances_deduplicated(self):
        body = "apply lemma_hint_1\nsimp [lemma_hint_1]"
        assert _extract_used_indices(body, 5) == [1]

    def test_substring_not_matched(self):
        # lemma_hint_1 must NOT match inside lemma_hint_10
        body = "exact lemma_hint_10"
        assert _extract_used_indices(body, 20) == [10]
        assert 1 not in _extract_used_indices(body, 20)

    def test_index_at_pool_boundary_excluded(self):
        # pool_size=3 means valid indices are 0,1,2; index 3 is out of bounds
        assert _extract_used_indices("exact lemma_hint_3", 3) == []

    def test_index_within_pool_included(self):
        assert _extract_used_indices("exact lemma_hint_0", 1) == [0]

    def test_hint_at_end_of_string(self):
        assert _extract_used_indices("exact lemma_hint_0", 5) == [0]

    def test_hint_followed_by_dot(self):
        # Lean method-call syntax: lemma_hint_0.apply
        assert _extract_used_indices("lemma_hint_0.apply", 5) == [0]


# ===========================================================================
# prove_round — JSON schema (monkeypatched, no LLM/Lean)
# ===========================================================================

class TestProveRoundSchema:
    def test_raw_response_and_used_indices_serialized(self, tmp_path, monkeypatch):
        """prove_results.json includes raw_response and used_indices on each attempt."""
        fixed = RoundResult(
            ok=True,
            attempts=[Attempt(
                proof_body="exact lemma_hint_0 rfl",
                ok=True,
                error_text="",
                raw_response="<lean4_proof>exact lemma_hint_0 rfl</lean4_proof>",
                used_indices=[0],
            )],
        )
        monkeypatch.setattr(prove_mod, "_run_prove_loop", lambda *a, **kw: fixed)

        thm = _thm("t1", "(n : Nat) : n = n")
        prove_mod.prove_round([thm], ["(h : P) : P"], None, Path("/fake"), [], 1, tmp_path)

        artifact = json.loads((tmp_path / prove_mod.PROVE_RESULTS_JSON).read_text())
        rec = artifact["results"]["t1"]["attempts"][0]
        assert rec["used_indices"] == [0]
        assert rec["raw_response"] == "<lean4_proof>exact lemma_hint_0 rfl</lean4_proof>"
        assert rec["proof_body"] == "exact lemma_hint_0 rfl"

    def test_json_top_level_fields_present(self, tmp_path, monkeypatch):
        """Artifact has lake_project, imports, and results at the top level."""
        monkeypatch.setattr(
            prove_mod, "_run_prove_loop",
            lambda *a, **kw: RoundResult(ok=False, attempts=[], final_error="err"),
        )
        thm = _thm("t1", "(n : Nat) : n = n")
        prove_mod.prove_round([thm], [], None, Path("/proj"), ["Mathlib"], 1, tmp_path)

        artifact = json.loads((tmp_path / prove_mod.PROVE_RESULTS_JSON).read_text())
        assert "lake_project" in artifact
        assert artifact["imports"] == ["Mathlib"]
        assert "t1" in artifact["results"]
