"""Integration tests for lean/DumpTerm.lean. Requires a Lean toolchain and lake project."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import jsonschema
import pytest

from lemma_generalization.models import Statement, term_from_dict

_LEAN_SOURCE = (Path(__file__).resolve().parents[1] / "lean" / "DumpTerm.lean").read_text()
_LAKE_PROJECT = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[2] / "schemas" / "term_tree.schema.json").read_text()
)


def _run_dump(decls: str, prefix: str = "__gen_") -> list[dict]:
    """Assembles DumpTerm.lean + decls + a trailing #eval, runs it, returns parsed JSON lines."""
    source = f'{_LEAN_SOURCE}\n{decls}\n#eval DumpTerm.dumpMatching "{prefix}"\n'
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", dir=_LAKE_PROJECT, delete=False
    ) as f:
        scratch_path = Path(f.name)
        f.write(source)

    try:
        proc = subprocess.run(
            ["lake", "env", "lean", scratch_path.name],
            cwd=_LAKE_PROJECT,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        scratch_path.unlink(missing_ok=True)

    results: list[dict] = []
    unexpected: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            results.append(json.loads(line))
        elif "declaration uses" not in line:
            unexpected.append(line)
    assert not unexpected, "unexpected Lean diagnostics:\n" + "\n".join(unexpected)
    return results


def _statement_of(line: dict) -> Statement:
    assert "error" not in line, f"conversion failed: {line['error']}"
    return Statement.from_dict(line["statement"])


@pytest.mark.integration
class TestExprToTerm:
    def test_bare_data_type_conclusion_no_binders(self) -> None:
        from lemma_generalization.models import Node

        [line] = _run_dump(
            """
            inductive Permut : List Nat -> List Nat -> Prop where
              | refl (l : List Nat) : Permut l l
            theorem __gen_0 : Permut ([] : List Nat) [] := sorry
            """
        )
        assert line["decl_name"] == "__gen_0"
        stmt = _statement_of(line)
        nil = Node("List.nil", [])
        assert stmt == Statement(binders=[], body=Node("Permut", [nil, nil]))

    def test_design_docs_running_example_single_binder(self) -> None:
        [line] = _run_dump(
            """
            inductive Permut : List Nat -> List Nat -> Prop where
              | refl (l : List Nat) : Permut l l
            theorem __gen_1 (l : List Nat) : Permut l l := sorry
            """
        )
        stmt = _statement_of(line)
        assert len(stmt.binders) == 1
        assert stmt.binders[0].display_name == "l"
        assert stmt.body.head == "Permut"
        assert stmt.body.args[0] == stmt.body.args[1]
        from lemma_generalization.models import Var
        assert stmt.body.args[0] == Var(0, "l")

    def test_multi_binder_cons_chain_matches_stage1_fixture(self) -> None:
        from lemma_generalization.models import Binder, Node, Var

        [line] = _run_dump(
            """
            inductive Permut : List Nat -> List Nat -> Prop where
              | refl (l : List Nat) : Permut l l
            theorem __gen_3 (e x : Nat) (xs : List Nat) :
                Permut (e :: x :: xs) (e :: x :: xs) := sorry
            """
        )
        stmt = _statement_of(line)
        nat = Node("Nat", [])
        cons_chain = Node("List.cons", [Var(2, "e"), Node("List.cons", [Var(1, "x"), Var(0, "xs")])])
        expected = Statement(
            binders=[
                Binder("e", nat, False),
                Binder("x", nat, False),
                Binder("xs", Node("List", [nat]), False),
            ],
            body=Node("Permut", [cons_chain, cons_chain]),
        )
        assert stmt == expected

    def test_nested_pi_in_binder_type(self) -> None:
        from lemma_generalization.models import Binder, Node, Pi, Var

        [line] = _run_dump(
            """
            theorem __gen_5 (ih : forall (n : Nat), n = n) (m : Nat) : m = m := sorry
            """
        )
        stmt = _statement_of(line)
        nat = Node("Nat", [])
        expected = Statement(
            binders=[
                Binder("ih", Pi("n", nat, Node("Eq", [Var(0, "n"), Var(0, "n")]), False), False),
                Binder("m", nat, False),
            ],
            body=Node("Eq", [Var(0, "m"), Var(0, "m")]),
        )
        assert stmt == expected

    def test_non_dependent_arrow_premise_stays_plain_node(self) -> None:
        from lemma_generalization.models import Binder, Node

        [line] = _run_dump(
            """
            theorem __gen_6 (x y : Nat) (hle : ¬ x <= y) : True := sorry
            """
        )
        stmt = _statement_of(line)
        # `hle`'s type must be a plain Node("Not", [...]), never a Pi -- Lean doesn't
        # unfold `Not`'s definition during elaboration.
        hle_binder = stmt.binders[2]
        assert isinstance(hle_binder.type, Node)
        assert hle_binder.type.head == "Not"

    def test_expr_lit_numeral(self) -> None:
        [line] = _run_dump(
            """
            theorem __gen_9 (n : Nat) : n + 0 = n := sorry
            """
        )
        stmt = _statement_of(line)
        assert stmt.body.head == "Eq"


@pytest.mark.integration
class TestDumpMatching:
    def test_batch_attribution_and_prefix_filtering(self) -> None:
        lines = _run_dump(
            """
            theorem __gen_1 (n : Nat) : n = n := sorry
            theorem __gen_5 (n : Nat) : n = n := sorry
            theorem __gen_9 (n : Nat) : n = n := sorry
            def helper : Nat := 0
            """
        )
        names = {line["decl_name"] for line in lines}
        assert names == {"__gen_1", "__gen_5", "__gen_9"}
        for line in lines:
            assert "error" not in line

    def test_deterministic_ordering(self) -> None:
        decls = """
            theorem __gen_1 (n : Nat) : n = n := sorry
            theorem __gen_5 (n : Nat) : n = n := sorry
            theorem __gen_9 (n : Nat) : n = n := sorry
            """
        first = _run_dump(decls)
        second = _run_dump(decls)
        assert [l["decl_name"] for l in first] == [l["decl_name"] for l in second]


@pytest.mark.integration
class TestSchemaConformance:
    def test_every_emitted_statement_validates(self) -> None:
        lines = _run_dump(
            """
            inductive Permut : List Nat -> List Nat -> Prop where
              | refl (l : List Nat) : Permut l l
            theorem __gen_1 (l : List Nat) : Permut l l := sorry
            theorem __gen_2 (ih : forall (n : Nat), n = n) (m : Nat) : m = m := sorry
            """
        )
        for line in lines:
            jsonschema.validate(line["statement"], _SCHEMA)
