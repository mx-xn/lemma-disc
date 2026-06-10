import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for [[FragmentBuilder]] (step 8) — assembles a [[Fragment]] from a
 *  [[Decomposition]] and the [[ProofOrderingGraph]] it came from.
 *
 *  `FragmentBuilder.build` calls [[Reconstructor]] internally; tests exercise the
 *  combined Reconstruct + Build pipeline and compare output obligations against an
 *  independently-called [[Reconstructor]] for programmatic groups.
 *
 *  Correctness properties (numbered labels used in group headers):
 *
 *  [FB1] V_H node with mₙ = 0 → LeafNode; mₙ ≥ 1 → CompositeNode.
 *  [FB2] An unfilled slot (no V_H node in that branch's subtree) → HoleNode.
 *  [FB3] childIds of a CompositeNode are CO-INDEXED with outputObligations: the child
 *        at slot i (V_H node id or hole id) is childIds(i).
 *  [FB4] Re-parenting: a V_H node's fragment-tree parent is its nearest V_H ancestor in
 *        the original proof tree, NOT necessarily its direct tree parent.
 *  [FB5] Each node's obligation = recon.nodeAnnotations(id).inputObligation; each
 *        CompositeNode's outputObligations = recon.nodeAnnotations(id).outputObligations;
 *        each HoleNode's obligation = the matching HoleAnnotation from recon.
 *  [FB6] frag.rootObligation = rootNode.obligation = recon.rootObligation.
 *  [FB7] Hole integer ids are unique within the fragment and do not alias any V_H id;
 *        holeId strings are non-empty and unique within the fragment.
 */
class FragmentBuilderTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private def hyp(name: String, typ: String): Hypothesis = Hypothesis(name, typ)
  private def obl(hyps: List[Hypothesis], goal: String): Obligation = Obligation(hyps, goal)
  private val noSum   = TacticSummary(Nil, Nil)
  private val dummyFp = Footprint(Set.empty, Set.empty, false, Nil)

  private def tn(id: Int, parent: Option[Int], children: List[Int],
                 in: Obligation, outs: List[Obligation],
                 text: String = "tac"): TacticNode =
    TacticNode(id, text, in, outs, noSum, parent, children)

  private def mkPog(rootId: Int, nodes: List[TacticNode],
                    edges: List[PogEdge], name: String = "d"): ProofOrderingGraph =
    val bps = BranchPath.compute(nodes)
    ProofOrderingGraph(name, s"theorem $name : g", rootId,
      nodes.find(_.id == rootId).get.inputObligation,
      nodes.map(n => PogNode(n, dummyFp, bps(n.id))), edges)

  private def e(from: Int, to: Int): PogEdge = PogEdge(from, to, UseEdge)

  private def build(vH: Set[Int], p: ProofOrderingGraph,
                    source: String = "file.lean", fragId: Int = 0): Fragment =
    FragmentBuilder.build(Decomposer.decompose(vH, p), p, source, fragId)

  // Node lookup by id — fails fast if absent.
  private def nodeById(frag: Fragment, id: Int): TreeNode =
    frag.nodes.find(_.id == id).getOrElse(fail(s"node $id absent from fragment"))

  private def holes(frag: Fragment):      List[HoleNode]      = frag.nodes.collect { case h: HoleNode      => h }
  private def composites(frag: Fragment): List[CompositeNode] = frag.nodes.collect { case c: CompositeNode => c }
  private def leaves(frag: Fragment):     List[LeafNode]      = frag.nodes.collect { case l: LeafNode      => l }


  // ── fixtures ─────────────────────────────────────────────────────────────────

  //  introChain: 0 → 1 → 2    edges: (0,1),(1,2),(0,2)
  private val ic0in  = obl(Nil, "∀x:Nat, P x")
  private val ic0out = obl(List(hyp("h", "Nat")), "P h")
  private val ic1out = obl(List(hyp("h", "Nat")), "Q")

  private val introChain = mkPog(0, List(
    tn(0, None,    List(1), ic0in,  List(ic0out), "intro h"),
    tn(1, Some(0), List(2), ic0out, List(ic1out), "rw"),
    tn(2, Some(1), Nil,     ic1out, Nil,          "exact")
  ), List(e(0,1), e(1,2), e(0,2)))

  //  reorderChain: A(0)→B(1)→C(2)→D(3)   edges (A,C),(C,D)
  //  B introduces k (incidental); C's rewrite depends on x from A; D is a leaf.
  private val rcAin  = obl(Nil, "∀x:Nat, P x")
  private val rcAout = obl(List(hyp("x", "Nat")), "P x")
  private val rcBout = obl(List(hyp("x", "Nat"), hyp("k", "Bool")), "P x")
  private val rcCout = obl(List(hyp("x", "Nat"), hyp("k", "Bool")), "Q x")

  private val reorderChain = mkPog(0, List(
    tn(0, None,    List(1), rcAin,  List(rcAout), "intro x"),
    tn(1, Some(0), List(2), rcAout, List(rcBout), "have k"),
    tn(2, Some(1), List(3), rcBout, List(rcCout), "rw"),
    tn(3, Some(2), Nil,     rcCout, Nil,          "exact")
  ), List(e(0,2), e(2,3)))

  //  branchFork: 0 → {1, 2}   edges: (0,1),(0,2)
  private val bfIn   = obl(List(hyp("h", "A∧B")), "C")
  private val bfOut0 = obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "C")
  private val bfOut1 = obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "C")

  private val branchFork = mkPog(0, List(
    tn(0, None,    List(1,2), bfIn,   List(bfOut0, bfOut1), "cases h"),
    tn(1, Some(0), Nil,       bfOut0, Nil,                  "exact h1"),
    tn(2, Some(0), Nil,       bfOut1, Nil,                  "exact h2")
  ), List(e(0,1), e(0,2)))

  //  leafPog: single leaf (mₙ=0)
  private val leafPog = mkPog(0, List(tn(0, None, Nil, ic0in, Nil, "exact")), Nil)


  // ── prop_14 golden fixture ───────────────────────────────────────────────────

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up).take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException("Examples.json not found"))

  private lazy val prop14: ProofOrderingGraph =
    PogParser.parseFile(fixture).pogs.head
      .ensuring(_.declName == "prop_14", "fixture drift: prop_14 expected first")

  private def p14node(id: Int): TacticNode =
    prop14.nodes.find(_.node.id == id).get.node


  // ── programmatic helpers ─────────────────────────────────────────────────────

  private val allFixtures = List(introChain, reorderChain, branchFork)

  private def admissibleDecomps(p: ProofOrderingGraph): List[Decomposition] =
    val ids = p.nodes.map(_.node.id).toIndexedSeq
    (1 until (1 << ids.size))
      .map(bits => ids.indices.collect { case i if (bits & (1 << i)) != 0 => ids(i) }.toSet)
      .filter(vH => Decomposer.isAdmissible(vH, p))
      .map(vH => Decomposer.decompose(vH, p))
      .toList

  private def candidateFor(d: Decomposition, p: ProofOrderingGraph): Candidate =
    val mById = p.nodes.iterator.map(pn => pn.node.id -> pn.node.outputObligations.size).toMap
    Candidate(Decomposer.fragmentRoot(d.vH, p).get, d.vH.iterator.map(id => id -> mById(id)).toMap)


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Singleton V_H: leaf node (mₙ = 0)  [FB1]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (singleton leaf)" should
    "[1a] produce exactly one LeafNode, no holes, correct obligation and metadata" in {
    val frag = build(Set(0), leafPog, source = "Foo.lean", fragId = 3)
    frag.nodes.size          shouldBe 1
    holes(frag)              shouldBe Nil
    frag.rootNodeId          shouldBe 0
    frag.rootObligation      shouldBe ic0in
    frag.fragmentId          shouldBe 3
    frag.sourceFile          shouldBe "Foo.lean"

    val leaf = frag.nodes.head
    leaf                     shouldBe a [LeafNode]
    leaf.id                  shouldBe 0
    leaf.parentId            shouldBe None
    leaf.childIds            shouldBe Nil
    leaf.obligation          shouldBe ic0in
    leaf.asInstanceOf[LeafNode].tacticText shouldBe "exact"
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — Singleton V_H: composite node with holes  [FB1, FB2, FB3]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (singleton composite)" should
    "[2a] produce one CompositeNode + one HoleNode when the only child is outside V_H" in {
    val frag = build(Set(0), introChain)
    val comp = composites(frag).headOption.getOrElse(fail("expected one composite"))
    val hole = holes(frag).headOption.getOrElse(fail("expected one hole"))

    frag.nodes.size               shouldBe 2
    comp.id                       shouldBe 0
    comp.parentId                 shouldBe None
    comp.childIds                 shouldBe List(hole.id)   // [FB3]: slot 0 = hole id
    comp.outputObligations        shouldBe List(ic0out)
    comp.obligation               shouldBe ic0in
    hole.parentId                 shouldBe Some(0)
    hole.obligation               shouldBe ic0out
    hole.childIds                 shouldBe Nil
    hole.holeId.nonEmpty          shouldBe true
  }

  it should "[2b] produce one CompositeNode + two HoleNodes for a 2-branch node with both children outside V_H" in {
    // V_H={0} on branchFork: branch-with-hole shape; FragmentBuilder is heuristic-agnostic.
    val frag = build(Set(0), branchFork)
    val comp = composites(frag).headOption.getOrElse(fail("expected one composite"))

    frag.nodes.size               shouldBe 3
    holes(frag).size              shouldBe 2
    comp.outputObligations        shouldBe List(bfOut0, bfOut1)
    comp.childIds.size            shouldBe 2              // [FB3]: one slot per output
    // Each slot's child is a HoleNode whose obligation equals outputObligations(i)  [FB3]
    for (childId, expectedObl) <- comp.childIds.zip(comp.outputObligations) do
      val h = nodeById(frag, childId)
      h                           shouldBe a [HoleNode]
      h.obligation                shouldBe expectedObl
      h.parentId                  shouldBe Some(0)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Linear chain, fully closed  [FB1, FB3]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (fully closed linear chain)" should
    "[3a] produce CompositeNode → CompositeNode → LeafNode with no holes and correct wiring" in {
    val frag = build(Set(0, 1, 2), introChain)

    frag.nodes.size                                         shouldBe 3
    holes(frag)                                             shouldBe Nil
    frag.rootNodeId                                         shouldBe 0
    frag.rootObligation                                     shouldBe ic0in

    val n0 = nodeById(frag, 0).asInstanceOf[CompositeNode]
    n0.parentId                                             shouldBe None
    n0.childIds                                             shouldBe List(1)
    n0.outputObligations                                    shouldBe List(ic0out)

    val n1 = nodeById(frag, 1).asInstanceOf[CompositeNode]
    n1.parentId                                             shouldBe Some(0)
    n1.childIds                                             shouldBe List(2)
    n1.outputObligations                                    shouldBe List(ic1out)

    val n2 = nodeById(frag, 2)
    n2                                                      shouldBe a [LeafNode]
    n2.parentId                                             shouldBe Some(1)
    n2.childIds                                             shouldBe Nil
    n2.obligation                                           shouldBe ic1out
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — Non-root fragment: V_pre is replayed, rootObligation ≠ pog root  [FB6]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (non-root fragment)" should
    "[4a] set rootNodeId=1 and rootObligation=ic0out for V_H={1,2} after replaying V_pre={0}" in {
    val frag = build(Set(1, 2), introChain)

    frag.rootNodeId             shouldBe 1
    frag.rootObligation         shouldBe ic0out    // ic0in only after replaying node 0
    holes(frag)                 shouldBe Nil
    nodeById(frag, 1).parentId  shouldBe None
    nodeById(frag, 2)           shouldBe a [LeafNode]
    nodeById(frag, 2).parentId  shouldBe Some(1)
  }

  it should "[4b] produce a single LeafNode with rootObligation=ic1out for V_H={2} (V_pre={0,1})" in {
    val frag = build(Set(2), introChain)

    frag.rootNodeId              shouldBe 2
    frag.rootObligation          shouldBe ic1out
    frag.nodes.size              shouldBe 1
    frag.nodes.head              shouldBe a [LeafNode]
    frag.nodes.head.parentId     shouldBe None
    holes(frag)                  shouldBe Nil
  }

  it should "[4c] produce a CompositeNode with one hole for V_H={1} (V_pre={0})" in {
    val frag = build(Set(1), introChain)
    val hole = holes(frag).headOption.getOrElse(fail("expected one hole"))

    frag.rootNodeId              shouldBe 1
    frag.rootObligation          shouldBe ic0out
    frag.nodes.size              shouldBe 2
    hole.obligation              shouldBe ic1out
    hole.parentId                shouldBe Some(1)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — Re-parenting: V_H = {A,C} skipping B  [FB4]
  //
  //   reorderChain: A(0)→B(1)→C(2)→D(3), edges (A,C),(C,D)
  //   B(1) is V_post. C(2) must be wired as A's DIRECT fragment-tree child (not B's).
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (re-parented fragment)" should
    "[5a] wire C (id=2) as A's (id=0) direct child, NOT id=1 (B), and give C parentId=Some(0)" in {
    val frag  = build(Set(0, 2), reorderChain)
    val nodeA = nodeById(frag, 0).asInstanceOf[CompositeNode]
    val nodeC = nodeById(frag, 2).asInstanceOf[CompositeNode]

    frag.nodes.size               shouldBe 3       // A + C + one hole
    frag.rootNodeId               shouldBe 0
    nodeA.parentId                shouldBe None
    nodeA.childIds                shouldBe List(2) // C, NOT B  [FB4]
    nodeC.parentId                shouldBe Some(0) // re-parented under A
  }

  it should "[5b] produce obligations for A, C, and the hole that are all free of k (B is V_post)" in {
    val frag  = build(Set(0, 2), reorderChain)
    val nodeA = nodeById(frag, 0).asInstanceOf[CompositeNode]
    val nodeC = nodeById(frag, 2).asInstanceOf[CompositeNode]
    val hole  = holes(frag).headOption.getOrElse(fail("expected one hole"))

    nodeA.outputObligations.head.hypotheses.map(_.name) should not contain "k"
    nodeC.obligation.hypotheses.map(_.name)             should not contain "k"
    nodeC.outputObligations.head.hypotheses.map(_.name) should not contain "k"
    hole.obligation.hypotheses.map(_.name)              should not contain "k"
  }

  it should "[5c] set rootObligation without k and produce one hole without k for V_H={C} (V_pre={A})" in {
    val frag = build(Set(2), reorderChain)
    val hole = holes(frag).headOption.getOrElse(fail("expected one hole"))

    frag.rootNodeId                                       shouldBe 2
    frag.rootObligation.hypotheses.map(_.name) should not contain "k"
    hole.obligation.hypotheses.map(_.name)     should not contain "k"
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — Branching V_H, fully closed  [FB1, FB3]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (fully closed branching)" should
    "[6a] produce a CompositeNode with two LeafNode children co-indexed with outputObligations" in {
    val frag = build(Set(0, 1, 2), branchFork)

    frag.nodes.size                               shouldBe 3
    holes(frag)                                   shouldBe Nil
    frag.rootNodeId                               shouldBe 0
    frag.rootObligation                           shouldBe bfIn

    val n0 = nodeById(frag, 0).asInstanceOf[CompositeNode]
    n0.parentId                                   shouldBe None
    n0.childIds                                   shouldBe List(1, 2)  // co-indexed  [FB3]
    n0.outputObligations                          shouldBe List(bfOut0, bfOut1)

    val n1 = nodeById(frag, 1)
    n1                                            shouldBe a [LeafNode]
    n1.parentId                                   shouldBe Some(0)
    n1.obligation                                 shouldBe bfOut0

    val n2 = nodeById(frag, 2)
    n2                                            shouldBe a [LeafNode]
    n2.parentId                                   shouldBe Some(0)
    n2.obligation                                 shouldBe bfOut1
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Slot ordering: hole at slot 0 BEFORE the V_H child at slot 1  [FB2, FB3]
  //
  //   V_H={0,2} on branchFork: slot 0 → child 1 (V_post → hole),
  //   slot 1 → child 2 (∈ V_H → filled). childIds must respect this order.
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (slot ordering)" should
    "[7a] place the hole at childIds(0) and the V_H child id at childIds(1)" in {
    val frag = build(Set(0, 2), branchFork)
    val n0   = nodeById(frag, 0).asInstanceOf[CompositeNode]

    frag.nodes.size              shouldBe 3
    holes(frag).size             shouldBe 1
    n0.childIds.size             shouldBe 2
    n0.outputObligations         shouldBe List(bfOut0, bfOut1)

    // Slot 0: child must be a HoleNode with obligation bfOut0  [FB3]
    val slot0 = nodeById(frag, n0.childIds(0))
    slot0                        shouldBe a [HoleNode]
    slot0.obligation             shouldBe bfOut0
    slot0.parentId               shouldBe Some(0)

    // Slot 1: child must be node 2 (LeafNode) with obligation bfOut1  [FB3]
    n0.childIds(1)               shouldBe 2
    val n2 = nodeById(frag, 2)
    n2                           shouldBe a [LeafNode]
    n2.parentId                  shouldBe Some(0)
    n2.obligation                shouldBe bfOut1
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Metadata  [FB6]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (metadata)" should
    "[8a] carry fragmentId unchanged" in {
    build(Set(0), introChain, fragId = 0).fragmentId shouldBe 0
    build(Set(0), introChain, fragId = 7).fragmentId shouldBe 7
  }

  it should "[8b] carry sourceFile unchanged" in {
    build(Set(0), introChain, source = "Foo.lean").sourceFile shouldBe "Foo.lean"
    build(Set(0), introChain, source = "Bar.lean").sourceFile shouldBe "Bar.lean"
  }

  it should "[8c] set declName from pog.declName" in {
    build(Set(0), introChain).declName shouldBe "d"
    build(Set(0), mkPog(0, List(tn(0, None, Nil, ic0in, Nil)), Nil, "myThm")).declName shouldBe "myThm"
  }

  it should "[8d-e] set rootNodeId to the fragment root's id and rootObligation to its obligation" in {
    for vH <- List(Set(0), Set(1), Set(0,1), Set(0,1,2)) do
      val frag = build(vH, introChain)
      val root = frag.nodes.find(_.parentId.isEmpty).getOrElse(fail(s"no root for vH=$vH"))
      withClue(s"vH=$vH: ") {
        frag.rootNodeId     shouldBe root.id        // [FB6]
        frag.rootObligation shouldBe root.obligation
      }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 9 — Structural invariants (programmatic over all admissible decomps)
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (structural invariants)" should
    "[9a] produce unique node ids within each fragment" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val ids = build(d.vH, p).nodes.map(_.id)
        ids.size shouldBe ids.distinct.size
      }
  }

  it should "[9b] have exactly one root (parentId=None) and every other node with parentId=Some(_)" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val ns = build(d.vH, p).nodes
        ns.count(_.parentId.isEmpty)   shouldBe 1
        ns.count(_.parentId.isDefined) shouldBe (ns.size - 1)
      }
  }

  it should "[9c] have mutually consistent parentId / childIds cross-references" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val frag  = build(d.vH, p)
        val byId  = frag.nodes.iterator.map(n => n.id -> n).toMap
        // Every entry in childIds refers to a node that points back at the parent.
        for n <- frag.nodes; childId <- n.childIds do
          byId(childId).parentId shouldBe Some(n.id)
        // Every non-root node's parentId appears in that parent's childIds.
        for n <- frag.nodes if n.parentId.isDefined do
          byId(n.parentId.get).childIds should contain(n.id)
      }
  }

  it should "[9d] have CompositeNode.childIds.size == outputObligations.size for every composite" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        composites(build(d.vH, p)).foreach { c =>
          c.childIds.size shouldBe c.outputObligations.size
        }
      }
  }

  it should "[9e] have HoleNodes and LeafNodes with childIds == Nil" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val frag = build(d.vH, p)
        holes(frag).foreach(_.childIds  shouldBe Nil)
        leaves(frag).foreach(_.childIds shouldBe Nil)
      }
  }

  it should "[9f-g] set rootNodeId to the unique parentless node, whose obligation == rootObligation" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val frag = build(d.vH, p)
        val root = frag.nodes.find(_.parentId.isEmpty).get
        frag.rootNodeId     shouldBe root.id
        frag.rootObligation shouldBe root.obligation   // [FB6]
      }
  }

  it should "[9h] produce exactly Decomposer.holeCount(candidate) HoleNodes" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        holes(build(d.vH, p)).size shouldBe Decomposer.holeCount(candidateFor(d, p))
      }
  }

  it should "[9i] have non-hole node ids equal to vH exactly" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val frag      = build(d.vH, p)
        val tacticIds = frag.nodes.collect {
          case c: CompositeNode => c.id
          case l: LeafNode      => l.id
        }.toSet
        tacticIds shouldBe d.vH
      }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 10 — Obligation correctness (programmatic)  [FB5]
  //
  // Call Reconstructor independently as the reference and compare.
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (obligation correctness)" should
    "[10a-b] match recon.nodeAnnotations for every V_H node's obligation and outputObligations" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      val frag  = build(d.vH, p)
      val recon = Reconstructor.reconstruct(d, p)
      for nodeId <- d.vH do
        withClue(s"vH=${d.vH} node=$nodeId: ") {
          val ann = recon.nodeAnnotations(nodeId)
          nodeById(frag, nodeId).obligation shouldBe ann.inputObligation
          nodeById(frag, nodeId) match
            case c: CompositeNode => c.outputObligations shouldBe ann.outputObligations
            case _: LeafNode      => // mₙ=0: no output obligations to compare
            case _: HoleNode      => fail("V_H node must not be a HoleNode")
        }
  }

  it should "[10c] match recon.holes for every HoleNode's obligation, identified by (parentId, slot)" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      val frag  = build(d.vH, p)
      val recon = Reconstructor.reconstruct(d, p)
      for h <- holes(frag) do
        val parentId  = h.parentId.getOrElse(fail("hole has no parent"))
        val slotIndex = nodeById(frag, parentId).childIds.indexOf(h.id)
        withClue(s"vH=${d.vH} hole parent=$parentId slot=$slotIndex: ") {
          val ann = recon.holes
            .find(a => a.parentNodeId == parentId && a.branchIndex == slotIndex)
            .getOrElse(fail(s"no HoleAnnotation for ($parentId, $slotIndex)"))
          h.obligation shouldBe ann.obligation
        }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 11 — Tactic text and summary carry-through  [FB1]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (tactic metadata carry-through)" should
    "[11a-b] copy tacticText and summary from the POG node into every CompositeNode" in {
    val frag    = build(Set(0, 1, 2), reorderChain)   // nodes 0,1,2 are all CompositeNodes here
    val pogById = reorderChain.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap
    composites(frag).foreach { c =>
      withClue(s"node ${c.id}: ") {
        c.tacticText shouldBe pogById(c.id).tacticText
        c.summary    shouldBe pogById(c.id).summary
      }
    }
  }

  it should "[11c-d] copy tacticText and summary from the POG node into every LeafNode" in {
    val frag    = build(Set(0, 1, 2), introChain)     // node 2 is a LeafNode ("exact")
    val pogById = introChain.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap
    leaves(frag).foreach { l =>
      withClue(s"node ${l.id}: ") {
        l.tacticText shouldBe pogById(l.id).tacticText
        l.summary    shouldBe pogById(l.id).summary
      }
    }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 12 — Hole IDs: uniqueness and non-conflict  [FB7]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (hole IDs)" should
    "[12a] produce non-empty holeId strings for every hole" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      holes(build(d.vH, p)).foreach { h =>
        withClue(s"vH=${d.vH} hole id=${h.id}: ") {
          h.holeId.nonEmpty shouldBe true
        }
      }
  }

  it should "[12b] produce distinct holeId strings within each fragment" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val holeIds = holes(build(d.vH, p)).map(_.holeId)
        holeIds.size shouldBe holeIds.distinct.size
      }
  }

  it should "[12c] not alias any V_H node's integer id with a hole's integer id" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        holes(build(d.vH, p)).map(_.id).toSet.intersect(d.vH) shouldBe empty
      }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 13 — Golden prop_14  [FB4, FB5, FB6]
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (prop_14 golden)" should
    "[13a] produce CompositeNode(4) → LeafNode(5) with no holes for V_H={4,5}" in {
    val frag = build(Set(4, 5), prop14, source = "Examples.lean", fragId = 42)

    frag.fragmentId              shouldBe 42
    frag.sourceFile              shouldBe "Examples.lean"
    frag.rootNodeId              shouldBe 4
    frag.rootObligation          shouldBe p14node(4).inputObligation
    frag.nodes.size              shouldBe 2
    holes(frag)                  shouldBe Nil

    val n4 = nodeById(frag, 4).asInstanceOf[CompositeNode]
    n4.parentId                  shouldBe None
    n4.childIds                  shouldBe List(5)
    n4.obligation                shouldBe p14node(4).inputObligation
    n4.outputObligations         shouldBe List(p14node(5).inputObligation)

    val n5 = nodeById(frag, 5)
    n5                           shouldBe a [LeafNode]
    n5.parentId                  shouldBe Some(4)
    n5.obligation                shouldBe p14node(5).inputObligation
  }

  it should "[13b] place node 1 at slot 0 and a hole at slot 1 for V_H={0,1} (heuristic-bypassed)" in {
    // prop_14 node 0 branches (m=2): child 1 ∈ V_H (slot 0 filled), child 2 ∉ V_H (slot 1 = hole).
    val frag = build(Set(0, 1), prop14)

    frag.rootNodeId              shouldBe 0
    frag.rootObligation          shouldBe prop14.rootObligation
    frag.nodes.size              shouldBe 3
    holes(frag).size             shouldBe 1

    val n0 = nodeById(frag, 0).asInstanceOf[CompositeNode]
    n0.parentId                  shouldBe None
    n0.childIds(0)               shouldBe 1              // slot 0 = node 1 (∈ V_H)
    n0.childIds(1)               shouldBe holes(frag).head.id  // slot 1 = hole

    val n1 = nodeById(frag, 1)
    n1                           shouldBe a [LeafNode]
    n1.parentId                  shouldBe Some(0)

    val hole = holes(frag).head
    hole.parentId                shouldBe Some(0)
    hole.obligation              shouldBe p14node(2).inputObligation  // V_pre=∅ → recorded output matches
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 14 — Defensive / fail-fast
  // ═══════════════════════════════════════════════════════════════════════════

  "FragmentBuilder (defensive)" should
    "[14a] propagate an error when a V_H node id is absent from the POG" in {
    val bad = Decomposition(Set(99), Set.empty, Set.empty)
    an [Exception] should be thrownBy FragmentBuilder.build(bad, introChain, "f.lean", 0)
  }

  it should "[14b] propagate an error for an empty V_H" in {
    val bad = Decomposition(Set.empty, Set.empty, Set.empty)
    an [Exception] should be thrownBy FragmentBuilder.build(bad, introChain, "f.lean", 0)
  }
