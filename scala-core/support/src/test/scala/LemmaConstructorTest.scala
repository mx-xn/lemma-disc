import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class LemmaConstructorTest extends AnyFlatSpec with Matchers:

  // ── shared test fixtures ──────────────────────────────────────────────────
  private val emptySum = TacticSummary(Set.empty, Nil)

  private def obl(hyps: List[Hypothesis], goal: String) = Obligation(hyps, goal)
  private def hyp(name: String, typ: String)             = Hypothesis(name, typ)

  private def hole(goal: String, hyps: List[Hypothesis] = Nil): Hole =
    Hole("ℓ", obl(hyps, goal))

  private def leaf(hyps: List[Hypothesis] = Nil, goal: String = "P"): Leaf =
    Leaf("tac", obl(hyps, goal), emptySum)

  // Build a Node whose output obligations mirror the children's root obligations.
  // `outHyps(i)` are the hypotheses in the i-th output obligation.
  private def mkNode(
    parentHyps: List[Hypothesis],
    parentGoal: String,
    outHyps:    List[List[Hypothesis]],
    outGoals:   List[String],
    kids:       List[PartialTree]
  ): Node =
    Node(
      "tac",
      obl(parentHyps, parentGoal),
      outHyps.zip(outGoals).map((hs, g) => obl(hs, g)),
      TacticSummary(Set.empty, outHyps.map(_ => Map.empty)),
      kids
    )

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Hole cases
  // ═══════════════════════════════════════════════════════════════════════════

  "computeLem" should "return Some(goal) for a hole (Lem(•ℓ) = gℓ)" in {
    // The hole's goal is the proposition that must be filled in
    LemmaConstructor.computeLem(Hole("ℓ1", obl(Nil, "P ∧ Q"))) shouldBe Some("P ∧ Q")
  }

  it should "return Some(goal) for a hole regardless of its hypothesis list" in {
    // Hypotheses in the hole's obligation do NOT affect what Lem returns — only the goal matters
    LemmaConstructor.computeLem(
      Hole("ℓ2", obl(List(hyp("h1","Nat"), hyp("h2","Bool")), "h1 + 1 = h2"))
    ) shouldBe Some("h1 + 1 = h2")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Leaf cases
  // ═══════════════════════════════════════════════════════════════════════════

  it should "return None (⊤) for a leaf — a closed tactic node contributes nothing (Lem(a) = ⊤)" in {
    LemmaConstructor.computeLem(leaf()) shouldBe None
  }

  it should "return None for a leaf even when it has a non-trivial summary" in {
    // The TacticSummary is used by SupportCalc, not computeLem; Lem of any leaf is always ⊤
    val richLeaf = Leaf("exact h1", obl(List(hyp("h1","Nat")), "P"),
                       TacticSummary(Set("h1"), Nil))
    LemmaConstructor.computeLem(richLeaf) shouldBe None
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Node: all children yield ⊤ → None
  // ═══════════════════════════════════════════════════════════════════════════

  it should "return None when all children are leaves (every branch is ⊤, conjunction of ⊤ is ⊤)" in {
    val n = mkNode(Nil, "P", List(Nil, Nil), List("Q","R"), List(leaf(), leaf()))
    LemmaConstructor.computeLem(n) shouldBe None
  }

  it should "return None for a node with no children (degenerate — empty parts list)" in {
    // A tactic node that spawns no sub-goals is semantically a leaf; Lem = ⊤
    val n = Node("tac", obl(Nil,"P"), Nil, TacticSummary(Set.empty, Nil), Nil)
    LemmaConstructor.computeLem(n) shouldBe None
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Node: holes with no new hypotheses → conjunction of goals
  // ═══════════════════════════════════════════════════════════════════════════

  it should "return conjunction of hole goals when output obligations add no new hypotheses" in {
    // parent Γ={h1}, both output obligations also have Γ={h1} → Γᵢ\Γ = ∅ in each branch
    val ph = List(hyp("h1","Nat"))
    val n  = mkNode(ph, "P", List(ph, ph), List("goalA","goalB"),
                   List(hole("goalA", ph), hole("goalB", ph)))
    LemmaConstructor.computeLem(n) shouldBe Some("goalA ∧ goalB")
  }

  it should "filter out ⊤ (leaf) children and keep only hole children in the conjunction" in {
    // [Leaf(⊤), Hole(goal2)] → parts has only goal2
    val ph = List(hyp("h1","Nat"))
    val n  = mkNode(ph, "P", List(ph, ph), List("Q","goal2"),
                   List(leaf(ph,"Q"), hole("goal2", ph)))
    LemmaConstructor.computeLem(n) shouldBe Some("goal2")
  }

  it should "filter ⊤ regardless of child position — [Hole, Leaf] ordering" in {
    val ph = List(hyp("h1","Nat"))
    val n  = mkNode(ph, "P", List(ph, ph), List("goal1","Q"),
                   List(hole("goal1", ph), leaf(ph,"Q")))
    LemmaConstructor.computeLem(n) shouldBe Some("goal1")
  }

  it should "filter all three ⊤ leaves from a three-child node, keeping only holes" in {
    // [Hole(g1), Leaf(⊤), Hole(g2)] → conjunction of g1 and g2 only
    val ph = List(hyp("h1","Nat"))
    val n  = mkNode(ph, "P", List(ph, ph, ph), List("g1","Q","g2"),
                   List(hole("g1",ph), leaf(ph,"Q"), hole("g2",ph)))
    LemmaConstructor.computeLem(n) shouldBe Some("g1 ∧ g2")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Node: new hypotheses in output obligation → implication wrap
  // ═══════════════════════════════════════════════════════════════════════════

  it should "wrap with an implication when a single new hypothesis appears in a branch" in {
    // parent Γ={h1:Nat}, output Γ₀={h1:Nat, h3:Bool} → Γ₀\Γ = {h3:Bool}
    // Lem(branch) = "(h3 : Bool) → Q"
    val ph = List(hyp("h1","Nat"))
    val ch = List(hyp("h1","Nat"), hyp("h3","Bool"))
    val n  = mkNode(ph, "P", List(ch), List("Q"), List(hole("Q", ch)))
    LemmaConstructor.computeLem(n) shouldBe Some("(h3 : Bool) → Q")
  }

  it should "chain multiple new hypotheses as separate binders, not conjoin with ∧" in {
    // Γ₀\Γ = {h2:Int, h3:Bool} → "(h2 : Int) → (h3 : Bool) → Q"
    // (∧-joined name:type pairs would be a Lean type error — see LemmaConstructor.scala)
    val ph = List(hyp("h1","Nat"))
    val ch = List(hyp("h1","Nat"), hyp("h2","Int"), hyp("h3","Bool"))
    val n  = mkNode(ph, "P", List(ch), List("Q"), List(hole("Q", ch)))
    LemmaConstructor.computeLem(n) shouldBe Some("(h2 : Int) → (h3 : Bool) → Q")
  }

  it should "not treat a hypothesis as new when the parent context already has that name" in {
    // parent has h1,h2; output obligation has h1,h2 — nothing is actually new
    val hs = List(hyp("h1","Nat"), hyp("h2","Bool"))
    val n  = mkNode(hs, "P", List(hs), List("Q"), List(hole("Q", hs)))
    LemmaConstructor.computeLem(n) shouldBe Some("Q")
  }

  it should "mix new-hyp and no-new-hyp children in the same conjunction" in {
    // child0 output adds h3 → "(h3 : Bool) → goal0"
    // child1 output adds nothing → "goal1"
    val ph  = List(hyp("h1","Nat"))
    val ch0 = List(hyp("h1","Nat"), hyp("h3","Bool"))
    val ch1 = List(hyp("h1","Nat"))
    val n   = mkNode(ph, "P", List(ch0, ch1), List("goal0","goal1"),
                    List(hole("goal0", ch0), hole("goal1", ch1)))
    // The implication part must be wrapped: ((h3:Bool)→goal0) ∧ goal1, not (h3:Bool)→(goal0 ∧ goal1)
    LemmaConstructor.computeLem(n) shouldBe Some("((h3 : Bool) → goal0) ∧ goal1")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — Node: two-level nesting
  // ═══════════════════════════════════════════════════════════════════════════

  it should "propagate Lem correctly through two levels of node nesting" in {
    // inner: parent={h1,h2}, output=[{h1,h2}], child=Hole("R") → Lem=Some("R")
    // outer: parent={h1},    output=[{h1,h2}], child=innerNode
    //        Γ₀\{h1} = {h2:Bool} → "(h2 : Bool) → R"
    val rootHyps  = List(hyp("h1","Nat"))
    val innerHyps = List(hyp("h1","Nat"), hyp("h2","Bool"))

    val inner = mkNode(innerHyps, "S", List(innerHyps), List("R"), List(hole("R", innerHyps)))
    val outer = mkNode(rootHyps,  "P", List(innerHyps), List("S"), List(inner))

    LemmaConstructor.computeLem(outer) shouldBe Some("(h2 : Bool) → R")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — provenance and field assembly
  // ═══════════════════════════════════════════════════════════════════════════

  "constructLemma" should "preserve fragment provenance fields unchanged" in {
    val frag = Fragment(42, "Foo.lean", "my_lemma",
                        obl(Nil, "True"), Hole("ℓ", obl(Nil, "True")))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.fragmentId shouldBe 42
    lemma.sourceFile  shouldBe "Foo.lean"
    lemma.declName    shouldBe "my_lemma"
  }

  it should "set conclusion to the root obligation's goal" in {
    val frag = Fragment(0, "F.lean", "f",
                        obl(List(hyp("h1","Nat")), "the_goal"),
                        leaf(List(hyp("h1","Nat")), "the_goal"))
    LemmaConstructor.constructLemma(frag).conclusion shouldBe "the_goal"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — premises: filter rootObligation hyps by computed support
  // ═══════════════════════════════════════════════════════════════════════════

  it should "produce empty premises when the support is ∅" in {
    // Leaf with no directlyUsed → support=∅ → no hypothesis passes the filter
    val frag = Fragment(0, "F.lean", "f",
                        obl(List(hyp("h1","Nat")), "P"),
                        Leaf("tac", obl(List(hyp("h1","Nat")), "P"),
                             TacticSummary(Set.empty, Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.premises  shouldBe Nil
    lemma.scopeVars shouldBe Nil
  }

  it should "include only root hypotheses whose names appear in the support" in {
    // Root has h1,h2,h3; support={h1,h3} → premises=[h1:T1, h3:T3], h2 excluded to scopeVars
    val rootHyps = List(hyp("h1","T1"), hyp("h2","T2"), hyp("h3","T3"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "P"),
                        Leaf("tac", obl(rootHyps, "P"),
                             TacticSummary(Set("h1","h3"), Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.premises  shouldBe List("h1 : T1", "h3 : T3")
    lemma.scopeVars shouldBe Nil
  }

  it should "preserve the hypothesis declaration order from rootObligation in premises" in {
    // Support contains all three; the list order (h1, h2, h3) must be maintained
    val hyps = List(hyp("h1","A"), hyp("h2","B"), hyp("h3","C"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(hyps, "G"),
                        Leaf("tac", obl(hyps, "G"), TacticSummary(Set("h1","h2","h3"), Nil)))
    LemmaConstructor.constructLemma(frag).premises shouldBe List("h1 : A", "h2 : B", "h3 : C")
  }

  it should "drop universe-polymorphic type binders (`_ : Type u_i`) from premises" in {
    // `α : Type u_1` and `β : Type u_2` are dropped; ordinary premises like
    // `xs : List α` survive even though their types mention the dropped vars
    // (Lean auto-binds free type variables implicitly).
    val hyps = List(
      hyp("α",  "Type u_1"),
      hyp("β",  "Type u_2"),
      hyp("xs", "List α"),
      hyp("ys", "List β"),
    )
    val frag = Fragment(0, "F.lean", "f",
                        obl(hyps, "G"),
                        Leaf("tac", obl(hyps, "G"),
                             TacticSummary(Set("α","β","xs","ys"), Nil)))
    LemmaConstructor.constructLemma(frag).premises shouldBe
      List("xs : List α", "ys : List β")
  }

  it should "keep non-universe `Type`-shaped binders (e.g. `Type`, `Type 0`)" in {
    // Only the universe-polymorphic shape `Type u_<id>` is dropped; concrete
    // `Type` levels are kept because they are not the Lean auto-bind idiom.
    val hyps = List(
      hyp("α", "Type"),
      hyp("β", "Type 0"),
      hyp("γ", "Type 1"),
    )
    val frag = Fragment(0, "F.lean", "f",
                        obl(hyps, "G"),
                        Leaf("tac", obl(hyps, "G"),
                             TacticSummary(Set("α","β","γ"), Nil)))
    LemmaConstructor.constructLemma(frag).premises shouldBe
      List("α : Type", "β : Type 0", "γ : Type 1")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — body and statement construction
  // ═══════════════════════════════════════════════════════════════════════════

  it should "set body=True for a leaf tree (Lem=⊤) and drop it from the statement" in {
    // When body="True", no extra binder is lifted from the body.
    val frag = Fragment(0, "F.lean", "f",
                        obl(List(hyp("h1","Nat")), "P"),
                        Leaf("tac", obl(List(hyp("h1","Nat")), "P"),
                             TacticSummary(Set("h1"), Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.body      shouldBe "True"
    lemma.statement shouldBe "(h1 : Nat) : P"
  }

  it should "lift the body into a fresh-name binder when Lem is not ⊤ (hole tree)" in {
    // body = hole's goal. With no premises, the body itself gets lifted with a fresh name.
    val frag = Fragment(0, "F.lean", "f",
                        obl(Nil, "outer"),
                        Hole("ℓ1", obl(Nil, "inner")))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.body      shouldBe "inner"
    lemma.statement shouldBe "(h1 : inner) : outer"
  }

  it should "produce just the conclusion when there are no premises and body=True" in {
    // No binders at all → statement = conclusion (no colon needed)
    val frag = Fragment(0, "F.lean", "f",
                        obl(Nil, "P"),
                        Leaf("tac", obl(Nil, "P"), TacticSummary(Set.empty, Nil)))
    LemmaConstructor.constructLemma(frag).statement shouldBe "P"
  }

  it should "render each premise as a Lean binder before the colon" in {
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Bool"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "P"),
                        Leaf("tac", obl(rootHyps, "P"),
                             TacticSummary(Set("h1","h2"), Nil)))
    LemmaConstructor.constructLemma(frag).statement shouldBe "(h1 : Nat) (h2 : Bool) : P"
  }

  it should "lift body into a binder after premises when both are present" in {
    // h1 is not in support and not referenced in conclusion "P" or body "Q" → dropped from scope_vars.
    // Fresh name for body avoids only h2 (premise) → gets h1.
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Bool"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "P"),
                        // Node: U={h2}, π={}, child=Hole(goal="Q") → body="Q"
                        Node("tac",
                             obl(rootHyps, "P"),
                             List(obl(rootHyps, "Q")),
                             TacticSummary(Set("h2"), List(Map.empty)),
                             List(Hole("ℓ1", obl(rootHyps, "Q")))))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars  shouldBe Nil
    lemma.premises   shouldBe List("h2 : Bool")
    lemma.body       shouldBe "Q"
    lemma.statement  shouldBe "(h2 : Bool) (h1 : Q) : P"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — end-to-end integration
  // ═══════════════════════════════════════════════════════════════════════════

  // ═══════════════════════════════════════════════════════════════════════════
  // computeLem — deeper trees: nested nodes, varied hyp types, multiple branches
  // ═══════════════════════════════════════════════════════════════════════════

  "computeLem" should "propagate Lem through a nested node child and wrap the implication when conjoining" in {
    // root(h1) has two branches:
    //   branch0 output adds h2:Bool → child is nodeMid(h1,h2) → hole("mid_goal",[h1,h2])
    //     computeLem(nodeMid) = "mid_goal"  (no new hyps at nodeMid's level)
    //     root contribution: "(h2 : Bool) → mid_goal"
    //   branch1 output has same hyps as root → child is hole("plain_goal",[h1])
    //     root contribution: "plain_goal"
    //   conjunction wraps the implication: "((h2 : Bool) → mid_goal) ∧ plain_goal"
    val rootHyps = List(hyp("h1","Nat"))
    val midHyps  = List(hyp("h1","Nat"), hyp("h2","Bool"))

    val nodeMid = mkNode(midHyps, "mid_obl",
                         List(midHyps), List("mid_goal"),
                         List(hole("mid_goal", midHyps)))
    val root    = mkNode(rootHyps, "P",
                         List(midHyps, rootHyps), List("mid_obl", "plain_goal"),
                         List(nodeMid, hole("plain_goal", rootHyps)))

    LemmaConstructor.computeLem(root) shouldBe Some("((h2 : Bool) → mid_goal) ∧ plain_goal")
  }

  it should "build a three-level implication chain as each node adds a new hypothesis" in {
    // root(h1:Nat) → mid adds h2:Bool → inner adds h3:Prop → hole("S")
    // computeLem(inner) = "(h3 : Prop) → S"
    // computeLem(mid)   = "(h2 : Bool) → (h3 : Prop) → S"
    val h1     = List(hyp("h1","Nat"))
    val h1h2   = List(hyp("h1","Nat"), hyp("h2","Bool"))
    val h1h2h3 = List(hyp("h1","Nat"), hyp("h2","Bool"), hyp("h3","Prop"))

    val inner = mkNode(h1h2,  "inner_obl", List(h1h2h3), List("S"), List(hole("S", h1h2h3)))
    val mid   = mkNode(h1,    "mid_obl",   List(h1h2),   List("inner_obl"), List(inner))

    LemmaConstructor.computeLem(mid) shouldBe Some("(h2 : Bool) → (h3 : Prop) → S")
  }

  it should "chain four levels of nesting including function types in hypothesis names" in {
    // Each level adds a hypothesis of a more complex type:
    //   h2:List Nat (level 1), h3:Nat → Bool (level 2), h4:α → α → Bool (level 3) → hole("D")
    // The → inside type names must not confuse the single-part short-circuit (no wrapping here).
    val h1       = List(hyp("h1","Nat"))
    val h1h2     = List(hyp("h1","Nat"), hyp("h2","List Nat"))
    val h1h2h3   = List(hyp("h1","Nat"), hyp("h2","List Nat"), hyp("h3","Nat → Bool"))
    val h1h2h3h4 = List(hyp("h1","Nat"), hyp("h2","List Nat"),
                        hyp("h3","Nat → Bool"), hyp("h4","α → α → Bool"))

    val level3 = mkNode(h1h2h3, "C", List(h1h2h3h4), List("D"), List(hole("D", h1h2h3h4)))
    val level2 = mkNode(h1h2,   "B", List(h1h2h3),   List("C"), List(level3))
    val level1 = mkNode(h1,     "A", List(h1h2),     List("B"), List(level2))

    LemmaConstructor.computeLem(level1) shouldBe
      Some("(h2 : List Nat) → (h3 : Nat → Bool) → (h4 : α → α → Bool) → D")
  }

  it should "wrap an inner conjunction string when it appears as an implication antecedent in a conjunction" in {
    // nodeA(h1,h2:Bool) has two sub-holes with the same hyps → Lem = "goal_x ∧ goal_y"
    // root(h1): branch0 output adds h2:Bool → "(h2 : Bool) → goal_x ∧ goal_y"
    //           branch1 output same hyps → "goal_z"
    // "goal_x ∧ goal_y" has no →, but the full part "(h2:Bool) → goal_x ∧ goal_y" does,
    // so it gets wrapped: "((h2 : Bool) → goal_x ∧ goal_y) ∧ goal_z"
    val rootHyps  = List(hyp("h1","Nat"))
    val nodeAHyps = List(hyp("h1","Nat"), hyp("h2","Bool"))

    val nodeA = mkNode(nodeAHyps, "nodeA_obl",
                       List(nodeAHyps, nodeAHyps), List("goal_x","goal_y"),
                       List(hole("goal_x", nodeAHyps), hole("goal_y", nodeAHyps)))
    val root  = mkNode(rootHyps, "P",
                       List(nodeAHyps, rootHyps), List("nodeA_obl","goal_z"),
                       List(nodeA, hole("goal_z", rootHyps)))

    LemmaConstructor.computeLem(root) shouldBe Some("((h2 : Bool) → goal_x ∧ goal_y) ∧ goal_z")
  }

  it should "conjoin two deeply-nested implication branches and wrap both" in {
    // Left branch (depth 2): root→nodeL(adds h2:Bool)→nodeLL(adds h3:Prop)→hole("goal_L")
    //   computeLem(nodeLL) = "(h3 : Prop) → goal_L"
    //   root branch L: "(h2 : Bool) → (h3 : Prop) → goal_L"
    // Right branch (depth 1): root→nodeR(adds h4:Nat)→hole("goal_R")
    //   root branch R: "(h4 : Nat) → goal_R"
    // Both parts contain → → both get wrapped
    val rootH = List(hyp("a","Nat"))
    val hL    = List(hyp("a","Nat"), hyp("h2","Bool"))
    val hLL   = List(hyp("a","Nat"), hyp("h2","Bool"), hyp("h3","Prop"))
    val hR    = List(hyp("a","Nat"), hyp("h4","Nat"))

    val nodeLL = mkNode(hL, "LL_obl", List(hLL), List("goal_L"), List(hole("goal_L", hLL)))
    val nodeL  = mkNode(rootH, "L_obl", List(hL), List("LL_obl"), List(nodeLL))
    val nodeR  = mkNode(hR, "R_obl", List(hR), List("goal_R"), List(hole("goal_R", hR)))
    val root   = mkNode(rootH, "P",
                        List(rootH, hR), List("L_obl","R_obl"),
                        List(nodeL, nodeR))

    LemmaConstructor.computeLem(root) shouldBe
      Some("((h2 : Bool) → (h3 : Prop) → goal_L) ∧ ((h4 : Nat) → goal_R)")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — dependency maps
  // ═══════════════════════════════════════════════════════════════════════════

  "constructLemma" should "resolve a multi-valued dependency map to pull multiple root hypotheses into support" in {
    // node has π = {h2 → {h1, h3}}: if a child uses h2, then h1 and h3 from the root context
    // are both required. The leaf directly uses h2 → support = {h1, h3}.
    // body = "True" (only a leaf child → Lem = ⊤); premises = {h1, h3} from root.
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Nat"), hyp("h3","Nat"))
    val nodeSum  = TacticSummary(Set.empty, List(Map("h2" -> Set("h1","h3"))))
    val leafSum  = TacticSummary(Set("h2"), Nil)
    val frag = Fragment(99, "Test.lean", "dep_map_test",
                        obl(rootHyps, "Q"),
                        Node("tac", obl(rootHyps, "Q"),
                             List(obl(rootHyps, "R")),
                             nodeSum,
                             List(Leaf("exact h2", obl(rootHyps, "R"), leafSum))))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars shouldBe Nil
    lemma.premises  shouldBe List("h1 : Nat", "h3 : Nat")
    lemma.body      shouldBe "True"
    lemma.statement shouldBe "(h1 : Nat) (h3 : Nat) : Q"
  }

  it should "handle a large tree (two branches of depth 3, two-hop dependency maps) correctly" in {
    // Tree (7 nodes, two branches each of depth 3 from root):
    //
    //   root (h1:Nat, h2:Bool)
    //   ├── branch L → node_L → node_LL → hole "L_leaf_goal"
    //   └── branch R → node_R → node_RR → hole "R_leaf_goal"
    //
    // Summaries / dependency maps:
    //   node_L:   U={h2}, π[0]={}
    //   node_RR:  U={h4}, π[0]={}
    //   node_R:   U={},   π[0]={h4 → {h2}}      (h4 in node_RR resolves to h2 in node_R's ctx)
    //   root:     U={},   π[0]={}, π[1]={h2→{h1}} (h2 in branch R resolves to h1 from root)
    //
    // Support trace:
    //   A(node_LL)=∅, A(node_L)={h2} (U={h2})
    //   A(node_RR)={h4} (U={h4}), A(node_R)={h2} (h4→{h2})
    //   A(root): branch L: h2→π[0]=∅; branch R: h2→{h1} → support={h1}
    //
    // Lem trace:
    //   node_LL: child=hole_LLL, no new hyps → "L_leaf_goal"
    //   node_L:  child=node_LL,  no new hyps → "L_leaf_goal"
    //   node_RR: child=hole_RRR, no new hyps → "R_leaf_goal"
    //   node_R:  child=node_RR, adds h4:Nat  → "(h4 : Nat) → R_leaf_goal"
    //   root:    branch L no new hyps → "L_leaf_goal"
    //            branch R adds h3:Prop → "(h3 : Prop) → (h4 : Nat) → R_leaf_goal"
    //   body = "L_leaf_goal ∧ ((h3 : Prop) → (h4 : Nat) → R_leaf_goal)"
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Bool"))
    val rHyps    = List(hyp("h1","Nat"), hyp("h2","Bool"), hyp("h3","Prop"))
    val rrHyps   = List(hyp("h1","Nat"), hyp("h2","Bool"), hyp("h3","Prop"), hyp("h4","Nat"))

    val holeLLL = Hole("ℓL", obl(rootHyps, "L_leaf_goal"))
    val nodeLL  = mkNode(rootHyps, "L_inner",
                         List(rootHyps), List("L_leaf_goal"), List(holeLLL))
    val nodeL   = Node("tacL", obl(rootHyps, "branch_L_goal"),
                       List(obl(rootHyps, "L_inner")),
                       TacticSummary(Set("h2"), List(Map.empty)),
                       List(nodeLL))

    val holeRRR = Hole("ℓR", obl(rrHyps, "R_leaf_goal"))
    val nodeRR  = Node("tacRR", obl(rrHyps, "R_inner"),
                       List(obl(rrHyps, "R_leaf_goal")),
                       TacticSummary(Set("h4"), List(Map.empty)),
                       List(holeRRR))
    val nodeR   = Node("tacR", obl(rHyps, "branch_R_goal"),
                       List(obl(rrHyps, "R_inner")),
                       TacticSummary(Set.empty, List(Map("h4" -> Set("h2")))),
                       List(nodeRR))

    val rootTree = Node("tacRoot", obl(rootHyps, "final_goal"),
                        List(obl(rootHyps, "branch_L_goal"), obl(rHyps, "branch_R_goal")),
                        TacticSummary(Set.empty, List(Map.empty, Map("h2" -> Set("h1")))),
                        List(nodeL, nodeR))

    val frag  = Fragment(7, "BigTest.lean", "big_test",
                         obl(rootHyps, "final_goal"), rootTree)
    val lemma = LemmaConstructor.constructLemma(frag)

    lemma.scopeVars  shouldBe Nil
    lemma.premises   shouldBe List("h1 : Nat")
    lemma.body       shouldBe "L_leaf_goal ∧ ((h3 : Prop) → (h4 : Nat) → R_leaf_goal)"
    lemma.conclusion shouldBe "final_goal"
    // body lifted as one binder; h1 (premise), h3/h4 (in body) all blocked → h2 is fresh
    lemma.statement  shouldBe
      "(h1 : Nat) (h2 : L_leaf_goal ∧ ((h3 : Prop) → (h4 : Nat) → R_leaf_goal)) : final_goal"
  }

  it should "produce the correct full lemma for a realistic Nat.add inductive step fragment" in {
    // Context: proving `h1 + succ h2 = succ h2 + h1` given the induction hypothesis `ih`.
    //
    // The tactic "rw [Nat.add_succ, Nat.succ_add]" uses ih directly (U={ih}) and creates
    // one sub-goal `h1 + h2 = h2 + h1` left as a hole.  π₁ maps h1 → {ih} but because
    // the hole's support is ∅, no extra hypotheses are pulled through.
    //
    // Expected outcome:
    //   support  = {ih}                            (only ih is truly needed)
    //   premises = ["ih : h1+0=0+h1"]
    //   body     = "h1+h2=h2+h1"                  (the remaining sub-goal)
    //   statement = "(ih : h1+0=0+h1) → h1+h2=h2+h1 → h1+succ h2=succ h2+h1"
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Nat"), hyp("ih","h1+0=0+h1"))
    val frag = Fragment(
      7, "Commutativity.lean", "add_comm_step",
      obl(rootHyps, "h1+succ h2=succ h2+h1"),
      Node(
        "rw [Nat.add_succ, Nat.succ_add]",
        obl(rootHyps, "h1+succ h2=succ h2+h1"),
        List(obl(rootHyps, "h1+h2=h2+h1")),
        TacticSummary(Set("ih"), List(Map("h1" -> Set("ih")))),
        List(Hole("ℓ1", obl(rootHyps, "h1+h2=h2+h1")))
      )
    )
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars  shouldBe List("h1 : Nat", "h2 : Nat")
    lemma.premises   shouldBe List("ih : h1+0=0+h1")
    lemma.body       shouldBe "h1+h2=h2+h1"
    lemma.conclusion shouldBe "h1+succ h2=succ h2+h1"
    // h1/h2 are scope vars (taken), h3 is free in the avoid string → fresh name = h3
    lemma.statement  shouldBe
      "(h1 : Nat) (h2 : Nat) (ih : h1+0=0+h1) (h3 : h1+h2=h2+h1) : h1+succ h2=succ h2+h1"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // constructLemma — scope_var reachability filtering (new rules)
  // ═══════════════════════════════════════════════════════════════════════════

  it should "keep only scope_vars reachable from conclusion and drop the rest" in {
    // h1 appears in conclusion "h1 = h1" → reachable → kept.
    // h3 : Bool is not referenced anywhere in conclusion/body/premise types → dropped.
    // support = {h2}, so h2 is a premise, h1 and h3 are non-support scope candidates.
    val rootHyps = List(hyp("h1","Nat"), hyp("h2","Nat"), hyp("h3","Bool"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "h1 = h1"),
                        Leaf("tac", obl(rootHyps, "h1 = h1"),
                             TacticSummary(Set("h2"), Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars shouldBe List("h1 : Nat")
    lemma.premises  shouldBe List("h2 : Nat")
  }

  it should "transitively keep scope_vars whose names appear in types of already-reachable scope_vars" in {
    // conclusion "h1.length = 0" → seeds = {h1, length}
    // h1 : List h2 → expand: add {List, h2} to seeds → h2 now reachable → kept
    // h3 : Bool → "h3" never enters seeds → dropped
    val rootHyps = List(hyp("h1","List h2"), hyp("h2","Nat"), hyp("h3","Bool"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "h1.length = 0"),
                        Leaf("tac", obl(rootHyps, "h1.length = 0"),
                             TacticSummary(Set.empty, Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars shouldBe List("h1 : List h2", "h2 : Nat")
  }

  it should "always keep inst-prefixed scope_vars even when unreferenced in conclusion or body" in {
    // inst✝ : LT T starts with "inst" → unconditionally kept (type class instance rule).
    // e appears in conclusion "e = e" → kept via reachability.
    // unused : Bool has an unreachable name and no inst prefix → dropped.
    val rootHyps = List(hyp("inst✝","LT T"), hyp("e","T"), hyp("unused","Bool"))
    val frag = Fragment(0, "F.lean", "f",
                        obl(rootHyps, "e = e"),
                        Leaf("tac", obl(rootHyps, "e = e"),
                             TacticSummary(Set.empty, Nil)))
    val lemma = LemmaConstructor.constructLemma(frag)
    lemma.scopeVars shouldBe List("inst✝ : LT T", "e : T")
  }
