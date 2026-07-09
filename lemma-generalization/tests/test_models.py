import json
from pathlib import Path

import pytest

from lemma_generalization.models import (
    Binder,
    Node,
    Pi,
    Statement,
    Var,
    term_from_dict,
    term_to_dict,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "term_tree.schema.json"


class TestVar:
    def test_eq_ignores_display_name(self) -> None:
        assert Var(0, "x") == Var(0, "y")

    def test_eq_differs_on_index(self) -> None:
        assert Var(0, "x") != Var(1, "x")

    def test_hash_ignores_display_name(self) -> None:
        assert hash(Var(0, "x")) == hash(Var(0, "y"))


class TestNode:
    def test_eq_nullary(self) -> None:
        assert Node("List.nil", []) == Node("List.nil", [])

    def test_eq_differs_on_head(self) -> None:
        assert Node("List.nil", []) != Node("List.cons", [])

    def test_eq_differs_on_arity(self) -> None:
        assert Node("f", [Var(0, "x")]) != Node("f", [])

    def test_eq_is_order_sensitive(self) -> None:
        a, b = Var(0, "a"), Var(1, "b")
        assert Node("f", [a, b]) != Node("f", [b, a])

    def test_eq_ignores_display_name_at_every_depth(self) -> None:
        left = Node("List.cons", [Var(0, "e"), Node("List.nil", [])])
        right = Node("List.cons", [Var(0, "x"), Node("List.nil", [])])
        assert left == right

    def test_hash_matches_nested_eq(self) -> None:
        left = Node("List.cons", [Var(0, "e"), Node("List.nil", [])])
        right = Node("List.cons", [Var(0, "x"), Node("List.nil", [])])
        assert hash(left) == hash(right)

    def test_var_and_node_never_equal(self) -> None:
        assert Var(0, "x") != Node("x", [])


class TestPi:
    def test_eq_ignores_display_name(self) -> None:
        nat = Node("Nat", [])
        assert Pi("n", nat, Node("P", [Var(0, "n")]), False) == Pi(
            "m", nat, Node("P", [Var(0, "m")]), False
        )

    def test_eq_differs_on_domain(self) -> None:
        body = Node("P", [Var(0, "n")])
        assert Pi("n", Node("Nat", []), body, False) != Pi("n", Node("Int", []), body, False)

    def test_eq_differs_on_body(self) -> None:
        nat = Node("Nat", [])
        assert Pi("n", nat, Node("P", [Var(0, "n")]), False) != Pi(
            "n", nat, Node("Q", [Var(0, "n")]), False
        )

    def test_eq_differs_on_implicit(self) -> None:
        nat = Node("Nat", [])
        body = Node("P", [Var(0, "n")])
        assert Pi("n", nat, body, True) != Pi("n", nat, body, False)

    def test_hash_matches_eq(self) -> None:
        nat = Node("Nat", [])
        left = Pi("n", nat, Node("P", [Var(0, "n")]), False)
        right = Pi("m", nat, Node("P", [Var(0, "m")]), False)
        assert hash(left) == hash(right)

    def test_pi_var_node_mutually_exclusive(self) -> None:
        pi = Pi("n", Node("Nat", []), Node("P", [Var(0, "n")]), False)
        assert pi != Var(0, "n")
        assert Var(0, "n") != pi
        assert pi != Node("n", [])
        assert Node("n", []) != pi


class TestBinder:
    def test_eq_ignores_display_name(self) -> None:
        nat = Node("Nat", [])
        assert Binder("n", nat, False) == Binder("m", nat, False)

    def test_eq_differs_on_implicit(self) -> None:
        nat = Node("Nat", [])
        assert Binder("n", nat, True) != Binder("n", nat, False)

    def test_eq_differs_on_type(self) -> None:
        assert Binder("n", Node("Nat", []), False) != Binder("n", Node("Int", []), False)

    def test_eq_ignores_display_name_with_pi_type(self) -> None:
        # ih : ∀ (n : ℕ), P n -- alpha-renaming n inside ih's own Pi shouldn't matter.
        nat = Node("Nat", [])
        left = Binder("ih", Pi("n", nat, Node("P", [Var(0, "n")]), False), False)
        right = Binder("hyp", Pi("m", nat, Node("P", [Var(0, "m")]), False), False)
        assert left == right


def _permut_cons_statement(e_name: str, x_name: str, xs_name: str) -> Statement:
    # (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs)
    # T's binder omitted for brevity (irrelevant to the equality being tested).
    cons_chain = Node("List.cons", [Var(2, e_name),
                       Node("List.cons", [Var(1, x_name), Var(0, xs_name)])])
    return Statement(
        binders=[
            Binder(e_name, Node("T", []), False),
            Binder(x_name, Node("T", []), False),
            Binder(xs_name, Node("List", [Node("T", [])]), False),
        ],
        body=Node("Permut", [cons_chain, cons_chain]),
    )


def _ih_statement(ih_name: str, pi_bound_name: str, domain_head: str = "Nat") -> Statement:
    # (ih : forall (n : Nat), f n = g n) (n : Nat) : P n
    domain = Node(domain_head, [])
    ih_type = Pi(
        pi_bound_name,
        domain,
        Node("Eq", [Node("f", [Var(0, pi_bound_name)]), Node("g", [Var(0, pi_bound_name)])]),
        False,
    )
    return Statement(
        binders=[Binder(ih_name, ih_type, False), Binder("n", Node("Nat", []), False)],
        body=Node("P", [Var(0, "n")]),
    )


class TestStatement:
    def test_eq_ignores_display_name_throughout(self) -> None:
        assert _permut_cons_statement("e", "x", "xs") == _permut_cons_statement("a", "b", "c")

    def test_eq_differs_on_binder_count(self) -> None:
        full = _permut_cons_statement("e", "x", "xs")
        fewer = Statement(binders=full.binders[:-1], body=full.body)
        assert full != fewer

    def test_eq_differs_on_body(self) -> None:
        full = _permut_cons_statement("e", "x", "xs")
        different_body = Statement(binders=full.binders, body=Node("List.nil", []))
        assert full != different_body

    def test_hashable_and_usable_as_dict_key(self) -> None:
        d = {_permut_cons_statement("e", "x", "xs"): "cons-case"}
        assert d[_permut_cons_statement("a", "b", "c")] == "cons-case"

    def test_eq_alpha_equivalent_with_nested_pi(self) -> None:
        assert _ih_statement("ih", "n") == _ih_statement("hyp", "m")

    def test_eq_differs_on_pi_domain(self) -> None:
        assert _ih_statement("ih", "n", "Nat") != _ih_statement("ih", "n", "Int")


class TestSerialization:
    def test_round_trip_preserves_structure_and_display_names(self) -> None:
        original = _permut_cons_statement("e", "x", "xs")
        restored = Statement.from_dict(original.to_dict())
        assert restored == original
        assert restored.binders[0].display_name == "e"
        assert restored.binders[2].display_name == "xs"
        # body's first cons-chain's inner Var references xs by display_name too.
        inner_var = restored.body.args[0].args[1].args[1]
        assert inner_var.display_name == "xs"

    def test_from_dict_raises_on_unknown_kind(self) -> None:
        with pytest.raises(ValueError):
            term_from_dict({"kind": "bogus"})

    def test_round_trip_pi(self) -> None:
        original = Pi("n", Node("Nat", []), Node("P", [Var(0, "n")]), False)
        restored = term_from_dict(term_to_dict(original))
        assert restored == original
        assert restored.display_name == "n"

    def test_round_trip_nested_pi_in_binder_type(self) -> None:
        original = _ih_statement("ih", "n")
        restored = Statement.from_dict(original.to_dict())
        assert restored == original
        assert restored.binders[0].display_name == "ih"
        assert restored.binders[0].type.display_name == "n"

    def test_round_trip_pi_inside_node_args(self) -> None:
        # h1 : A = B ∧ ((n : Nat) → P n) -- Pi nested inside And's argument, not a binder type.
        pi = Pi("n", Node("Nat", []), Node("P", [Var(0, "n")]), False)
        original = Node("And", [Node("Eq", [Node("A", []), Node("B", [])]), pi])
        restored = term_from_dict(term_to_dict(original))
        assert restored == original
        assert restored.args[1].display_name == "n"


class TestSchema:
    def test_representative_statement_validates(self) -> None:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text())
        instance = _permut_cons_statement("e", "x", "xs").to_dict()
        jsonschema.validate(instance, schema)

    def test_representative_ih_statement_validates(self) -> None:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text())
        instance = _ih_statement("ih", "n").to_dict()
        jsonschema.validate(instance, schema)
