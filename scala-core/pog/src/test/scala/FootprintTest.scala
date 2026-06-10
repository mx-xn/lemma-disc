import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for `Footprint.compute` (Step 4) — the name-level coarsening of the
 *  paper's tactic footprint Φ(a, Γ, g) = (D, M, µ, ρ) (Definition 2, §2.1).
 *
 *  `compute` is a PURE function of one node's input obligation, output
 *  obligations, and summary — it never inspects the tree (`parent_id` /
 *  `child_ids`). Recovery rules (see scala-core/pog/CLAUDE.md §"Recovering the
 *  Footprint"), with the corrections agreed during design review:
 *
 *    modifies_hyps  = { h ∈ Γ | h dropped OR its `type` changed in SOME branch }
 *                     (INPUT names only; newly-introduced names never count —
 *                      paper Def 2: M ⊆ {g}∪Γ).
 *    modifies_goal  = ∃ branch i. goalᵢ ≠ goal   (pure syntactic check).
 *    uses (D)       = (directly_used ∩ names(Γ)) \ modifies_hyps
 *                     (decision: D ⊆ Γ, so external lemma names are dropped).
 *    rho[i]         = invert(dependency_maps[i]) ∪ { "⊢" → {"⊢"} }
 *                     for EVERY output branch; leaves (no outputs) → rho = [].
 *
 *  ── Two deliberate departures from the CLAUDE.md Step-4 *snippet* — do NOT
 *     "fix" the tests back to match it: ──────────────────────────────────────
 *
 *    1. rho ORIENTATION. The snippet writes `rho = πᵢ` verbatim, but phase-1
 *       `dependency_maps` are oriented output-name → input-names (the BACKWARD
 *       direction). The schema (pog.schema.json) and the Step-6 forward
 *       propagation both require input-name → {output-names}, so `compute`
 *       INVERTS πᵢ. (Un-inverted, the documented use-edge prop_14 (0→5) is
 *       underivable.)
 *
 *    2. rho GOAL ENTRY is UNCONDITIONAL. The snippet gates "⊢"→{"⊢"} on
 *       `modifies_goal`, conflating two distinct facts: whether the goal is in
 *       M (can ORIGINATE a dependency — `modifies_goal`) vs. whether the goal
 *       PROPAGATES forward (always, identity). Gating breaks goal-threading
 *       composition through intermediate non-goal-modifying tactics, so the
 *       goal entry is always present on every non-leaf branch.
 *
 *  Likewise, the CLAUDE.md FootprintTest example table (the `intro h` row) and
 *  the ParserTest comment claiming `ih` enters M_hyps are SUPERSEDED by the
 *  code/paper behavior asserted here.
 */
class FootprintTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private def h(name: String, ty: String): Hypothesis = Hypothesis(name, ty)

  private def obl(goal: String, hyps: Hypothesis*): Obligation =
    Obligation(hyps.toList, goal)

  /** A standalone node. Tree fields are dummies on purpose — `compute` must
   *  ignore them (see Group 6.1). */
  private def node(
    in:   Obligation,
    outs: List[Obligation]                = Nil,
    used: List[String]                    = Nil,
    deps: List[Map[String, List[String]]] = Nil
  ): TacticNode =
    TacticNode(
      id                = 0,
      tacticText        = "tac",
      inputObligation   = in,
      outputObligations = outs,
      summary           = TacticSummary(used, deps),
      parentId          = None,
      childIds          = Nil
    )

  private val Goal = "⊢"  // reserved goal-slot token


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Leaf nodes (no output obligations)
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (leaf)" should "give D={h}, M=∅, M_goal=false, rho=[] for `exact h`" in {
    val n = node(obl("Q", h("h", "P")), outs = Nil, used = List("h"))
    Footprint.compute(n) shouldBe
      Footprint(uses = Set("h"), modifiesHyps = Set.empty, modifiesGoal = false, rho = Nil)
  }

  it should "give an all-empty footprint for a no-use leaf (`sorry` / `rfl`)" in {
    val n = node(obl("P"), outs = Nil, used = Nil)
    Footprint.compute(n) shouldBe
      Footprint(Set.empty, Set.empty, modifiesGoal = false, Nil)
  }

  it should "keep every used hyp in D for a multi-use leaf (`exact (f h)`)" in {
    val n = node(obl("C", h("f", "A → C"), h("h", "A")), outs = Nil, used = List("f", "h"))
    Footprint.compute(n).uses shouldBe Set("f", "h")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — modifies_goal (the boolean M_goal = ∃i. goalᵢ ≠ goal)
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (modifies_goal)" should "be true when a single branch rewrites the goal (`simp`)" in {
    val n = node(
      in   = obl("A", h("h", "P")),
      outs = List(obl("B", h("h", "P"))),
      deps = List(Map("h" -> List("h")))
    )
    val f = Footprint.compute(n)
    f.modifiesGoal shouldBe true
    f.modifiesHyps shouldBe Set.empty   // h carried through unchanged
  }

  it should "be false when the goal text is identical across the single branch" in {
    // a no-op-on-goal tactic that only introduces `k`
    val n = node(
      in   = obl("A", h("h", "P")),
      outs = List(obl("A", h("h", "P"), h("k", "Q"))),
      deps = List(Map("h" -> List("h")))
    )
    Footprint.compute(n).modifiesGoal shouldBe false
  }

  it should "be true (∃-semantics) when only ONE of two branches changes the goal" in {
    val n = node(
      in   = obl("G", h("h", "A ∨ B")),
      outs = List(obl("G", h("h", "A")), obl("G2", h("h", "B")))
    )
    Footprint.compute(n).modifiesGoal shouldBe true
  }

  it should "be true for `intro h` (goal `P → Q` ⟹ `Q`), and NOT put the introduced `h` in M_hyps" in {
    // Supersedes the CLAUDE.md example table, which wrongly says M_goal=false /
    // M_hyps={...} for intro.
    val n = node(
      in   = obl("P → Q"),
      outs = List(obl("Q", h("h", "P"))),
      deps = List(Map("h" -> List()))
    )
    val f = Footprint.compute(n)
    f.modifiesGoal shouldBe true
    f.modifiesHyps shouldBe Set.empty   // `h` is introduced, not an input hyp
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — modifies_hyps (input hyps dropped OR retyped, unioned over branches)
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (modifies_hyps)" should "flag a hyp DROPPED in a branch (induction-nil drops `xs`)" in {
    val n = node(
      in   = obl("g", h("xs", "List α"), h("ys", "List α")),
      outs = List(obl("g0", h("ys", "List α")))
    )
    Footprint.compute(n).modifiesHyps shouldBe Set("xs")
  }

  it should "flag a hyp whose TYPE changed in place (`rw … at hyp`)" in {
    val n = node(
      in   = obl("g", h("h", "a = b"), h("hyp", "P a")),
      outs = List(obl("g", h("h", "a = b"), h("hyp", "P b"))),
      deps = List(Map("h" -> List("h"), "hyp" -> List("hyp")))
    )
    val f = Footprint.compute(n)
    f.modifiesHyps shouldBe Set("hyp")   // `h` unchanged
    f.modifiesGoal shouldBe false
  }

  it should "UNION over branches — a hyp dropped in just one branch counts" in {
    val n = node(
      in   = obl("g", h("h", "P")),
      outs = List(obl("g0"), obl("g1", h("h", "P")))   // branch 0 drops h
    )
    Footprint.compute(n).modifiesHyps shouldBe Set("h")
  }

  it should "NOT flag a newly-introduced hyp (introductions ∉ M_hyps)" in {
    val n = node(
      in   = obl("g", h("a", "A")),
      outs = List(obl("g", h("a", "A"), h("b", "B")))
    )
    Footprint.compute(n).modifiesHyps shouldBe Set.empty
  }

  it should "NOT flag a pure REORDER of unchanged hyps" in {
    val n = node(
      in   = obl("g", h("h1", "P"), h("h2", "Q")),
      outs = List(obl("g", h("h2", "Q"), h("h1", "P")))
    )
    Footprint.compute(n).modifiesHyps shouldBe Set.empty
  }

  it should "collect ALL modified input hyps" in {
    val n = node(
      in   = obl("g", h("a", "A"), h("b", "B"), h("c", "C")),
      outs = List(obl("g", h("c", "C")))   // a, b dropped
    )
    Footprint.compute(n).modifiesHyps shouldBe Set("a", "b")
  }

  it should "flag a type change occurring in only ONE branch" in {
    val n = node(
      in   = obl("g", h("h", "P a")),
      outs = List(obl("g", h("h", "P a")), obl("g", h("h", "P b")))
    )
    Footprint.compute(n).modifiesHyps shouldBe Set("h")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — uses  (D = (directly_used ∩ names(Γ)) \ modifies_hyps)
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (uses / D)" should "keep a used + unmodified hyp" in {
    val n = node(
      in   = obl("g", h("k", "K")),
      outs = List(obl("g", h("k", "K"))),
      used = List("k"),
      deps = List(Map("k" -> List("k")))
    )
    Footprint.compute(n).uses shouldBe Set("k")
  }

  it should "remove a used-but-modified hyp from D (kept hyp survives)" in {
    val n = node(
      in   = obl("g", h("h", "P"), h("k", "K")),
      outs = List(obl("g", h("k", "K"))),   // h dropped
      used = List("h", "k"),
      deps = List(Map("k" -> List("k")))
    )
    Footprint.compute(n).uses shouldBe Set("k")
  }

  it should "yield D=∅ when the only used hyp is itself modified" in {
    val n = node(
      in   = obl("g", h("h", "P")),
      outs = List(obl("g")),   // h dropped
      used = List("h")
    )
    Footprint.compute(n).uses shouldBe Set.empty
  }

  it should "yield D=∅ when nothing is used" in {
    val n = node(obl("g", h("h", "P")), outs = List(obl("g", h("h", "P"))),
                 used = Nil, deps = List(Map("h" -> List("h"))))
    Footprint.compute(n).uses shouldBe Set.empty
  }

  it should "DROP a directly_used name that is not an input hypothesis (external lemma)" in {
    // decision: D ⊆ Γ, so `Nat.add_comm` (not in Γ) does not leak into D.
    val n = node(
      in   = obl("g", h("h", "P")),
      outs = List(obl("g", h("h", "P"))),
      used = List("h", "Nat.add_comm"),
      deps = List(Map("h" -> List("h")))
    )
    Footprint.compute(n).uses shouldBe Set("h")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — rho  (per-branch forward map: invert(πᵢ) ∪ {⊢→{⊢}})
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (rho)" should "carry an identity entry through unchanged, plus ⊢→{⊢}" in {
    val n = node(
      in   = obl("g", h("ys", "List α")),
      outs = List(obl("g", h("ys", "List α"))),
      deps = List(Map("ys" -> List("ys")))
    )
    Footprint.compute(n).rho shouldBe
      List(Map("ys" -> Set("ys"), Goal -> Set(Goal)))
  }

  it should "INVERT dependency_maps: output→inputs becomes input→{outputs}" in {
    // π = { a ← {x,y}, b ← {x} }  ⟹  x → {a,b}, y → {a}
    val n = node(
      in   = obl("g2", h("x", "X"), h("y", "Y")),
      outs = List(obl("g2", h("a", "A"), h("b", "B"))),
      deps = List(Map("a" -> List("x", "y"), "b" -> List("x")))
    )
    val rho0 = Footprint.compute(n).rho.head
    rho0("x") shouldBe Set("a", "b")
    rho0("y") shouldBe Set("a")
    rho0(Goal) shouldBe Set(Goal)
  }

  it should "add ⊢→{⊢} to EVERY branch when the goal is modified" in {
    val n = node(
      in   = obl("G", h("h", "A ∨ B")),
      outs = List(obl("G1", h("h", "A")), obl("G2", h("h", "B"))),
      deps = List(Map("h" -> List("h")), Map("h" -> List("h")))
    )
    val rho = Footprint.compute(n).rho
    rho.length      shouldBe 2
    rho.foreach(_(Goal) shouldBe Set(Goal))
  }

  it should "STILL include ⊢→{⊢} on a non-leaf node whose goal is UNCHANGED" in {
    // The corrected behavior: goal PROPAGATION is independent of goal MODIFICATION.
    val n = node(
      in   = obl("g", h("h", "P")),
      outs = List(obl("g", h("h", "P"))),
      deps = List(Map("h" -> List("h")))
    )
    val f = Footprint.compute(n)
    f.modifiesGoal       shouldBe false          // goal NOT modified …
    f.rho.head(Goal)     shouldBe Set(Goal)       // … yet ⊢ still propagates
  }

  it should "decouple modifies_goal (boolean) from the rho goal entry" in {
    // Same node as above, stated as the explicit invariant: a false boolean
    // must NOT suppress the rho ⊢ entry.
    val n = node(obl("g", h("h", "P")), outs = List(obl("g", h("h", "P"))),
                 deps = List(Map("h" -> List("h"))))
    val f = Footprint.compute(n)
    (f.modifiesGoal, f.rho.head.contains(Goal)) shouldBe (false, true)
  }

  it should "produce rho=[] for a leaf (no outputs ⇒ no ⊢ anywhere)" in {
    val n = node(obl("g", h("h", "P")), outs = Nil, used = List("h"))
    Footprint.compute(n).rho shouldBe Nil
  }

  it should "yield {⊢→{⊢}} for a non-leaf branch whose dependency map is empty" in {
    // Real shape: prop_78 node 0 branch 0 has an empty {} dep map.
    val n = node(
      in   = obl("g", h("h", "P")),
      outs = List(obl("g0")),
      deps = List(Map.empty[String, List[String]])
    )
    Footprint.compute(n).rho shouldBe List(Map(Goal -> Set(Goal)))
  }

  it should "DEDUP a dependency value list into a Set" in {
    val n = node(
      in   = obl("g", h("xs", "List α")),
      outs = List(obl("g", h("xs", "List α"))),
      deps = List(Map("xs" -> List("xs", "xs")))   // duplicate source
    )
    Footprint.compute(n).rho.head("xs") shouldBe Set("xs")
  }

  it should "co-index rho with output branches and preserve their order" in {
    val n = node(
      in   = obl("G", h("h", "A ∨ B")),
      outs = List(obl("G1", h("h", "A")), obl("G2", h("h", "B"))),
      deps = List(Map("h" -> List("a0")), Map("h" -> List("a1")))
    )
    val rho = Footprint.compute(n).rho
    rho.length                 shouldBe 2                 // == #outputs
    rho(0).get("a0")           shouldBe Some(Set("h"))    // branch 0 inverted
    rho(1).get("a1")           shouldBe Some(Set("h"))    // branch 1 inverted
    rho(0).contains("a1")      shouldBe false             // no cross-branch bleed
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — structural / determinism / golden
  // ═══════════════════════════════════════════════════════════════════════════

  "Footprint.compute (structure)" should "ignore parent_id / child_ids entirely" in {
    val in   = obl("Q", h("h", "P"))
    val base = node(in, outs = Nil, used = List("h"))
    val withTree = base.copy(parentId = Some(99), childIds = List(7, 8, 9))
    Footprint.compute(base) shouldBe Footprint.compute(withTree)
  }

  it should "be insensitive to input-hyp ORDER (Set-valued fields)" in {
    val a = node(obl("g", h("a", "A"), h("b", "B")), outs = List(obl("g", h("a", "A"))),
                 used = List("a", "b"))
    val b = node(obl("g", h("b", "B"), h("a", "A")), outs = List(obl("g", h("a", "A"))),
                 used = List("a", "b"))
    Footprint.compute(a) shouldBe Footprint.compute(b)
  }

  // ── Golden: the real prop_14 root `induction xs` node from the fixture ──────
  // Tree shape & raw values verified against the trace in ParserTest.

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  it should "match the hand-derived footprint of prop_14's root induction node" in {
    val root = Parser.parseFile(fixture)
      .declarations.head.tacticNodes.find(_.id == 0).getOrElse(fail("no prop_14 root"))

    Footprint.compute(root) shouldBe Footprint(
      uses         = Set.empty,             // U={xs}, but xs ∈ M_hyps ⇒ removed
      modifiesHyps = Set("xs"),             // dropped in the nil branch
      modifiesGoal = true,                  // both branch goals differ from input
      rho = List(
        // nil branch: invert {α←α, p←p, ys←ys}  + goal
        Map("α" -> Set("α"), "p" -> Set("p"), "ys" -> Set("ys"), Goal -> Set(Goal)),
        // cons branch: invert {α←α, p←p, ys←ys, x←α, xs←xs, ih←{xs,ys,p}} + goal
        Map(
          "α"  -> Set("α", "x"),
          "p"  -> Set("p", "ih"),
          "ys" -> Set("ys", "ih"),
          "xs" -> Set("xs", "ih"),
          Goal -> Set(Goal)
        )
      )
    )
  }
