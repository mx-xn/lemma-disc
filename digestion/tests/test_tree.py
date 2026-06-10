"""Unit tests for _build_tree. No Lean / LeanDojo required."""
import sys
import unittest.mock as mock

for _m in [
    "lean_dojo_v2", "lean_dojo_v2.lean_dojo",
    "lean_dojo_v2.lean_dojo.data_extraction",
    "lean_dojo_v2.lean_dojo.data_extraction.ast",
    "lean_dojo_v2.lean_dojo.data_extraction.traced_data",
    "lean_dojo_v2.lean_dojo.data_extraction.trace",
]:
    sys.modules.setdefault(_m, mock.MagicMock())

from dataclasses import dataclass  # noqa: E402

from digestion.extractor import _build_tree, _split_connective, _strip_arm_bodies  # noqa: E402


# ── Fake Pos + TracedTactic ──────────────────────────────────────────────────

@dataclass(frozen=True)
class _Pos:
    line_nb: int
    column_nb: int

    def __lt__(self, o):
        return (self.line_nb, self.column_nb) < (o.line_nb, o.column_nb)

    def __le__(self, o):
        return self == o or self < o


class _FakeTactic:
    """Minimal TracedTactic stand-in with explicit span coordinates."""
    def __init__(
        self,
        start_line: int, start_col: int,
        end_line: int, end_col: int,
        *,
        tactic: str = "skip",
        state_before: str = "",
        state_after: str = "",
    ):
        self._start = _Pos(start_line, start_col)
        self._end = _Pos(end_line, end_col)
        self._tactic = tactic
        self._state_before = state_before
        self._state_after = state_after
        self.ast = mock.MagicMock()
        self.ast.traverse_preorder = lambda fn, node_cls: None  # empty AST

    @property
    def start(self): return self._start
    @property
    def end(self): return self._end
    @property
    def tactic(self): return self._tactic
    @property
    def state_before(self): return self._state_before
    @property
    def state_after(self): return self._state_after


# ── helpers ──────────────────────────────────────────────────────────────────

def _by_id(nodes):
    return {n.id: n for n in nodes}


# ── tests ────────────────────────────────────────────────────────────────────

def test_empty():
    assert _build_tree([]) == []


def test_single_node():
    tt = _FakeTactic(1, 1, 1, 10, state_before="⊢ True", state_after="no goals")
    nodes = _build_tree([tt])
    assert len(nodes) == 1
    n = nodes[0]
    assert n.id == 0
    assert n.parent_id is None
    assert n.child_ids == []
    assert n.output_obligations == []


def test_linear_chain():
    # A (lines 1-5) contains B (lines 2-4) contains C (line 3).
    # A has 1 output obligation → 1 child (B).
    # B has 1 output obligation → 1 child (C).
    # C closes the goal.
    one_goal = "⊢ P"
    A = _FakeTactic(1, 1, 5, 1, state_before=one_goal, state_after=one_goal)
    B = _FakeTactic(2, 1, 4, 1, state_before=one_goal, state_after=one_goal)
    C = _FakeTactic(3, 1, 3, 10, state_before=one_goal, state_after="no goals")

    nodes = _build_tree([A, B, C])
    by_id = _by_id(nodes)

    assert by_id[0].parent_id is None   # A is root
    assert by_id[1].parent_id == 0      # B's parent is A
    assert by_id[2].parent_id == 1      # C's parent is B

    assert by_id[0].child_ids == [1]    # A → B
    assert by_id[1].child_ids == [2]    # B → C
    assert by_id[2].child_ids == []     # C is leaf


def test_branching():
    # A (lines 1-5) contains B (line 2) and C (line 3); B and C are siblings.
    # A produces 2 output obligations → child_ids = [B.id, C.id].
    two_goals = "h1 : P\n⊢ P\n\nh2 : Q\n⊢ Q"
    A = _FakeTactic(1, 1, 5, 1, state_before="⊢ P ∧ Q", state_after=two_goals)
    B = _FakeTactic(2, 1, 2, 10, state_before="h1 : P\n⊢ P", state_after="no goals")
    C = _FakeTactic(3, 1, 3, 10, state_before="h2 : Q\n⊢ Q", state_after="no goals")

    nodes = _build_tree([A, B, C])
    by_id = _by_id(nodes)

    assert by_id[0].parent_id is None
    assert by_id[1].parent_id == 0
    assert by_id[2].parent_id == 0

    assert by_id[0].child_ids == [1, 2]
    assert by_id[1].child_ids == []
    assert by_id[2].child_ids == []


