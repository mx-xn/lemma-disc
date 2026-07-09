"""Unit tests for elaborate.py's pure logic (cache, batch rendering, output parsing,
and orchestration). No Lean toolchain required — see test_elaborate_integration.py
for the real lake env lean round trip."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lemma_generalization.elaborate import (
    _cache_path,
    _decl_name,
    _elaborate_batch,
    _fragment_id_of,
    _parse_output,
    _read_cache,
    _render_batch,
    _write_cache,
    elaborate_statements,
)
from lemma_generalization.models import Node, Statement

_DUMPTERM_SOURCE = (
    Path(__file__).resolve().parents[1] / "lean" / "DumpTerm.lean"
).read_text()


# ── decl name <-> fragment id ────────────────────────────────────────────────

class TestDeclName:
    def test_decl_name_round_trips_fragment_id(self) -> None:
        assert _fragment_id_of(_decl_name(42)) == 42

    def test_decl_name_has_expected_prefix(self) -> None:
        assert _decl_name(3) == "__gen_3"


# ── cache key / IO ────────────────────────────────────────────────────────────

class TestCache:
    def test_cache_path_stable_for_same_inputs(self, tmp_path: Path) -> None:
        a = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        b = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        assert a == b

    def test_cache_path_differs_on_statement(self, tmp_path: Path) -> None:
        a = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        b = _cache_path(tmp_path, "(n : Nat) : n = 0", ["Mod"], Path("/proj"))
        assert a != b

    def test_cache_path_differs_on_imports(self, tmp_path: Path) -> None:
        a = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        b = _cache_path(tmp_path, "(n : Nat) : n = n", ["Other"], Path("/proj"))
        assert a != b

    def test_cache_path_differs_on_lake_project(self, tmp_path: Path) -> None:
        a = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        b = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/other"))
        assert a != b

    def test_read_cache_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _read_cache(tmp_path / "nope.json") is None

    def test_write_then_read_statement_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "entry.json"
        stmt = Statement(binders=[], body=Node("List.nil", []))
        _write_cache(path, {"statement": stmt.to_dict()})
        cached = _read_cache(path)
        assert cached is not None
        assert Statement.from_dict(cached["statement"]) == stmt

    def test_write_then_read_error_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "entry.json"
        _write_cache(path, {"error": "unsupported Expr shape"})
        cached = _read_cache(path)
        assert cached == {"error": "unsupported Expr shape"}


# ── batch rendering ───────────────────────────────────────────────────────────

class TestRenderBatch:
    def test_contains_decl_for_each_lemma(self) -> None:
        source = _render_batch(
            [(3, "(l : List Nat) : Permut l l"), (7, "(n : Nat) : n = n")],
            ["Mod"],
        )
        assert "theorem __gen_3 (l : List Nat) : Permut l l := sorry" in source
        assert "theorem __gen_7 (n : Nat) : n = n := sorry" in source

    def test_imports_precede_everything_else(self) -> None:
        # DumpTerm.lean's own text starts with "import Lean", so the leading import
        # block legitimately extends past just our two project imports -- what
        # matters is that Mod1/Mod2 come first, in order, and every line before the
        # first non-import line is itself an import (nothing sneaks in between).
        source = _render_batch([(1, "(n : Nat) : n = n")], ["Mod1", "Mod2"])
        lines = [l for l in source.splitlines() if l.strip()]
        assert lines[:2] == ["import Mod1", "import Mod2"]
        first_non_import = next(i for i, l in enumerate(lines) if not l.startswith("import"))
        assert all(l.startswith("import") for l in lines[:first_non_import])

    def test_embeds_dumpterm_source_verbatim(self) -> None:
        source = _render_batch([(1, "(n : Nat) : n = n")], ["Mod"])
        assert _DUMPTERM_SOURCE in source

    def test_ends_with_dump_matching_eval(self) -> None:
        source = _render_batch([(1, "(n : Nat) : n = n")], ["Mod"])
        assert source.rstrip().endswith('#eval DumpTerm.dumpMatching "__gen_"')

    def test_empty_batch_still_well_formed(self) -> None:
        source = _render_batch([], ["Mod"])
        assert "import Mod" in source
        assert source.rstrip().endswith('#eval DumpTerm.dumpMatching "__gen_"')


# ── output parsing ────────────────────────────────────────────────────────────

class TestParseOutput:
    def test_all_succeed(self) -> None:
        raw = (
            '{"decl_name": "__gen_1", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "A", "args": []}}}\n'
            '{"decl_name": "__gen_2", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "B", "args": []}}}\n'
        )
        statements, errors = _parse_output(raw, {1, 2})
        assert errors == {}
        assert statements[1] == Statement(binders=[], body=Node("A", []))
        assert statements[2] == Statement(binders=[], body=Node("B", []))

    def test_dumpterm_caught_error_line(self) -> None:
        raw = (
            '{"decl_name": "__gen_1", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "A", "args": []}}}\n'
            '{"decl_name": "__gen_5", "error": "unsupported Expr shape: ..."}\n'
        )
        statements, errors = _parse_output(raw, {1, 5})
        assert 1 in statements
        assert 5 not in statements
        assert errors[5] == "unsupported Expr shape: ..."

    def test_decl_with_no_output_line_gets_leftover_diagnostic(self) -> None:
        raw = (
            '{"decl_name": "__gen_1", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "A", "args": []}}}\n'
            "scratch.lean:4:1: error: unknown identifier 'foo'\n"
        )
        statements, errors = _parse_output(raw, {1, 9})
        assert 1 in statements
        assert 9 not in statements
        assert "unknown identifier" in errors[9]

    def test_whole_batch_fails_on_import_error(self) -> None:
        raw = "scratch.lean:1:0: error: unknown module 'BadImport'\n"
        statements, errors = _parse_output(raw, {1, 2})
        assert statements == {}
        assert "unknown module" in errors[1]
        assert "unknown module" in errors[2]

    def test_declaration_uses_sorry_lines_ignored(self) -> None:
        raw = (
            '{"decl_name": "__gen_1", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "A", "args": []}}}\n'
            "scratch.lean:1:0: warning: declaration uses 'sorry'\n"
        )
        statements, errors = _parse_output(raw, {1})
        assert 1 in statements
        assert errors == {}

    def test_no_output_and_no_diagnostics_does_not_crash(self) -> None:
        statements, errors = _parse_output("", {1})
        assert statements == {}
        assert 1 in errors
        assert errors[1]  # non-empty fallback message, not silently dropped

    def test_all_covered_by_json_ignores_stray_unrelated_lines(self) -> None:
        # A stray line unrelated to any failure (e.g. an unrelated info line)
        # shouldn't cause a covered decl to be marked as failed.
        raw = (
            '{"decl_name": "__gen_1", "statement": '
            '{"binders": [], "body": {"kind": "node", "head": "A", "args": []}}}\n'
            "some unrelated stray line\n"
        )
        statements, errors = _parse_output(raw, {1})
        assert 1 in statements
        assert errors == {}


# ── top-level orchestration (elaborate_statements), batch runner stubbed ─────

class TestElaborateStatements:
    def test_empty_input_makes_no_batch_calls(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []
        monkeypatch.setattr(
            "lemma_generalization.elaborate._elaborate_batch",
            lambda batch, *a, **k: calls.append(batch) or ({}, {}),
        )
        statements, errors = elaborate_statements(
            {}, lake_project=Path("/proj"), imports=["Mod"], cache_dir=tmp_path
        )
        assert statements == {} and errors == {}
        assert calls == []

    def test_all_cache_hits_skip_batch_runner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        stmt = Statement(binders=[], body=Node("A", []))
        path = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        _write_cache(path, {"statement": stmt.to_dict()})

        calls: list = []
        monkeypatch.setattr(
            "lemma_generalization.elaborate._elaborate_batch",
            lambda batch, *a, **k: calls.append(batch) or ({}, {}),
        )
        statements, errors = elaborate_statements(
            {1: "(n : Nat) : n = n"},
            lake_project=Path("/proj"),
            imports=["Mod"],
            cache_dir=tmp_path,
        )
        assert statements == {1: stmt}
        assert errors == {}
        assert calls == []

    def test_all_cache_misses_batched_by_batch_size(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list = []

        def fake_batch(batch, lake_project, imports, timeout_s):
            calls.append([fid for fid, _ in batch])
            return {}, {fid: "boom" for fid, _ in batch}

        monkeypatch.setattr("lemma_generalization.elaborate._elaborate_batch", fake_batch)
        statements, errors = elaborate_statements(
            {i: f"(n : Nat) : n = {i}" for i in range(5)},
            lake_project=Path("/proj"),
            imports=["Mod"],
            cache_dir=tmp_path,
            batch_size=2,
        )
        assert len(calls) == 3  # ceil(5/2)
        assert sorted(sum(calls, [])) == list(range(5))
        assert set(errors) == set(range(5))

    def test_mixed_hits_and_misses_only_misses_batched(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        stmt = Statement(binders=[], body=Node("A", []))
        hit_path = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        _write_cache(hit_path, {"statement": stmt.to_dict()})

        calls: list = []

        def fake_batch(batch, lake_project, imports, timeout_s):
            calls.append(batch)
            return {fid: Statement(binders=[], body=Node("B", [])) for fid, _ in batch}, {}

        monkeypatch.setattr("lemma_generalization.elaborate._elaborate_batch", fake_batch)
        statements, errors = elaborate_statements(
            {1: "(n : Nat) : n = n", 2: "(n : Nat) : n = 0"},
            lake_project=Path("/proj"),
            imports=["Mod"],
            cache_dir=tmp_path,
        )
        assert statements[1] == stmt
        assert statements[2] == Statement(binders=[], body=Node("B", []))
        assert [fid for fid, _ in calls[0]] == [2]

    def test_fresh_results_written_to_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        stmt = Statement(binders=[], body=Node("A", []))

        def fake_batch(batch, lake_project, imports, timeout_s):
            return {1: stmt}, {2: "boom"}

        monkeypatch.setattr("lemma_generalization.elaborate._elaborate_batch", fake_batch)
        elaborate_statements(
            {1: "(n : Nat) : n = n", 2: "(n : Nat) : n = 0"},
            lake_project=Path("/proj"),
            imports=["Mod"],
            cache_dir=tmp_path,
        )
        ok_path = _cache_path(tmp_path, "(n : Nat) : n = n", ["Mod"], Path("/proj"))
        err_path = _cache_path(tmp_path, "(n : Nat) : n = 0", ["Mod"], Path("/proj"))
        assert Statement.from_dict(_read_cache(ok_path)["statement"]) == stmt
        assert _read_cache(err_path) == {"error": "boom"}

    def test_success_and_failure_are_mutually_exclusive(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_batch(batch, lake_project, imports, timeout_s):
            return {1: Statement(binders=[], body=Node("A", []))}, {2: "boom"}

        monkeypatch.setattr("lemma_generalization.elaborate._elaborate_batch", fake_batch)
        statements, errors = elaborate_statements(
            {1: "(n : Nat) : n = n", 2: "(n : Nat) : n = 0"},
            lake_project=Path("/proj"),
            imports=["Mod"],
            cache_dir=tmp_path,
        )
        assert set(statements) & set(errors) == set()
        assert set(statements) | set(errors) == {1, 2}
