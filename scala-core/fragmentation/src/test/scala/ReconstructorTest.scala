import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for [[Reconstructor]] (Phase B, paper §2.3.1) — obligation replay.
 *
 *  [R1] V_pre is replayed in DFS-preorder from the proof root obligation; the
 *       result is (Γ_F, g_F), the input to the fragment root. Dropping a V_post
 *       ancestor means its effects never run, so (Γ_F, g_F) may differ from the
 *       recorded input of the fragment root.
 *  [R2] V_H is replayed from (Γ_F, g_F) in DFS-preorder. Each V_H node's
 *       output obligation on branch i is Effects.apply(derive(n, i), nodeInput).
 *  [R3] A branch of a V_H node is a hole iff no V_H node appears in the subtree
 *       rooted at that branch's original-tree child. The hole's obligation is the
 *       same output obligation that a V_H child would have received.
 *  [R4] When a V_H node's direct tree-child is V_post but a deeper descendant is
 *       in V_H, the descendant is re-parented (no hole); its input obligation
 *       comes from the nearest V_H ancestor's output at the connecting branch.
 *  [R5] Hole obligations equal recorded residuals when V_H is a contiguous
 *       subtree with V_pre = the full ancestor chain (no reordering).
 */
class ReconstructorTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private def hyp(name: String, typ: String): Hypothesis = Hypothesis(name, typ)
  private def obl(hyps: List[Hypothesis], goal: String): Obligation = Obligation(hyps, goal)
  private val noSum   = TacticSummary(Nil, Nil)
  private val dummyFp = Footprint(Set.empty, Set.empty, false, Nil)

  private def tn(id: Int, parent: Option[Int], children: List[Int],
                 in: Obligation, outs: List[Obligation]): TacticNode =
    TacticNode(id, "tac", in, outs, noSum, parent, children)

  private def pog(rootId: Int, nodes: List[TacticNode], edges: List[PogEdge]): ProofOrderingGraph =
    val bps = BranchPath.compute(nodes)
    ProofOrderingGraph("d", "theorem d : g", rootId,
      nodes.find(_.id == rootId).get.inputObligation,
      nodes.map(n => PogNode(n, dummyFp, bps(n.id))), edges)

  private def e(from: Int, to: Int): PogEdge = PogEdge(from, to, UseEdge)

  private def decomp(vH: Set[Int], p: ProofOrderingGraph): Decomposition =
    Decomposer.decompose(vH, p)


  // ── fixtures ─────────────────────────────────────────────────────────────────

  //  introChain: 0 → 1 → 2    edges: (0,1), (1,2), (0,2)
  //  node 0: [] ⊢ ∀x:Nat,P x  →  [h:Nat] ⊢ P h        (intro h, m=1)
  //  node 1: [h:Nat] ⊢ P h    →  [h:Nat] ⊢ Q           (rewrite, m=1)
  //  node 2: [h:Nat] ⊢ Q      →  leaf                   (m=0)
  private val ic0in  = obl(Nil, "∀x:Nat, P x")
  private val ic0out = obl(List(hyp("h", "Nat")), "P h")
  private val ic1out = obl(List(hyp("h", "Nat")), "Q")

  private val introChain = pog(0, List(
    tn(0, None,    List(1), ic0in,  List(ic0out)),
    tn(1, Some(0), List(2), ic0out, List(ic1out)),
    tn(2, Some(1), Nil,     ic1out, Nil)
  ), List(e(0, 1), e(1, 2), e(0, 2)))


  //  postIncidental: 0 → 1 → 2    edges: (1,2) only
  //  node 0: [h:Nat] ⊢ P h          →  [h:Nat, k:Bool] ⊢ P h   (have k — incidental, m=1)
  //  node 1: [h:Nat, k:Bool] ⊢ P h  →  [h:Nat, k:Bool] ⊢ Q     (rewrite goal, m=1)
  //  node 2: [h:Nat, k:Bool] ⊢ Q    →  leaf                      (m=0)
  //
  //  No POG edge from node 0 → node 1 or 2: neither 1 nor 2 depends on k.
  //  V_H={1,2}: node 0 is V_post; its introduction of k is never replayed.
  private val pi0in  = obl(List(hyp("h", "Nat")), "P h")
  private val pi0out = obl(List(hyp("h", "Nat"), hyp("k", "Bool")), "P h")
  private val pi1out = obl(List(hyp("h", "Nat"), hyp("k", "Bool")), "Q")

  private val postIncidental = pog(0, List(
    tn(0, None,    List(1), pi0in,  List(pi0out)),
    tn(1, Some(0), List(2), pi0out, List(pi1out)),
    tn(2, Some(1), Nil,     pi1out, Nil)
  ), List(e(1, 2)))


  //  reorderChain: A(0) → B(1) → C(2) → D(3)    edges: (0,2), (2,3)
  //  A: [] ⊢ ∀x:Nat,P x      →  [x:Nat] ⊢ P x          (intro x, m=1)
  //  B: [x:Nat] ⊢ P x         →  [x:Nat, k:Bool] ⊢ P x  (have k — incidental, m=1)
  //  C: [x:Nat, k:Bool] ⊢ P x →  [x:Nat, k:Bool] ⊢ Q x  (rewrite goal, m=1)
  //  D: [x:Nat, k:Bool] ⊢ Q x →  leaf                    (m=0)
  //
  //  Edge (A,C): C's rewrite depends on x from A. No edge (B,C): C ignores k.
  //  V_H={A,C}: B is V_post; D is V_post (hole at C's branch 0).
  //  k is absent from all reconstructed obligations when B is in V_post.
  private val rcAin  = obl(Nil, "∀x:Nat, P x")
  private val rcAout = obl(List(hyp("x", "Nat")), "P x")
  private val rcBout = obl(List(hyp("x", "Nat"), hyp("k", "Bool")), "P x")
  private val rcCout = obl(List(hyp("x", "Nat"), hyp("k", "Bool")), "Q x")

  private val reorderChain = pog(0, List(
    tn(0, None,    List(1), rcAin,  List(rcAout)),
    tn(1, Some(0), List(2), rcAout, List(rcBout)),
    tn(2, Some(1), List(3), rcBout, List(rcCout)),
    tn(3, Some(2), Nil,     rcCout, Nil)
  ), List(e(0, 2), e(2, 3)))


  //  branchFork: 0 → {1, 2}    edges: (0,1), (0,2)
  //  node 0: [h:A∧B] ⊢ C  →  [h:A∧B,h1:A] ⊢ C (br0) / [h:A∧B,h2:B] ⊢ C (br1)  (m=2)
  //  node 1: [h:A∧B,h1:A] ⊢ C  →  leaf   (m=0)
  //  node 2: [h:A∧B,h2:B] ⊢ C  →  leaf   (m=0)
  private val bfIn   = obl(List(hyp("h", "A∧B")), "C")
  private val bfOut0 = obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "C")
  private val bfOut1 = obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "C")

  private val branchFork = pog(0, List(
    tn(0, None,    List(1, 2), bfIn,   List(bfOut0, bfOut1)),
    tn(1, Some(0), Nil,        bfOut0, Nil),
    tn(2, Some(0), Nil,        bfOut1, Nil)
  ), List(e(0, 1), e(0, 2)))


  // ── prop_14 golden fixture (real phase-2 output) ─────────────────────────────

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


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Singleton V_H at proof root, no V_pre
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (singleton V_H)" should
    "[1a] annotate a leaf at proof root with its input obligation and no holes or outputs" in {
    val leafPog = pog(0, List(tn(0, None, Nil, ic0in, Nil)), Nil)
    val r       = Reconstructor.reconstruct(decomp(Set(0), leafPog), leafPog)
    r.rootObligation                        shouldBe ic0in
    r.nodeAnnotations.keySet                shouldBe Set(0)
    r.nodeAnnotations(0).inputObligation    shouldBe ic0in
    r.nodeAnnotations(0).outputObligations  shouldBe Nil
    r.holes                                 shouldBe Nil
  }

  it should "[1b] produce one hole when a non-leaf root's only child is not in V_H" in {
    val r = Reconstructor.reconstruct(decomp(Set(0), introChain), introChain)
    r.rootObligation                             shouldBe ic0in
    r.nodeAnnotations(0).outputObligations       shouldBe List(ic0out)
    r.holes.size                                 shouldBe 1
    r.holes.head.parentNodeId                    shouldBe 0
    r.holes.head.branchIndex                     shouldBe 0
    r.holes.head.obligation                      shouldBe ic0out
  }

  // V_H={0} on branchFork produces a branch-with-hole shape, which the enumeration
  // heuristic would reject — but the Reconstructor is heuristic-agnostic and must
  // still compute both holes correctly.
  it should "[1c] produce two per-branch holes when a branching root's children are both outside V_H" in {
    val r        = Reconstructor.reconstruct(decomp(Set(0), branchFork), branchFork)
    val byBranch = r.holes.map(h => h.branchIndex -> h.obligation).toMap
    r.rootObligation                             shouldBe bfIn
    r.nodeAnnotations(0).outputObligations       shouldBe List(bfOut0, bfOut1)
    r.holes.size                                 shouldBe 2
    r.holes.map(_.parentNodeId).toSet            shouldBe Set(0)
    byBranch(0)                                  shouldBe bfOut0
    byBranch(1)                                  shouldBe bfOut1
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — V_pre replay: (Γ_F, g_F) correctness  [R1]
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (V_pre replay)" should
    "[2a] compute (Γ_F,g_F) by replaying a single V_pre node from the proof root" in {
    // V_pre={0}: apply intro-h effect to [] ⊢ ∀x:Nat,P x → [h:Nat] ⊢ P h
    val r = Reconstructor.reconstruct(decomp(Set(1), introChain), introChain)
    r.rootObligation shouldBe ic0out  // [h:Nat] ⊢ P h — equals node 1's recorded input
  }

  it should "[2b] compose two V_pre effects in order for a two-node pre-set" in {
    // V_pre={0,1}: replay 0 then 1 from proof root → [h:Nat] ⊢ Q
    val r = Reconstructor.reconstruct(decomp(Set(2), introChain), introChain)
    r.rootObligation shouldBe ic1out  // [h:Nat] ⊢ Q — equals node 2's recorded input
  }

  it should "[2c] pick the correct branch index when a branching V_pre node has multiple children" in {
    // V_H={2}, V_pre={0}: node 0 branches (m=2); the fragment lives under child 2 (branch 1)
    val r = Reconstructor.reconstruct(decomp(Set(2), branchFork), branchFork)
    r.rootObligation shouldBe bfOut1  // branch-1 output of node 0 = node 2's recorded input
  }

  it should "[2d] produce (Γ_F,g_F) without a V_post ancestor's effects, differing from recorded input" in {
    // postIncidental: V_H={1,2}, V_pre={}, V_post={0}.
    // Node 0 introduces k but is V_post: k must be absent from (Γ_F,g_F).
    val r = Reconstructor.reconstruct(decomp(Set(1, 2), postIncidental), postIncidental)
    r.rootObligation          shouldBe pi0in   // [h:Nat] ⊢ P h — no k
    r.rootObligation          should not equal pi0out  // ≠ recorded input of node 1 ([h:Nat,k:Bool] ⊢ P h)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Hole obligations  [R3, R5]
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (hole obligations)" should
    "[3a] equal the node's recorded output when no reordering occurred  [R5]" in {
    // V_H={0}, V_pre={}: hole obligation = node 0's recorded outputObligations(0)
    val r = Reconstructor.reconstruct(decomp(Set(0), introChain), introChain)
    r.holes.head.obligation shouldBe ic0out  // matches recorded output of node 0
  }

  it should "[3b] thread the obligation through V_pre before computing the hole" in {
    // V_H={1}, V_pre={0}: node 1's input is ic0out; its branch-0 output is ic1out → hole = ic1out
    val r = Reconstructor.reconstruct(decomp(Set(1), introChain), introChain)
    r.holes.size            shouldBe 1
    r.holes.head.obligation shouldBe ic1out  // [h:Nat] ⊢ Q
  }

  // Heuristic-bypassed shape — both holes are computed and indexed by branch.
  it should "[3c] produce per-branch holes with correct obligations for a branching V_H node" in {
    val r        = Reconstructor.reconstruct(decomp(Set(0), branchFork), branchFork)
    val byBranch = r.holes.map(h => h.branchIndex -> h.obligation).toMap
    byBranch(0) shouldBe bfOut0
    byBranch(1) shouldBe bfOut1
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — No holes when all branches are filled by V_H  [R2]
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (fully closed V_H)" should
    "[4a] produce no holes for a fully closed linear V_H, with per-node obligations correct" in {
    val r = Reconstructor.reconstruct(decomp(Set(0, 1, 2), introChain), introChain)
    r.holes                              shouldBe Nil
    r.nodeAnnotations(0).inputObligation shouldBe ic0in
    r.nodeAnnotations(1).inputObligation shouldBe ic0out
    r.nodeAnnotations(2).inputObligation shouldBe ic1out
  }

  it should "[4b] produce no holes for a fully closed branching V_H, with both branch obligations correct" in {
    val r = Reconstructor.reconstruct(decomp(Set(0, 1, 2), branchFork), branchFork)
    r.holes                              shouldBe Nil
    r.nodeAnnotations(1).inputObligation shouldBe bfOut0
    r.nodeAnnotations(2).inputObligation shouldBe bfOut1
  }

  // Heuristic-bypassed shape: V_H={0,1} is branch-with-hole (the heuristic rejects it),
  // but the Reconstructor produces exactly one hole on branch 1.
  it should "[4c] produce exactly one hole when one branch of a forking V_H node is unfilled" in {
    val r = Reconstructor.reconstruct(decomp(Set(0, 1), branchFork), branchFork)
    r.holes.size             shouldBe 1
    r.holes.head.branchIndex shouldBe 1
    r.holes.head.obligation  shouldBe bfOut1
    r.nodeAnnotations(1).inputObligation shouldBe bfOut0  // branch 0 filled correctly
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — Reordered fragment: B is V_post, effects compose without k  [R4]
  // ═══════════════════════════════════════════════════════════════════════════
  //
  //  reorderChain: A(0) → B(1) → C(2) → D(3)    edges (A,C),(C,D)
  //  B introduces k (incidental); C's rewrite effect only touches the goal string,
  //  so derive(C,0) composed with C's k-free reconstructed input still resolves.
  //
  //  V_H={A,C}: B is V_post → k absent. Contrast: V_H={A,B,C} → k propagates through.

  "Reconstructor (reordered fragment)" should
    "[5a] re-parent C under A when B is V_post, with k absent from all reconstructed obligations" in {
    // V_H={A(0),C(2)}, V_pre={}, V_post={B(1),D(3)}
    val r      = Reconstructor.reconstruct(decomp(Set(0, 2), reorderChain), reorderChain)
    val noKOut = obl(List(hyp("x", "Nat")), "Q x")  // C's reconstructed output: no k

    r.rootObligation                                shouldBe rcAin
    r.nodeAnnotations(0).outputObligations(0)       shouldBe rcAout  // [x:Nat] ⊢ P x
    // C re-parented: input fed from A's output, not B's (no k)
    r.nodeAnnotations(2).inputObligation            shouldBe rcAout
    r.nodeAnnotations(2).inputObligation            should not equal rcBout  // ≠ C's recorded input
    r.nodeAnnotations(2).inputObligation.hypotheses.map(_.name) should not contain "k"
    // C's output = apply(derive(C,0), [x:Nat] ⊢ P x) = [x:Nat] ⊢ Q x  (no k)
    r.nodeAnnotations(2).outputObligations(0)       shouldBe noKOut
    // D not in V_H → hole at C's branch 0; obligation also has no k
    r.holes.size              shouldBe 1
    r.holes.head.parentNodeId shouldBe 2
    r.holes.head.branchIndex  shouldBe 0
    r.holes.head.obligation   shouldBe noKOut
  }

  it should "[5b] propagate k through all obligations when B is included in V_H" in {
    // V_H={A(0),B(1),C(2)}, V_post={D(3)}: k introduced by B is present throughout
    val r = Reconstructor.reconstruct(decomp(Set(0, 1, 2), reorderChain), reorderChain)
    r.nodeAnnotations(1).inputObligation       shouldBe rcAout  // B's input: [x:Nat] ⊢ P x
    r.nodeAnnotations(1).outputObligations(0)  shouldBe rcBout  // B's output: [x:Nat,k:Bool] ⊢ P x
    r.nodeAnnotations(2).inputObligation       shouldBe rcBout  // k present
    r.nodeAnnotations(2).outputObligations(0)  shouldBe rcCout  // [x:Nat,k:Bool] ⊢ Q x
    // D not in V_H → hole at C's branch 0; obligation has k — contrast with [5a]
    r.holes.size            shouldBe 1
    r.holes.head.obligation shouldBe rcCout
  }

  it should "[5c] exclude k from rootObligation when B is V_post (V_H={C} with V_pre={A})" in {
    // V_H={C(2)}, V_pre={A(0)}, V_post={B(1),D(3)}
    // Replay A from proof root → [x:Nat] ⊢ P x. B is V_post: k never introduced.
    val r      = Reconstructor.reconstruct(decomp(Set(2), reorderChain), reorderChain)
    val noKOut = obl(List(hyp("x", "Nat")), "Q x")

    r.rootObligation shouldBe rcAout    // [x:Nat] ⊢ P x — no k (B skipped)
    r.rootObligation should not equal rcBout  // ≠ C's recorded input (which has k)
    r.nodeAnnotations(2).inputObligation.hypotheses.map(_.name) should not contain "k"
    // D not in V_H → hole at C's branch 0; derived without k
    r.holes.size            shouldBe 1
    r.holes.head.obligation shouldBe noKOut  // [x:Nat] ⊢ Q x
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — Golden prop_14 fixture  [R2, R5]
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (prop_14 golden)" should
    "[6a] reproduce the recorded input of node 4 as rootObligation for V_H={4,5}  [R5]" in {
    // V_pre={0,2,3} = full ancestor chain; no reordering → recorded obligations match
    val r = Reconstructor.reconstruct(decomp(Set(4, 5), prop14), prop14)
    r.rootObligation                     shouldBe p14node(4).inputObligation
    r.nodeAnnotations(5).inputObligation shouldBe p14node(5).inputObligation
    r.holes                              shouldBe Nil  // {4,5} fully closed: node 5 is a leaf
  }

  it should "[6b] produce a hole at branch 1 of node 0 for V_H={0,1}" in {
    // Admissible but heuristic-bypassed (branch-with-hole). V_pre={}.
    // Branch 0 of node 0 → child 1 ∈ V_H (filled).
    // Branch 1 of node 0 → child 2 ∉ V_H → hole; obligation = node 0's recorded output[1]
    //                                          = node 2's recorded input  [R5]
    val r = Reconstructor.reconstruct(decomp(Set(0, 1), prop14), prop14)
    r.rootObligation                     shouldBe prop14.rootObligation
    r.nodeAnnotations(1).inputObligation shouldBe p14node(1).inputObligation
    r.holes.size                         shouldBe 1
    r.holes.head.parentNodeId            shouldBe 0
    r.holes.head.branchIndex             shouldBe 1
    r.holes.head.obligation              shouldBe p14node(2).inputObligation
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Structural invariants (programmatic over all hand-built fixtures)
  // ═══════════════════════════════════════════════════════════════════════════

  private val allFixtures = List(introChain, postIncidental, reorderChain, branchFork)

  /** All admissible decompositions of a POG via brute-force powerset. */
  private def admissibleDecomps(p: ProofOrderingGraph): List[Decomposition] =
    val ids = p.nodes.map(_.node.id).toIndexedSeq
    (1 until (1 << ids.size))
      .map(bits => ids.indices.collect { case i if (bits & (1 << i)) != 0 => ids(i) }.toSet)
      .filter(vH => Decomposer.isAdmissible(vH, p))
      .map(vH => Decomposer.decompose(vH, p))
      .toList

  "Reconstructor (structural invariants)" should
    "[7a] include exactly the V_H nodes in nodeAnnotations" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        Reconstructor.reconstruct(d, p).nodeAnnotations.keySet shouldBe d.vH
      }
  }

  it should "[7b] not include any V_pre or V_post node in nodeAnnotations" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      withClue(s"vH=${d.vH}: ") {
        val r = Reconstructor.reconstruct(d, p)
        r.nodeAnnotations.keySet.intersect(d.vPre ++ d.vPost) shouldBe empty
      }
  }

  it should "[7c] reference only V_H nodes as hole parents, with branch indices in range" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      val mById = p.nodes.iterator.map(n => n.node.id -> n.node.outputObligations.size).toMap
      val r     = Reconstructor.reconstruct(d, p)
      for h <- r.holes do withClue(s"vH=${d.vH} hole=$h: ") {
        d.vH should contain(h.parentNodeId)
        h.branchIndex should (be >= 0 and be < mById(h.parentNodeId))
      }
  }

  it should "[7d] set each non-root V_H node's input = its fragment-tree parent's output at the connecting branch" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      val r    = Reconstructor.reconstruct(d, p)
      val byId = p.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap

      def descendants(x: Int): Set[Int] =
        val cs = byId(x).childIds
        cs.toSet ++ cs.flatMap(descendants)

      def nearestVHAncestor(id: Int): Option[(Int, Int)] =
        var cur = byId(id).parentId
        while cur.isDefined && !d.vH.contains(cur.get) do cur = byId(cur.get).parentId
        cur.map { parentId =>
          val branchIdx = byId(parentId).childIds.indexWhere { childId =>
            childId == id || descendants(childId).contains(id)
          }
          (parentId, branchIdx)
        }

      for nodeId <- d.vH do
        nearestVHAncestor(nodeId).foreach { (parentId, branchIdx) =>
          withClue(s"vH=${d.vH} node=$nodeId parent=$parentId branch=$branchIdx: ") {
            r.nodeAnnotations(nodeId).inputObligation shouldBe
              r.nodeAnnotations(parentId).outputObligations(branchIdx)
          }
        }
  }

  it should "[7e] have each branch of each V_H node be either a hole or a V_H-subtree entry, never both" in {
    for p <- allFixtures; d <- admissibleDecomps(p) do
      val r         = Reconstructor.reconstruct(d, p)
      val byId      = p.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap
      val holeSlots = r.holes.map(h => (h.parentNodeId, h.branchIndex)).toSet

      def subtreeHasVH(x: Int): Boolean =
        d.vH.contains(x) || byId(x).childIds.exists(subtreeHasVH)

      for nodeId <- d.vH do
        val node = byId(nodeId)
        for branchIdx <- node.outputObligations.indices do
          val childId      = node.childIds(branchIdx)
          val filledByVH   = subtreeHasVH(childId)
          val isHole       = holeSlots.contains((nodeId, branchIdx))
          withClue(s"vH=${d.vH} node=$nodeId branch=$branchIdx: ") {
            (filledByVH || isHole)  shouldBe true   // every branch accounted for
            (filledByVH && isHole)  shouldBe false  // no branch is both
          }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Defensive / fail-fast
  // ═══════════════════════════════════════════════════════════════════════════

  "Reconstructor (defensive)" should
    "[8a] throw when a V_H node id is absent from the POG" in {
    val bad = Decomposition(Set(99), Set.empty, Set.empty)
    an [Exception] should be thrownBy Reconstructor.reconstruct(bad, introChain)
  }

  it should "[8b] throw when V_H is empty" in {
    val bad = Decomposition(Set.empty, Set.empty, Set.empty)
    an [Exception] should be thrownBy Reconstructor.reconstruct(bad, introChain)
  }