def test_none_positions_become_roots():
    # Tactics with None spans can't be placed → each treated as root.
    class _NoSpan(_FakeTactic):
        @property
        def start(self): return None
        @property
        def end(self): return None

    A = _NoSpan(0, 0, 0, 0, state_before="⊢ P", state_after="no goals")
    B = _NoSpan(0, 0, 0, 0, state_before="⊢ Q", state_after="no goals")
    nodes = _build_tree([A, B])
    assert nodes[0].parent_id is None
    assert nodes[1].parent_id is None


def test_sequential_flat_roots():
    # E12: three tactics with non-overlapping spans (no containment).
    # chain-root linking should produce A → B → C.
    one_goal = "⊢ P"
    A = _FakeTactic(1, 1, 1, 5, tactic="intro h", state_before="⊢ Nat → P", state_after=one_goal)
    B = _FakeTactic(2, 1, 2, 5, tactic="rw [h]",  state_before=one_goal,    state_after=one_goal)
    C = _FakeTactic(3, 1, 3, 5, tactic="rfl",     state_before=one_goal,    state_after="no goals")

    nodes = _build_tree([A, B, C])
    by_id = _by_id(nodes)

    assert by_id[0].parent_id is None   # A is root
    assert by_id[1].parent_id == 0      # B chained from A
    assert by_id[2].parent_id == 1      # C chained from B
    assert by_id[0].child_ids == [1]
    assert by_id[1].child_ids == [2]
    assert by_id[2].child_ids == []


def test_compound_two_arms():
    # E13: compound tactic whose state_after is "no goals" (LeanDojo behaviour for
    # induction/cases blocks).  Output obligations must be recovered from children's
    # state_before, and child_ids must be populated.
    parent = _FakeTactic(
        1, 1, 6, 1,
        tactic="induction xs with | nil => * | cons => *",
        state_before="xs : List Nat\n⊢ P xs",
        state_after="no goals",
    )
    child1 = _FakeTactic(
        2, 3, 3, 10,
        tactic="rfl",
        state_before="⊢ P []",
        state_after="no goals",
    )
    child2 = _FakeTactic(
        4, 3, 5, 10,
        tactic="simp",
        state_before="x : Nat\nxs : List Nat\n⊢ P (x :: xs)",
        state_after="no goals",
    )

    nodes = _build_tree([parent, child1, child2])
    by_id = _by_id(nodes)

    assert by_id[0].parent_id is None
    assert by_id[0].child_ids == [1, 2]
    assert len(by_id[0].output_obligations) == 2
    assert by_id[0].output_obligations[0].goal == "P []"
    assert by_id[0].output_obligations[1].goal == "P (x :: xs)"
    assert len(by_id[0].summary.dependency_maps) == 2

    assert by_id[1].parent_id == 0
    assert by_id[2].parent_id == 0


def test_compound_three_arms():
    # E14: compound tactic with three arms (e.g. cases on a 3-constructor type).
    parent = _FakeTactic(
        1, 1, 10, 1,
        tactic="cases t with | A => * | B => * | C => *",
        state_before="t : T\n⊢ P t",
        state_after="no goals",
    )
    c1 = _FakeTactic(2, 3, 3, 10, tactic="rfl",  state_before="⊢ P A", state_after="no goals")
    c2 = _FakeTactic(4, 3, 4, 10, tactic="rfl",  state_before="⊢ P B", state_after="no goals")
    c3 = _FakeTactic(6, 3, 6, 10, tactic="rfl",  state_before="⊢ P C", state_after="no goals")

    nodes = _build_tree([parent, c1, c2, c3])
    by_id = _by_id(nodes)

    assert by_id[0].child_ids == [1, 2, 3]
    assert len(by_id[0].output_obligations) == 3
    assert [o.goal for o in by_id[0].output_obligations] == ["P A", "P B", "P C"]
    assert len(by_id[0].summary.dependency_maps) == 3


