import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for [[Linearizer]] — DFS preorder of the proof tree, restricted to a
 *  vertex set.
 *
 *  [L1] Order is the TREE's DFS preorder filtered to the given set; not a
 *       topological sort of the POG edge-graph.
 *  [L2] Reordered {A,C}: chain A→B→C with edges (A,B)(A,C) → [A,C]. B sits
 *       between them in the tree but is absent from the set; the result is still
 *       a valid linearization because there is no B→C edge.
 *  [L3] Sibling order follows childIds list order (left-to-right proof order).
 *  [L4] Fail-fast when an ID is absent from the POG.
 */
class LinearizerTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private val dummyObl = Obligation(Nil, "g")
  private val dummyFp  = Footprint(Set.empty, Set.empty, false, Nil)
  private val dummySum = TacticSummary(Nil, Nil)

  private def tn(id: Int, parent: Option[Int], children: List[Int]): TacticNode =
    TacticNode(id, "tac", dummyObl, List.fill(children.size)(dummyObl), dummySum, parent, children)

  private def pog(rootId: Int, nodes: List[TacticNode]): ProofOrderingGraph =
    val bps = BranchPath.compute(nodes)
    ProofOrderingGraph("d", "theorem d : g", rootId, dummyObl,
      nodes.map(n => PogNode(n, dummyFp, bps(n.id))), Nil)

  private def isSubsequenceOf(sub: List[Int], full: List[Int]): Boolean =
    sub match
      case Nil    => true
      case h :: t => full.dropWhile(_ != h) match
        case Nil    => false
        case _ :: r => isSubsequenceOf(t, r)


  // ── fixtures ─────────────────────────────────────────────────────────────────

  // 0 → 1 → 2
  private val chainPog = pog(0,
    List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)))

  // 0 → {1, 2}
  private val forkPog = pog(0,
    List(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil)))

  // 0 → {1, 2};  2 → 3;  3 → {4, 5}.  Preorder: [0,1,2,3,4,5]
  private val deepPog = pog(0, List(
    tn(0, None, List(1, 2)), tn(1, Some(0), Nil),
    tn(2, Some(0), List(3)), tn(3, Some(2), List(4, 5)),
    tn(4, Some(3), Nil),     tn(5, Some(3), Nil)))

  // 0 → {1, 2, 3}
  private val triPog = pog(0,
    List(tn(0, None, List(1, 2, 3)), tn(1, Some(0), Nil),
         tn(2, Some(0), Nil),        tn(3, Some(0), Nil)))


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Degenerate inputs
  // ═══════════════════════════════════════════════════════════════════════════

  "Linearizer.linearize" should "return Nil for the empty set" in {
    Linearizer.linearize(Set.empty, chainPog) shouldBe Nil
  }

  it should "return [root] for a singleton containing the root" in {
    Linearizer.linearize(Set(0), chainPog) shouldBe List(0)
  }

  it should "return [leaf] for a singleton containing a leaf" in {
    Linearizer.linearize(Set(2), chainPog) shouldBe List(2)
  }

  it should "return the full DFS preorder for the complete vertex set" in {
    Linearizer.linearize(Set(0, 1, 2), chainPog) shouldBe List(0, 1, 2)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — Linear chain (0→1→2)  [L1, L2]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "yield [1] for the middle node of the chain" in {
    Linearizer.linearize(Set(1), chainPog) shouldBe List(1)
  }

  it should "yield [0,1] for the head pair of the chain" in {
    Linearizer.linearize(Set(0, 1), chainPog) shouldBe List(0, 1)
  }

  it should "yield [1,2] for the tail pair of the chain" in {
    Linearizer.linearize(Set(1, 2), chainPog) shouldBe List(1, 2)
  }

  it should "[L2] yield [0,2] for the reordered {A,C} pair (middle node absent)" in {
    // Key CLAUDE.md case: B (node 1) lies between A and C in the tree but is
    // excluded from the set. Result [A,C] is a valid linearization because
    // there is no edge B→C in the POG.
    Linearizer.linearize(Set(0, 2), chainPog) shouldBe List(0, 2)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Branching tree (0→{1,2})  [L3]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "yield [0,1,2] for the full fork" in {
    Linearizer.linearize(Set(0, 1, 2), forkPog) shouldBe List(0, 1, 2)
  }

  it should "yield [0,1] for root + left child of the fork" in {
    Linearizer.linearize(Set(0, 1), forkPog) shouldBe List(0, 1)
  }

  it should "yield [0,2] for root + right child of the fork" in {
    Linearizer.linearize(Set(0, 2), forkPog) shouldBe List(0, 2)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — Deeper tree (0→{1,2}; 2→3; 3→{4,5})  [L1, L3]
  // Preorder: [0,1,2,3,4,5]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "yield [0,1,2,3,4,5] for the full deep tree" in {
    Linearizer.linearize((0 to 5).toSet, deepPog) shouldBe List(0, 1, 2, 3, 4, 5)
  }

  it should "yield [2,3,4,5] for the right subtree (no root or left branch)" in {
    Linearizer.linearize(Set(2, 3, 4, 5), deepPog) shouldBe List(2, 3, 4, 5)
  }

  it should "yield [0,3] when skipping intermediate levels 1 and 2" in {
    Linearizer.linearize(Set(0, 3), deepPog) shouldBe List(0, 3)
  }

  it should "[L3] yield [1,4] for nodes on different branches (left branch before right subtree)" in {
    Linearizer.linearize(Set(1, 4), deepPog) shouldBe List(1, 4)
  }

  it should "yield [0,4] for root and a deep right-branch descendant" in {
    Linearizer.linearize(Set(0, 4), deepPog) shouldBe List(0, 4)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — Three-child fork (0→{1,2,3})  [L3]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "yield [0,1,2,3] for the full three-child fork" in {
    Linearizer.linearize(Set(0, 1, 2, 3), triPog) shouldBe List(0, 1, 2, 3)
  }

  it should "[L3] yield [1,3] when the middle sibling (2) is absent" in {
    Linearizer.linearize(Set(1, 3), triPog) shouldBe List(1, 3)
  }

  it should "yield [0,1] for root + first child of the three-child fork" in {
    Linearizer.linearize(Set(0, 1), triPog) shouldBe List(0, 1)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — Prop_14 golden fixture
  // Tree: 0→{1,2};  2→3;  3→{4,6};  4→5.  Preorder: [0,1,2,3,4,5,6]
  // ═══════════════════════════════════════════════════════════════════════════

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up).take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  private lazy val prop14: ProofOrderingGraph =
    PogParser.parseFile(fixture).pogs.head
      .ensuring(_.declName == "prop_14", "fixture drift: prop_14 expected first")

  it should "yield [4,5] for the cons sub-chain in prop_14" in {
    Linearizer.linearize(Set(4, 5), prop14) shouldBe List(4, 5)
  }

  it should "yield [0,2,3] when skipping the nil-branch leaf (node 1) in prop_14" in {
    Linearizer.linearize(Set(0, 2, 3), prop14) shouldBe List(0, 2, 3)
  }

  it should "yield [0,1] for root + nil-branch leaf in prop_14" in {
    Linearizer.linearize(Set(0, 1), prop14) shouldBe List(0, 1)
  }

  it should "yield [2,3,4,5,6] for the cons subtree (no root or nil branch)" in {
    Linearizer.linearize(Set(2, 3, 4, 5, 6), prop14) shouldBe List(2, 3, 4, 5, 6)
  }

  it should "yield [0,4] for root and a deep cons-branch descendant in prop_14" in {
    Linearizer.linearize(Set(0, 4), prop14) shouldBe List(0, 4)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Invariant properties
  // Checked programmatically across representative subsets of each hand-built
  // fixture. The full-set ordering serves as the reference subsequence; its
  // correctness is pinned by Groups 1–5.
  // ═══════════════════════════════════════════════════════════════════════════

  private val allFixtures = List(chainPog, forkPog, deepPog, triPog)

  private def subsets(p: ProofOrderingGraph): List[Set[Int]] =
    val ids = p.nodes.map(_.node.id)
    List(
      Set.empty[Int],
      Set(ids.head),
      ids.toSet,
      ids.take(ids.size / 2).toSet,
      ids.drop(1).toSet
    ).distinct

  it should "always return a result whose size equals the input set size" in {
    for p <- allFixtures; ids <- subsets(p) do
      withClue(s"ids=$ids: ") {
        Linearizer.linearize(ids, p).size shouldBe ids.size
      }
  }

  it should "always return a result containing exactly the input elements" in {
    for p <- allFixtures; ids <- subsets(p) do
      withClue(s"ids=$ids: ") {
        Linearizer.linearize(ids, p).toSet shouldBe ids
      }
  }

  it should "always return a subsequence of the full DFS preorder" in {
    for p <- allFixtures do
      val fullOrder = Linearizer.linearize(p.nodes.map(_.node.id).toSet, p)
      for ids <- subsets(p) do
        val result = Linearizer.linearize(ids, p)
        withClue(s"ids=$ids result=$result fullOrder=$fullOrder: ") {
          isSubsequenceOf(result, fullOrder) shouldBe true
        }
  }

  it should "be deterministic for the same inputs" in {
    val ids = (0 to 5).toSet
    Linearizer.linearize(ids, deepPog) shouldBe Linearizer.linearize(ids, deepPog)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Defensive / fail-fast  [L4]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[L4] throw when an ID in the set is absent from the POG" in {
    an [Exception] should be thrownBy Linearizer.linearize(Set(99), chainPog)
  }
