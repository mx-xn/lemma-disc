"""Integration tests for elaborate.py's real `lake env lean` round trip.
Requires a Lean toolchain and the MiniCodePropsLeanSrc lake project."""
from __future__ import annotations

from pathlib import Path

import pytest

from lemma_generalization.elaborate import elaborate_statements

_LAKE_PROJECT = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
_IMPORTS = ["LeanSrc.Examples"]


@pytest.mark.integration
class TestElaborateStatementsEndToEnd:
    def test_real_corpus_statement_elaborates(self, tmp_path: Path) -> None:
        statements, errors = elaborate_statements(
            {29: "(x : ℕ) : x ∈ ins1 x []"},
            lake_project=_LAKE_PROJECT,
            imports=_IMPORTS,
            cache_dir=tmp_path,
        )
        assert errors == {}
        stmt = statements[29]
        assert len(stmt.binders) == 1
        assert stmt.body.head == "Membership.mem"

    def test_second_run_hits_cache_and_skips_lean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inputs = {29: "(x : ℕ) : x ∈ ins1 x []"}
        first, first_errors = elaborate_statements(
            inputs, lake_project=_LAKE_PROJECT, imports=_IMPORTS, cache_dir=tmp_path
        )
        assert first_errors == {}

        calls: list = []
        monkeypatch.setattr(
            "lemma_generalization.elaborate._elaborate_batch",
            lambda batch, *a, **k: calls.append(batch) or ({}, {}),
        )
        second, second_errors = elaborate_statements(
            inputs, lake_project=_LAKE_PROJECT, imports=_IMPORTS, cache_dir=tmp_path
        )
        assert calls == []
        assert second == first
        assert second_errors == {}

    def test_out_of_scope_statement_reported_as_error_not_raised(self, tmp_path: Path) -> None:
        # `f n` applies a bound variable `f : Nat -> Nat` directly, rather than a
        # global constant -- resolveHeadAndExplicitArgs's throwError case in
        # DumpTerm.lean, caught by dumpMatching and surfaced as a JSON "error" line.
        statements, errors = elaborate_statements(
            {1: "(f : Nat -> Nat) (n : Nat) : f n = f n"},
            lake_project=_LAKE_PROJECT,
            imports=_IMPORTS,
            cache_dir=tmp_path,
        )
        assert 1 in errors
        assert 1 not in statements