def test_compound_mixed_leaf_and_subtree():
    # E20: compound parent; one arm closes via simp_all (leaf, U = all hyps),
    # the other arm has a further child tactic.
    parent = _FakeTactic(
        1, 1, 10, 1,
        tactic="cases h with | inl => * | inr => *",
        state_before="h : P ∨ Q\n⊢ R",
        state_after="no goals",
    )
    leaf_arm = _FakeTactic(
        2, 3, 3, 15,
        tactic="simp_all",
        state_before="hp : P\n⊢ R",
        state_after="no goals",
    )
    inner_parent = _FakeTactic(
        4, 3, 8, 1,
        tactic="apply f",
        state_before="hq : Q\n⊢ R",
        state_after="hq : Q\n⊢ S",
    )
    inner_child = _FakeTactic(
        5, 5, 5, 10,
        tactic="exact hq",
        state_before="hq : Q\n⊢ S",
        state_after="no goals",
    )

    nodes = _build_tree([parent, leaf_arm, inner_parent, inner_child])
    by_id = _by_id(nodes)

    # compound parent
    assert by_id[0].child_ids == [1, 2]
    assert len(by_id[0].output_obligations) == 2

    # leaf arm: simp_all consumes all hypotheses in its context
    assert by_id[1].child_ids == []
    assert by_id[1].output_obligations == []
    assert by_id[1].summary.directly_used == ["hp"]

    # inner_parent is the second arm's root
    assert by_id[2].parent_id == 0
    assert by_id[2].child_ids == [3]

    # inner_child is a leaf
    assert by_id[3].parent_id == 2
    assert by_id[3].child_ids == []
    assert by_id[3].summary.directly_used == ["hq"]


def test_ids_are_dfs_preorder():
    one_goal = "⊢ P"
    A = _FakeTactic(1, 1, 5, 1, state_before=one_goal, state_after=one_goal)
    B = _FakeTactic(2, 1, 4, 1, state_before=one_goal, state_after=one_goal)
    C = _FakeTactic(3, 1, 3, 10, state_before=one_goal, state_after="no goals")
    nodes = _build_tree([A, B, C])
    # IDs are assigned in the order tactics are yielded (already DFS pre-order).
    assert [n.id for n in nodes] == [0, 1, 2]
    assert nodes[0].id < nodes[1].id < nodes[2].id


# ── _strip_arm_bodies ────────────────────────────────────────────────────────

def test_strip_arm_bodies_inline():
    # E18a: arm body on the same line as the arrow.
    text = "induction xs with\n  | nil => simp\n  | cons x xs ih => exact ih"
    result = _strip_arm_bodies(text)
    assert result == "induction xs with\n  | nil => _*_\n  | cons x xs ih => _*_"


def test_strip_arm_bodies_block():
    # E18b: arm body on following indented lines.
    text = (
        "induction xs with\n"
        "  | nil =>\n"
        "    simp\n"
        "    ring\n"
        "  | cons x xs ih =>\n"
        "    exact ih"
    )
    result = _strip_arm_bodies(text)
    assert result == (
        "induction xs with\n"
        "  | nil => _*_\n"
        "  | cons x xs ih => _*_"
    )


def test_strip_arm_bodies_non_arm_lines_preserved():
    # E18c: lines before the first arm are preserved verbatim.
    text = "cases h\nnext h1 h2 =>\n  exact h1"
    result = _strip_arm_bodies(text)
    # No | arm markers → nothing stripped.
    assert result == text


def test_strip_arm_bodies_arrow_in_inline_body_not_confused():
    # E18d: arm body itself contains '=>' — only the arm header => should trigger.
    text = "cases h with\n  | inl hp => exact (fun _ => hp)\n  | inr hq => exact hq"
    result = _strip_arm_bodies(text)
    assert result == "cases h with\n  | inl hp => _*_\n  | inr hq => _*_"


# ── _split_connective ────────────────────────────────────────────────────────

def test_split_connective_and():
    assert _split_connective("Q ∧ R", "∧") == ("Q", "R")


def test_split_connective_iff():
    assert _split_connective("A ↔ B", "↔") == ("A", "B")


def test_split_connective_nested_parens():
    # Top-level ∧; the left side contains a parenthesised conjunction.
    assert _split_connective("(A ∧ B) ∧ C", "∧") == ("(A ∧ B)", "C")


def test_split_connective_none_when_absent():
    assert _split_connective("P → Q", "∧") is None


# ── _expand_semicolons (via _build_tree) ─────────────────────────────────────

