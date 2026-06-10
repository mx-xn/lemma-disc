import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class SupportCalcTest extends AnyFlatSpec with Matchers:

  // ── shared test fixtures ──────────────────────────────────────────────────
  private val emptyObl = Obligation(Nil, "True")

  private def leaf(used: Set[String]): Leaf =
    Leaf("tac", emptyObl, TacticSummary(used, Nil))

  private def hole(id: String = "ℓ"): Hole =
    Hole(id, emptyObl)

  private def node(
    u:    Set[String],
    maps: List[Map[String, Set[String]]],
    kids: List[PartialTree]
  ): Node =
    Node("tac", emptyObl, kids.map(_ => emptyObl), TacticSummary(u, maps), kids)

  // ── Supp-Hole ─────────────────────────────────────────────────────────────

  "computeSupport" should "return ∅ for a hole regardless of its obligation (Supp-Hole)" in {
    // Holes are open sub-goals; they never contribute hypotheses to the support
    SupportCalc.computeSupport(
      Hole("ℓ1", Obligation(List(Hypothesis("h1","Nat"), Hypothesis("h2","Bool")), "P"))
    ) shouldBe Set.empty
  }

  it should "return ∅ for a hole with an empty obligation (Supp-Hole trivial)" in {
    SupportCalc.computeSupport(Hole("ℓ2", emptyObl)) shouldBe Set.empty
  }

  // ── Supp-Leaf ─────────────────────────────────────────────────────────────

  it should "return ∅ for a leaf with empty directlyUsed (Supp-Leaf empty)" in {
    SupportCalc.computeSupport(leaf(Set.empty)) shouldBe Set.empty
  }

  it should "return {h1} for a leaf with directlyUsed={h1} (Supp-Leaf singleton)" in {
    SupportCalc.computeSupport(leaf(Set("h1"))) shouldBe Set("h1")
  }

  it should "return exactly directlyUsed for a leaf with multiple hypotheses (Supp-Leaf multi)" in {
    SupportCalc.computeSupport(leaf(Set("h1", "h2", "h3"))) shouldBe Set("h1", "h2", "h3")
  }

  // ── Supp-Comp: hole children (A_i = ∅, so pulled = ∅) ────────────────────

  it should "return only U when all children are holes — holes contribute no support (Supp-Comp)" in {
    // U={h1}, π₁={h2→{h1,h2}}, π₂={}, A₁=A₂=∅ → pulled=∅ → A={h1}
    // The rich π maps don't matter because the holes' A is empty; nothing to pull through
    val n = node(
      u    = Set("h1"),
      maps = List(Map("h2" -> Set("h1","h2")), Map.empty),
      kids = List(hole(), hole())
    )
    SupportCalc.computeSupport(n) shouldBe Set("h1")
  }

  // ── Supp-Comp: pulled contribution through dependency map ─────────────────

  it should "pull child support through the dependency map (Supp-Comp basic pull)" in {
    // U={}, π₁={h2→{h1}}, child Leaf A={h2} → pulled={h1} → A={h1}
    val n = node(
      u    = Set.empty,
      maps = List(Map("h2" -> Set("h1"))),
      kids = List(leaf(Set("h2")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h1")
  }

  it should "union U with all pulled hypotheses when both are non-empty (Supp-Comp union)" in {
    // U={h5}, π₁={h1→{h3}, h2→{h4}}, child A={h1,h2} → pulled={h3,h4} → A={h3,h4,h5}
    val n = node(
      u    = Set("h5"),
      maps = List(Map("h1" -> Set("h3"), "h2" -> Set("h4"))),
      kids = List(leaf(Set("h1", "h2")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h3", "h4", "h5")
  }

  it should "silently drop child-support hypotheses absent from the dependency map" in {
    // h_unknown is in A_child but not a key in π₁ — getOrElse gives ∅, so it disappears
    val n = node(
      u    = Set.empty,
      maps = List(Map("h1" -> Set("h3"))),
      kids = List(leaf(Set("h1", "h_unknown")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h3")
  }

  it should "accumulate contributions from multiple children via separate dependency maps" in {
    // π₁={h1→{h3}}, π₂={h2→{h4}}, child₁ A={h1}, child₂ A={h2} → A={h3,h4}
    val n = node(
      u    = Set.empty,
      maps = List(Map("h1" -> Set("h3")), Map("h2" -> Set("h4"))),
      kids = List(leaf(Set("h1")), leaf(Set("h2")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h3", "h4")
  }

  it should "handle mixed hole+leaf children: holes contribute nothing, leaves contribute normally" in {
    // child₀=Hole(A=∅), child₁=Leaf(A={h2}), π₀={}, π₁={h2→{h4}} → A={h4}
    val n = node(
      u    = Set.empty,
      maps = List(Map.empty, Map("h2" -> Set("h4"))),
      kids = List(hole(), leaf(Set("h2")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h4")
  }

  it should "deduplicate pulled hypotheses when multiple children map to the same name" in {
    // π₁={h1→{h3}}, π₂={h2→{h3}}, both children contribute {h3} → A={h3} not a multiset
    val n = node(
      u    = Set.empty,
      maps = List(Map("h1" -> Set("h3")), Map("h2" -> Set("h3"))),
      kids = List(leaf(Set("h1")), leaf(Set("h2")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h3")
  }

  it should "handle a dependency map entry that fans out to multiple hypotheses" in {
    // π₁={h1→{h3,h4,h5}}, child A={h1} → pulled={h3,h4,h5}
    val n = node(
      u    = Set.empty,
      maps = List(Map("h1" -> Set("h3", "h4", "h5"))),
      kids = List(leaf(Set("h1")))
    )
    SupportCalc.computeSupport(n) shouldBe Set("h3", "h4", "h5")
  }

  it should "propagate support through two levels of node nesting" in {
    // grandchild Leaf:  A = {h_leaf}
    // inner Node:  U={},  π₁={h_leaf→{h_mid}}   → A = {h_mid}
    // outer Node:  U={},  π₁={h_mid→{h_outer}}  → A = {h_outer}
    val grandchild = leaf(Set("h_leaf"))
    val inner = node(
      u    = Set.empty,
      maps = List(Map("h_leaf" -> Set("h_mid"))),
      kids = List(grandchild)
    )
    val outer = node(
      u    = Set.empty,
      maps = List(Map("h_mid" -> Set("h_outer"))),
      kids = List(inner)
    )
    SupportCalc.computeSupport(outer) shouldBe Set("h_outer")
  }

  it should "return only U for a degenerate node with no children" in {
    // zipWithIndex on empty list → no iterations → pulled = ∅ → A = U
    val n = Node("tac", emptyObl, Nil, TacticSummary(Set("h1"), Nil), Nil)
    SupportCalc.computeSupport(n) shouldBe Set("h1")
  }
