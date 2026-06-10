import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for [[Effects]] — `derive`, `deriveAll`, and `apply`.
 *
 *  Pinned design decisions verified by these tests:
 *    [D1] Modify(prop, old, snew): prop = "⊢" targets the goal; a hypothesis name targets
 *         that hypothesis's type in-place. `old` is a fail-fast pre-condition on the
 *         current value — Apply throws if it doesn't match.
 *    [D2] Derivation order within an Effect: Clears (input order) → type-change Modifies
 *         (input order) → Introduces (output order) → goal Modify (last). Ensures each
 *         Modify's `old` is unambiguous at application time (e.g. a cleared hypothesis
 *         cannot be mistakenly targeted by a later type-change Modify).
 *    [D3] apply is pure — calling it twice on the same inputs gives the same result.
 *    [D4] Round-trip: apply(derive(node,i), node.inputObligation) reproduces the recorded
 *         output exactly on goal and as a (name→type) SET on hypotheses (list order may
 *         differ because Introduce appends at end whereas the recorded output may have had
 *         the new hypothesis at an interior position).
 */
class EffectsTest extends AnyFlatSpec with Matchers:

  // ── helpers ─────────────────────────────────────────────────────────────────

  private def hyp(name: String, typ: String): Hypothesis = Hypothesis(name, typ)
  private def obl(hyps: List[Hypothesis], goal: String): Obligation = Obligation(hyps, goal)
  private val noSum = TacticSummary(Nil, Nil)

  /** Minimal TacticNode — only inputObligation and outputObligations are meaningful. */
  private def tn(in: Obligation, outs: Obligation*): TacticNode =
    TacticNode(0, "tac", in, outs.toList, noSum, None, Nil)

  /** Wrap a single action in an Effect and apply it, for concise single-action tests. */
  private def applyOne(action: Action, o: Obligation): Obligation =
    Effects.apply(Effect(List(action)), o)

  /** Hypothesis set as (name, type) pairs — order-independent comparison for [D4]. */
  private def hypSet(o: Obligation): Set[(String, String)] =
    o.hypotheses.map(h => (h.name, h.`type`)).toSet

  /** Assert round-trip identity for branch `i` of `node` ([D4]). */
  private def assertRoundTrip(node: TacticNode, branchIndex: Int): Unit =
    val expected = node.outputObligations(branchIndex)
    val result   = Effects.apply(Effects.derive(node, branchIndex), node.inputObligation)
    withClue(s"goal mismatch on branch $branchIndex: ") {
      result.goal    shouldBe expected.goal
    }
    withClue(s"hypothesis set mismatch on branch $branchIndex: ") {
      hypSet(result) shouldBe hypSet(expected)
    }

  // ── shared fixture: induction node ──────────────────────────────────────────
  // [xs: List Nat] ⊢ P xs
  //   branch 0: [] ⊢ P []
  //   branch 1: [ih: P t, h: Nat] ⊢ P (h::t)

  private val indIn   = obl(List(hyp("xs", "List Nat")), "P xs")
  private val indOut0 = obl(Nil, "P []")
  private val indOut1 = obl(List(hyp("ih", "P t"), hyp("h", "Nat")), "P (h::t)")
  private val indNode = tn(indIn, indOut0, indOut1)


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — derive: single-branch tactics (1 output obligation)
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.derive (single-branch)" should "produce an empty Effect for an identity tactic" in {
    val node = tn(obl(List(hyp("h", "Nat")), "P h"), obl(List(hyp("h", "Nat")), "P h"))
    Effects.derive(node, 0) shouldBe Effect(Nil)
  }

  it should "produce a goal Modify for a goal-only rewrite" in {
    val node = tn(obl(List(hyp("h", "a=b")), "P a"), obl(List(hyp("h", "a=b")), "P b"))
    Effects.derive(node, 0) shouldBe Effect(List(Modify("⊢", "P a", "P b")))
  }

  it should "produce a Clear for pure hypothesis removal" in {
    val node = tn(obl(List(hyp("h", "Nat")), "P h"), obl(Nil, "P h"))
    Effects.derive(node, 0) shouldBe Effect(List(Clear("h")))
  }

  it should "produce Introduce then goal Modify for intro h (new hyp + goal change)" in {
    val node = tn(obl(Nil, "∀x:Nat, P x"), obl(List(hyp("h", "Nat")), "P h"))
    Effects.derive(node, 0) shouldBe
      Effect(List(Introduce(hyp("h", "Nat")), Modify("⊢", "∀x:Nat, P x", "P h")))
  }

  it should "produce two Introduces in output order then goal Modify for intro x y" in {
    val node = tn(
      obl(Nil, "∀x y:Nat, P x y"),
      obl(List(hyp("x", "Nat"), hyp("y", "Nat")), "P x y")
    )
    Effects.derive(node, 0) shouldBe Effect(List(
      Introduce(hyp("x", "Nat")),
      Introduce(hyp("y", "Nat")),
      Modify("⊢", "∀x y:Nat, P x y", "P x y")
    ))
  }

  it should "produce a hyp-name Modify for an in-place hypothesis type change" in {
    val node = tn(
      obl(List(hyp("h", "a=b"), hyp("k", "P a")), "Q"),
      obl(List(hyp("h", "a=b"), hyp("k", "P b")), "Q")
    )
    Effects.derive(node, 0) shouldBe Effect(List(Modify("k", "P a", "P b")))
  }

  it should "produce Clear then goal Modify for a simp-style tactic" in {
    val node = tn(
      obl(List(hyp("h", "T"), hyp("k", "U")), "P"),
      obl(List(hyp("h", "T")), "Q")
    )
    Effects.derive(node, 0) shouldBe Effect(List(Clear("k"), Modify("⊢", "P", "Q")))
  }

  it should "produce Clear then Introduce when one hyp is replaced by a differently-named one" in {
    val node = tn(obl(List(hyp("h", "T")), "P"), obl(List(hyp("k", "V")), "P"))
    Effects.derive(node, 0) shouldBe Effect(List(Clear("h"), Introduce(hyp("k", "V"))))
  }

  it should "produce only an Introduce when a new hyp is added without a goal change" in {
    val node = tn(
      obl(List(hyp("h", "T")), "P"),
      obl(List(hyp("h", "T"), hyp("j", "V")), "P")
    )
    Effects.derive(node, 0) shouldBe Effect(List(Introduce(hyp("j", "V"))))
  }

  it should "produce multiple Clears in input order then goal Modify for multi-hyp elimination" in {
    val node = tn(
      obl(List(hyp("x", "T"), hyp("y", "U")), "P x y"),
      obl(Nil, "Q")
    )
    Effects.derive(node, 0) shouldBe
      Effect(List(Clear("x"), Clear("y"), Modify("⊢", "P x y", "Q")))
  }

  it should "produce hyp-Modify before goal-Modify when both change simultaneously" in {
    val node = tn(obl(List(hyp("h", "T1")), "P"), obl(List(hyp("h", "T2")), "Q"))
    Effects.derive(node, 0) shouldBe
      Effect(List(Modify("h", "T1", "T2"), Modify("⊢", "P", "Q")))
  }

  it should "produce all four action kinds in correct order for a complex tactic" in {
    // [a:T1, b:U] ⊢ P  →  [a:T2, c:V] ⊢ Q  (b cleared, a type-changed, c introduced, goal changed)
    val node = tn(
      obl(List(hyp("a", "T1"), hyp("b", "U")), "P"),
      obl(List(hyp("a", "T2"), hyp("c", "V")), "Q")
    )
    Effects.derive(node, 0) shouldBe Effect(List(
      Clear("b"),
      Modify("a", "T1", "T2"),
      Introduce(hyp("c", "V")),
      Modify("⊢", "P", "Q")
    ))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — derive / deriveAll: multi-branch (2 output obligations)
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.derive (multi-branch)" should "produce the nil-case effect for induction branch 0" in {
    Effects.derive(indNode, 0) shouldBe
      Effect(List(Clear("xs"), Modify("⊢", "P xs", "P []")))
  }

  it should "produce the cons-case effect for induction branch 1" in {
    Effects.derive(indNode, 1) shouldBe Effect(List(
      Clear("xs"),
      Introduce(hyp("ih", "P t")),
      Introduce(hyp("h", "Nat")),
      Modify("⊢", "P xs", "P (h::t)")
    ))
  }

  it should "produce independent effects for a cases-style split" in {
    val casesNode = tn(
      obl(List(hyp("h", "A∧B")), "Q"),
      obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "Q"),
      obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "Q")
    )
    Effects.derive(casesNode, 0) shouldBe Effect(List(Introduce(hyp("h1", "A"))))
    Effects.derive(casesNode, 1) shouldBe Effect(List(Introduce(hyp("h2", "B"))))
  }

  "Effects.deriveAll" should "return a list of length 2 for a 2-branch node" in {
    Effects.deriveAll(indNode).size shouldBe 2
  }

  it should "agree with derive(node, i) for each branch index" in {
    Effects.deriveAll(indNode) shouldBe
      List(Effects.derive(indNode, 0), Effects.derive(indNode, 1))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — deriveAll: leaf tactic (0 output obligations)
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.deriveAll (leaf)" should "return an empty list" in {
    Effects.deriveAll(tn(obl(List(hyp("h", "P")), "P"))) shouldBe Nil
  }

  "Effects.derive (leaf)" should "throw for any branch index" in {
    val leaf = tn(obl(List(hyp("h", "P")), "P"))
    an [Exception] should be thrownBy Effects.derive(leaf, 0)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — apply: each action type + goal/hyp same-string disambiguation
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.apply" should "remove the named hypothesis via Clear, leaving others and goal intact" in {
    applyOne(Clear("h"), obl(List(hyp("h", "Nat"), hyp("k", "T")), "P")) shouldBe
      obl(List(hyp("k", "T")), "P")
  }

  it should "append a new hypothesis at the END via Introduce, leaving goal intact" in {
    val result = applyOne(Introduce(hyp("k", "T")), obl(List(hyp("h", "Nat")), "P"))
    result shouldBe obl(List(hyp("h", "Nat"), hyp("k", "T")), "P")
    result.hypotheses.last shouldBe hyp("k", "T")
  }

  it should "replace the goal via Modify('⊢', old, snew), leaving Γ unchanged" in {
    applyOne(Modify("⊢", "P a", "P b"), obl(List(hyp("h", "Nat")), "P a")) shouldBe
      obl(List(hyp("h", "Nat")), "P b")
  }

  it should "replace a hypothesis type in-place via Modify(name, old, snew), leaving goal unchanged" in {
    applyOne(Modify("k", "P a", "P b"), obl(List(hyp("h", "a=b"), hyp("k", "P a")), "Q")) shouldBe
      obl(List(hyp("h", "a=b"), hyp("k", "P b")), "Q")
  }

  it should "leave the obligation unchanged for an empty Effect" in {
    val o = obl(List(hyp("h", "Nat")), "P h")
    Effects.apply(Effect(Nil), o) shouldBe o
  }

  it should "target ONLY the goal when prop='⊢', even if a hyp type equals the goal string" in {
    // goal = "P a", h: P a — Modify("⊢",...) must change only the goal
    val o = obl(List(hyp("h", "P a")), "P a")
    applyOne(Modify("⊢", "P a", "P b"), o) shouldBe obl(List(hyp("h", "P a")), "P b")
  }

  it should "target ONLY the named hyp when prop is a name, even if the goal has the same string" in {
    // goal = "P a", h: P a — Modify("h",...) must change only h's type
    val o = obl(List(hyp("h", "P a")), "P a")
    applyOne(Modify("h", "P a", "P b"), o) shouldBe obl(List(hyp("h", "P b")), "P a")
  }

  it should "target only the specifically named hyp when multiple hyps and the goal all share a string" in {
    // h1: P a, h2: P a, goal: P a — Modify("h2",...) must touch only h2
    val o = obl(List(hyp("h1", "P a"), hyp("h2", "P a")), "P a")
    applyOne(Modify("h2", "P a", "P b"), o) shouldBe
      obl(List(hyp("h1", "P a"), hyp("h2", "P b")), "P a")
  }

  it should "leave the goal unchanged when a hyp-name Modify changes a hyp type" in {
    applyOne(Modify("h", "a=b", "b=a"), obl(List(hyp("h", "a=b")), "P")).goal shouldBe "P"
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — apply: precision / non-interference
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.apply (precision)" should "Clear only the named hypothesis — others unaffected" in {
    applyOne(Clear("b"), obl(List(hyp("a", "T"), hyp("b", "U"), hyp("c", "V")), "P")) shouldBe
      obl(List(hyp("a", "T"), hyp("c", "V")), "P")
  }

  it should "Modify('⊢') not alter Γ at all" in {
    val o = obl(List(hyp("h", "T")), "P")
    applyOne(Modify("⊢", "P", "Q"), o).hypotheses shouldBe o.hypotheses
  }

  it should "Modify(hypName) not alter the goal" in {
    applyOne(Modify("h", "a=b", "b=a"), obl(List(hyp("h", "a=b")), "P")).goal shouldBe "P"
  }

  it should "Modify update the hypothesis IN-PLACE preserving position" in {
    applyOne(Modify("b", "T2", "T4"), obl(List(hyp("a", "T1"), hyp("b", "T2"), hyp("c", "T3")), "P")) shouldBe
      obl(List(hyp("a", "T1"), hyp("b", "T4"), hyp("c", "T3")), "P")
  }

  it should "apply sequential Clears independently" in {
    Effects.apply(
      Effect(List(Clear("a"), Clear("c"))),
      obl(List(hyp("a", "T"), hyp("b", "U"), hyp("c", "V")), "P")
    ) shouldBe obl(List(hyp("b", "U")), "P")
  }

  it should "apply sequential Introduces stacking in declaration order" in {
    Effects.apply(
      Effect(List(Introduce(hyp("a", "T")), Introduce(hyp("b", "U")))),
      obl(Nil, "P")
    ) shouldBe obl(List(hyp("a", "T"), hyp("b", "U")), "P")
  }

  it should "apply a multi-action Effect in sequence (Clear then goal Modify)" in {
    Effects.apply(
      Effect(List(Clear("k"), Modify("⊢", "P", "Q"))),
      obl(List(hyp("h", "T"), hyp("k", "U")), "P")
    ) shouldBe obl(List(hyp("h", "T")), "Q")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — derivation ordering: [D2] why Clear→Modify→Introduce→goalModify matters
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.derive (ordering)" should
    "place Clear before Introduce when a cleared hyp and a new hyp share the same type" in {
    // h:T cleared, k:T introduced — must be [Clear("h"), Introduce(k:T)], not reversed,
    // so that any subsequent type-change Modify targeting "T" finds the right hypothesis
    val node = tn(obl(List(hyp("h", "T")), "P"), obl(List(hyp("k", "T")), "P"))
    Effects.derive(node, 0) shouldBe Effect(List(Clear("h"), Introduce(hyp("k", "T"))))
  }

  it should "place a type-change Modify before an Introduce that has the same old type" in {
    // h: T1→T2, j: T1 introduced — [Modify("h","T1","T2"), Introduce(j:T1)]
    // Reversed would leave two T1-typed entries when Modify runs, causing ambiguity
    val node = tn(
      obl(List(hyp("h", "T1")), "P"),
      obl(List(hyp("h", "T2"), hyp("j", "T1")), "P")
    )
    val Effect(actions) = Effects.derive(node, 0)
    actions(0) shouldBe Modify("h", "T1", "T2")
    actions(1) shouldBe Introduce(hyp("j", "T1"))
  }

  it should "emit multiple Clears in INPUT hypothesis list order" in {
    val node = tn(
      obl(List(hyp("a", "T"), hyp("b", "U"), hyp("c", "V")), "P"),
      obl(Nil, "Q")
    )
    val Effect(actions) = Effects.derive(node, 0)
    actions.take(3) shouldBe List(Clear("a"), Clear("b"), Clear("c"))
  }

  it should "emit multiple Introduces in OUTPUT hypothesis list order" in {
    val node = tn(
      obl(Nil, "P"),
      obl(List(hyp("x", "T"), hyp("y", "U"), hyp("z", "V")), "Q")
    )
    val Effect(actions) = Effects.derive(node, 0)
    actions.take(3) shouldBe
      List(Introduce(hyp("x", "T")), Introduce(hyp("y", "U")), Introduce(hyp("z", "V")))
  }

  it should "always place the goal Modify last" in {
    val node = tn(
      obl(List(hyp("a", "T1"), hyp("b", "U")), "P"),
      obl(List(hyp("a", "T2"), hyp("c", "V")), "Q")
    )
    Effects.derive(node, 0).actions.last shouldBe Modify("⊢", "P", "Q")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — round-trip: apply(derive(node,i), inputObl) ≃ outputObligations(i)  [D4]
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects round-trip" should "hold for an identity tactic" in {
    assertRoundTrip(tn(obl(List(hyp("h", "Nat")), "P h"), obl(List(hyp("h", "Nat")), "P h")), 0)
  }

  it should "hold for a goal-only rewrite" in {
    assertRoundTrip(tn(obl(List(hyp("h", "a=b")), "P a"), obl(List(hyp("h", "a=b")), "P b")), 0)
  }

  it should "hold for a pure hypothesis removal" in {
    assertRoundTrip(tn(obl(List(hyp("h", "Nat")), "P h"), obl(Nil, "P h")), 0)
  }

  it should "hold for intro h (new hyp + goal change)" in {
    assertRoundTrip(tn(obl(Nil, "∀x:Nat, P x"), obl(List(hyp("h", "Nat")), "P h")), 0)
  }

  it should "hold for intro x y (two new hyps + goal change)" in {
    assertRoundTrip(
      tn(obl(Nil, "∀x y:Nat, P x y"), obl(List(hyp("x", "Nat"), hyp("y", "Nat")), "P x y")), 0)
  }

  it should "hold for an in-place hypothesis type change" in {
    assertRoundTrip(
      tn(obl(List(hyp("h", "a=b"), hyp("k", "P a")), "Q"),
         obl(List(hyp("h", "a=b"), hyp("k", "P b")), "Q")), 0)
  }

  it should "hold for clear + goal rewrite" in {
    assertRoundTrip(
      tn(obl(List(hyp("h", "T"), hyp("k", "U")), "P"), obl(List(hyp("h", "T")), "Q")), 0)
  }

  it should "hold for replacing one hyp with a differently-named one" in {
    assertRoundTrip(tn(obl(List(hyp("h", "T")), "P"), obl(List(hyp("k", "V")), "P")), 0)
  }

  it should "hold for have-style Introduce without goal change" in {
    assertRoundTrip(
      tn(obl(List(hyp("h", "T")), "P"), obl(List(hyp("h", "T"), hyp("j", "V")), "P")), 0)
  }

  it should "hold for multiple clears + goal change" in {
    assertRoundTrip(
      tn(obl(List(hyp("x", "T"), hyp("y", "U")), "P x y"), obl(Nil, "Q")), 0)
  }

  it should "hold when both a hyp type and the goal change simultaneously" in {
    assertRoundTrip(tn(obl(List(hyp("h", "T1")), "P"), obl(List(hyp("h", "T2")), "Q")), 0)
  }

  it should "hold for the complex all-four-kinds tactic" in {
    assertRoundTrip(
      tn(obl(List(hyp("a", "T1"), hyp("b", "U")), "P"),
         obl(List(hyp("a", "T2"), hyp("c", "V")), "Q")), 0)
  }

  it should "hold for induction branch 0 (nil case)" in { assertRoundTrip(indNode, 0) }
  it should "hold for induction branch 1 (cons case)" in { assertRoundTrip(indNode, 1) }

  it should "hold for cases branch 0" in {
    val n = tn(obl(List(hyp("h", "A∧B")), "Q"),
               obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "Q"),
               obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "Q"))
    assertRoundTrip(n, 0)
  }

  it should "hold for cases branch 1" in {
    val n = tn(obl(List(hyp("h", "A∧B")), "Q"),
               obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "Q"),
               obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "Q"))
    assertRoundTrip(n, 1)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — defensive / fail-fast
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects (fail-fast)" should "throw when derive is called with a branch index >= output count" in {
    an [Exception] should be thrownBy Effects.derive(tn(obl(Nil, "P")), 0)
    an [Exception] should be thrownBy Effects.derive(tn(obl(Nil, "P"), obl(Nil, "Q")), 1)
  }

  it should "throw when Clear names a hypothesis not present in Γ" in {
    an [Exception] should be thrownBy applyOne(Clear("nonexistent"), obl(List(hyp("h", "T")), "P"))
  }

  it should "throw when Modify('⊢') old does not match the current goal" in {
    an [Exception] should be thrownBy
      applyOne(Modify("⊢", "WRONG", "P b"), obl(List(hyp("h", "Nat")), "P a"))
  }

  it should "throw when Modify names a hypothesis not present in Γ" in {
    an [Exception] should be thrownBy
      applyOne(Modify("nonexistent", "T", "U"), obl(List(hyp("h", "T")), "P"))
  }

  it should "throw when Modify(hypName) old does not match the hypothesis's current type" in {
    an [Exception] should be thrownBy
      applyOne(Modify("h", "WRONG", "T2"), obl(List(hyp("h", "T1")), "P"))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 9 — multi-branch apply independence
  // ═══════════════════════════════════════════════════════════════════════════

  "Effects.apply (multi-branch independence)" should
    "produce distinct obligations from the two induction branch effects applied to the same input" in {
    val effects = Effects.deriveAll(indNode)
    Effects.apply(effects(0), indIn) should not equal Effects.apply(effects(1), indIn)
  }

  it should "produce obligations that both differ from the original input obligation" in {
    val effects = Effects.deriveAll(indNode)
    Effects.apply(effects(0), indIn) should not equal indIn
    Effects.apply(effects(1), indIn) should not equal indIn
  }

  it should "not mutate the input obligation across repeated calls (apply is pure)" in {
    val effects = Effects.deriveAll(indNode)
    val first   = Effects.apply(effects(0), indIn)
    val second  = Effects.apply(effects(0), indIn)
    first  shouldBe second
    indIn  shouldBe obl(List(hyp("xs", "List Nat")), "P xs")
  }