def test_semicolon_constructor_and():
    # `constructor <;> assumption` on goal `Q ∧ R` should expand into:
    #   node 0: constructor  (parent=None, children=[1,2], out=[⊢Q, ⊢R])
    #   node 1: assumption   (parent=0, children=[], in=⊢Q, directly_used=["hs"])
    #   node 2: assumption   (parent=0, children=[], in=⊢R, directly_used=["hr"])
    tt = _FakeTactic(
        1, 1, 1, 30,
        tactic="constructor <;> assumption",
        state_before="hs : Q\nhr : R\n⊢ Q ∧ R",
        state_after="no goals",
    )
    nodes = _build_tree([tt])
    by_id = _by_id(nodes)

    assert len(nodes) == 3, f"expected 3 nodes, got {len(nodes)}: {[n.tactic_text for n in nodes]}"

    assert by_id[0].tactic_text == "constructor"
    assert by_id[0].parent_id is None
    assert len(by_id[0].output_obligations) == 2
    assert by_id[0].output_obligations[0].goal == "Q"
    assert by_id[0].output_obligations[1].goal == "R"
    assert by_id[0].child_ids == [1, 2]
    assert by_id[0].summary.directly_used == []

    assert by_id[1].tactic_text == "assumption"
    assert by_id[1].parent_id == 0
    assert by_id[1].input_obligation.goal == "Q"
    assert by_id[1].output_obligations == []
    assert by_id[1].child_ids == []
    assert by_id[1].summary.directly_used == ["hs"]

    assert by_id[2].tactic_text == "assumption"
    assert by_id[2].parent_id == 0
    assert by_id[2].input_obligation.goal == "R"
    assert by_id[2].output_obligations == []
    assert by_id[2].child_ids == []
    assert by_id[2].summary.directly_used == ["hr"]


def test_semicolon_constructor_iff():
    # `constructor <;> intro h` on goal `A ↔ B` should expand into:
    #   node 0: constructor  (children=[1,2], out=[⊢ A→B, ⊢ B→A])
    #   node 1: intro h
    #   node 2: intro h
    tt = _FakeTactic(
        1, 1, 1, 30,
        tactic="constructor <;> intro h",
        state_before="⊢ A ↔ B",
        state_after="no goals",
    )
    nodes = _build_tree([tt])
    by_id = _by_id(nodes)

    assert len(nodes) == 3
    assert by_id[0].tactic_text == "constructor"
    assert by_id[0].output_obligations[0].goal == "A → B"
    assert by_id[0].output_obligations[1].goal == "B → A"
    assert by_id[1].tactic_text == "intro h"
    assert by_id[2].tactic_text == "intro h"


def test_semicolon_unknown_t1_not_expanded():
    # `cases h <;> simp` — `cases` subgoal count is not inferrable without
    # trace data; should remain as a single node.
    tt = _FakeTactic(
        1, 1, 1, 20,
        tactic="cases h <;> simp",
        state_before="h : P ∨ Q\n⊢ R",
        state_after="no goals",
    )
    nodes = _build_tree([tt])
    assert len(nodes) == 1
    assert nodes[0].tactic_text == "cases h <;> simp"


def test_semicolon_constructor_dep_maps_are_passthrough():
    # All hypotheses pass through unchanged in each branch of `constructor`.
    tt = _FakeTactic(
        1, 1, 1, 30,
        tactic="constructor <;> assumption",
        state_before="h : P\n⊢ P ∧ P",
        state_after="no goals",
    )
    nodes = _build_tree([tt])
    by_id = _by_id(nodes)
    for branch_map in by_id[0].summary.dependency_maps:
        assert branch_map == {"h": ["h"]}


# ── Goal-stack chaining (semicolon sequencing under cases arms) ──────────────

def test_goalstack_constructor_then_close_each_branch_separately():
    """`cases h | inl => constructor; left; exact hpr.1; exact hpr.2`

    constructor produces 2 goals (P∨Q, R).  `left` operates on goal 0 → P.
    `exact hpr.1` closes P.  `exact hpr.2` then must close R, which was
    constructor's SECOND output — so it should be a child of constructor,
    not of `exact hpr.1`.  This is the or_and_distrib bug.
    """
    cases = _FakeTactic(
        1, 1, 5, 50,
        tactic="cases hpqr with | inl hpr => constructor; left; exact hpr.1; exact hpr.2",
        state_before="hpqr : P ∧ R ∨ Q ∧ R\n⊢ (P ∨ Q) ∧ R",
        state_after="no goals",
    )
    constructor = _FakeTactic(
        2, 1, 2, 11,
        tactic="constructor",
        state_before="hpr : P ∧ R\n⊢ (P ∨ Q) ∧ R",
        state_after="hpr : P ∧ R\n⊢ P ∨ Q\n\nhpr : P ∧ R\n⊢ R",
    )
    left_t = _FakeTactic(
        2, 13, 2, 17,
        tactic="left",
        state_before="hpr : P ∧ R\n⊢ P ∨ Q\n\nhpr : P ∧ R\n⊢ R",
        state_after="hpr : P ∧ R\n⊢ P\n\nhpr : P ∧ R\n⊢ R",
    )
    exact1 = _FakeTactic(
        2, 19, 2, 30,
        tactic="exact hpr.1",
        state_before="hpr : P ∧ R\n⊢ P\n\nhpr : P ∧ R\n⊢ R",
        state_after="hpr : P ∧ R\n⊢ R",
    )
    exact2 = _FakeTactic(
        2, 32, 2, 43,
        tactic="exact hpr.2",
        state_before="hpr : P ∧ R\n⊢ R",
        state_after="no goals",
    )

    nodes = _build_tree([cases, constructor, left_t, exact1, exact2])
    by_id = _by_id(nodes)

    # Tree should be:
    #   0: cases       → [1]
    #   1: constructor → [2, 4]   (output 0: P∨Q, output 1: R)
    #   2: left        → [3]      (its only NEW output is ⊢ P)
    #   3: exact hpr.1 → []       (closes its goal)
    #   4: exact hpr.2 → []       (closes constructor's 2nd branch)
    assert by_id[1].child_ids == [2, 4], (
        f"constructor should branch to left+exact hpr.2; got {by_id[1].child_ids}"
    )
    assert len(by_id[1].output_obligations) == 2

    assert by_id[2].child_ids == [3]
    assert len(by_id[2].output_obligations) == 1, (
        f"`left` only produces 1 NEW output (⊢ P); ⊢ R is leftover"
    )
    assert by_id[2].output_obligations[0].goal == "P"

    assert by_id[3].child_ids == []
    assert by_id[3].output_obligations == [], (
        f"`exact hpr.1` closes ⊢ P; the ⊢ R it shows is leftover, not its output"
    )

    assert by_id[4].parent_id == 1, (
        f"exact hpr.2 should chain back to constructor (id 1), not exact hpr.1 (id 3); "
        f"got parent={by_id[4].parent_id}"
    )
    assert by_id[4].child_ids == []
    assert by_id[4].output_obligations == []


def test_goalstack_closes_simple_chain_unaffected():
    """Linear `intro h; subst h; simp` should still chain sequentially —
    no leftover goals, so the new pass-3 behaviour matches the old one."""
    a = _FakeTactic(1, 1, 5, 50, tactic="cases h with | mk => intro x; rfl",
                    state_before="h : True\n⊢ P", state_after="no goals")
    b = _FakeTactic(2, 1, 2, 10, tactic="intro x",
                    state_before="⊢ Q → P", state_after="x : Q\n⊢ P")
    c = _FakeTactic(2, 12, 2, 15, tactic="rfl",
                    state_before="x : Q\n⊢ P", state_after="no goals")
    nodes = _build_tree([a, b, c])
    by_id = _by_id(nodes)
    # b is the first tactic of cases's only arm → child of a.
    # c chains to b (b's new output ⊢ P matches c's input).
    assert by_id[0].child_ids == [1]
    assert by_id[1].child_ids == [2]
    assert by_id[2].child_ids == []


def test_subtract_leftover_basic():
    from digestion.extractor import _subtract_leftover
    from digestion.models import Hypothesis, Obligation
    a = Obligation(hypotheses=[Hypothesis(name="h", type="P")], goal="P")
    b = Obligation(hypotheses=[Hypothesis(name="h", type="P")], goal="Q")
    # state_after [P, Q] minus leftover [Q] = [P]
    assert _subtract_leftover([a, b], [b]) == [a]
    # Multiset semantics: [P, P] minus [P] = [P]
    assert _subtract_leftover([a, a], [a]) == [a]
    # Empty leftover is identity.
    assert _subtract_leftover([a, b], []) == [a, b]
    # Leftover with no match leaves after unchanged.
    assert _subtract_leftover([a], [b]) == [a]
