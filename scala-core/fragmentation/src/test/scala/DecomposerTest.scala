import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for `Decomposer` (Phase A, paper §2.3) — POG decomposition, PRE-
 *  obligation. Everything here is STRUCTURAL: tree shape, dependency edges, and
 *  per-node subgoal counts mₙ. No obligations, no tactic effects (those are
 *  Phase B / Reconstructor).
 *
 *  Like DependencyTest, the unit-level predicates take the LEAST input that
 *  determines them, so each is exercised in isolation with injected values:
 *    • isConvex(vH, edges)            — edge reachability only (kind ignored)
 *    • isBranchClosed(vH, branchPaths)— branch paths only
 *    • vPre(vH, edges)                — edge reachability only
 *  while fragmentRoot / isAdmissible / decompose / enumerate take a full POG.
 *
 *  ── Load-bearing interpretations (settled with the author; expected values
 *     below depend on each) ─────────────────────────────────────────────────
 *
 *    [C1] CONVEXITY is over directed paths in G_T (EDGES), never tree edges. The
 *         reordered {A,C} (chain A→B→C, edges (A,B),(A,C) only) IS convex — B is
 *         not on a directed edge-path A⇒C. The same nodes with edges (A,B),(B,C)
 *         are NOT convex. Graph-convex ≠ tree-contiguous. (Group 1)
 *
 *    [C2] BRANCH CLOSURE compares tree POSITIONS = branch paths with the self
 *         `*` stripped from the last segment (so ["1*"] and ["1","0"] share
 *         prefix ["1"], forcing nothing extra). But the required FORK must be the
 *         actual BRANCHING node: matched by its STORED path carrying `*`
 *         (["1*"], or ["*"] at the root). A non-branching node sharing the
 *         stripped position must NOT satisfy the requirement — branch paths are
 *         not unique per node, and `*` is what singles out the one fork. (Group 2)
 *
 *    [C3] V_pre is the JUSTIFICATION closure, not "minimal": n ∈ vPre iff cond 3
 *         (∃ edge (n,h), h∈vH) or cond 4 (∃ edge (n,p), p∈vPre). On the POG DAG
 *         this is the unique dependency-ancestor closure of vH through non-vH
 *         nodes; an unjustified node is excluded (lands in vPost). vPre may reach
 *         DOWNWARD in the tree (a tree-descendant of the fragment root the
 *         fragment depends on). (Group 4)
 *
 *    [C4] TRIVIAL fragments re-prove the original goal, so enumerate drops them
 *         regardless of the (swappable) heuristic: root == proofRoot && no holes.
 *         The whole proof is the canonical instance. Admissibility is unaffected
 *         — a trivial fragment is still admissible. (isTrivial; Groups 7–8)
 */
class DecomposerTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private val dummyObl = Obligation(Nil, "g")
  private val dummyFp  = Footprint(Set.empty, Set.empty, false, Nil)
  private val dummySum = TacticSummary(Nil, Nil)

  /** A dependency edge; `kind` is irrelevant to Phase A, so we use a fixed dummy. */
  private def e(from: Int, to: Int): PogEdge = PogEdge(from, to, UseEdge)

  private def bp(segs: String*): BranchPath = BranchPath(segs.toList)

  /** Node by TREE SHAPE only; mₙ = output count tracks child count (the well-
   *  formed proof-tree invariant — every subgoal slot is filled in the original
   *  proof). Obligation/footprint/summary are dummies — Phase A never reads them. */
  private def tn(id: Int, parent: Option[Int], children: List[Int]): TacticNode =
    TacticNode(id, "tac", dummyObl, List.fill(children.size)(dummyObl), dummySum, parent, children)

  /** Assemble a POG from a tree (TacticNodes) and a hand-chosen edge set. Branch
   *  paths are derived from the tree via the real pog-module algorithm, so they
   *  stay consistent with the shape; edges are injected verbatim for control. */
  private def pog(rootId: Int, nodes: List[TacticNode], edges: List[PogEdge]): ProofOrderingGraph =
    val bps = BranchPath.compute(nodes)
    ProofOrderingGraph("d", "theorem d : g", rootId, dummyObl,
      nodes.map(n => PogNode(n, dummyFp, bps(n.id))), edges)

  /** A candidate from its root and explicit per-node subgoal counts mₙ. */
  private def cand(root: Int, counts: (Int, Int)*): Candidate = Candidate(root, counts.toMap)


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Convexity (isConvex), over G_T EDGES not tree edges  [C1]
  // ═══════════════════════════════════════════════════════════════════════════

  "Decomposer.isConvex" should "hold vacuously for the empty set and singletons" in {
    Decomposer.isConvex(Set.empty, Nil)        shouldBe true
    Decomposer.isConvex(Set(7), List(e(0, 7))) shouldBe true
  }

  it should "hold for an adjacent edge pair" in {
    Decomposer.isConvex(Set(0, 1), List(e(0, 1))) shouldBe true
  }

  it should "accept the reordered {A,C}: chain A→B→C with edges (A,B),(A,C) skips B" in {
    // B (=1) is NOT on a directed edge-path A⇒C (the only path 0⇒2 is the direct
    // edge), so {A,C} is convex even though B sits between them in the tree.
    Decomposer.isConvex(Set(0, 2), List(e(0, 1), e(0, 2))) shouldBe true
  }

  it should "reject {A,C} when the path runs THROUGH B: edges (A,B),(B,C)" in {
    Decomposer.isConvex(Set(0, 2), List(e(0, 1), e(1, 2))) shouldBe false
  }

  it should "be a GRAPH property, not a TREE property: no edges ⇒ convex despite a tree-intermediate" in {
    // A→B→C in the tree but no dependency edges at all: vacuously convex.
    Decomposer.isConvex(Set(0, 2), Nil) shouldBe true
  }

  it should "reject a diamond's tips {A,D} (both B and C lie on A⇒D paths)" in {
    val edges = List(e(0, 1), e(0, 2), e(1, 3), e(2, 3))
    Decomposer.isConvex(Set(0, 3), edges)          shouldBe false
    Decomposer.isConvex(Set(0, 1, 2, 3), edges)    shouldBe true
  }

  it should "reject a 3-hop {A,C} but accept the filled-in {A,B,C}" in {
    val edges = List(e(0, 1), e(1, 2))
    Decomposer.isConvex(Set(0, 2), edges)    shouldBe false
    Decomposer.isConvex(Set(0, 1, 2), edges) shouldBe true
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — Branch closure (isBranchClosed), over branch paths  [C2]
  // ═══════════════════════════════════════════════════════════════════════════

  // A branching root with two leaf children.
  private val forkPaths = Map(0 -> bp("*"), 1 -> bp("0"), 2 -> bp("1"))

  // prop_14-shaped nested fork:  0 ["*"] → {1 ["0"], 2 ["1"]};  2 → 3 ["1*"]
  //   → {4 ["1","0"], 5 ["1","0"], 6 ["1","1"]}  (5 is below 4 on the same branch)
  private val nestedPaths = Map(
    0 -> bp("*"), 1 -> bp("0"), 2 -> bp("1"), 3 -> bp("1*"),
    4 -> bp("1", "0"), 5 -> bp("1", "0"), 6 -> bp("1", "1")
  )

  "Decomposer.isBranchClosed" should "hold for any subset of a linear chain (no differing paths)" in {
    val linear = Map(0 -> bp(), 1 -> bp(), 2 -> bp())
    Decomposer.isBranchClosed(Set(0, 2), linear)    shouldBe true
    Decomposer.isBranchClosed(Set(0, 1, 2), linear) shouldBe true
  }

  it should "reject two children of a fork when the fork node is absent" in {
    Decomposer.isBranchClosed(Set(1, 2), forkPaths) shouldBe false
  }

  it should "accept once the fork node ['*'] is included" in {
    Decomposer.isBranchClosed(Set(0, 1, 2), forkPaths) shouldBe true
  }

  it should "accept a single branch taken with its fork present ({R,c0}) — the branch-with-hole shape" in {
    // Admissible (branch-closed); it is the ENUMERATION HEURISTIC, not closure,
    // that later rejects branch-with-a-hole.
    Decomposer.isBranchClosed(Set(0, 1), forkPaths) shouldBe true
  }

  it should "require the NESTED fork ['1*'] for two cousins, not the root" in {
    Decomposer.isBranchClosed(Set(4, 6), nestedPaths)       shouldBe false
    Decomposer.isBranchClosed(Set(3, 4, 6), nestedPaths)    shouldBe true
  }

  it should "NOT force an extra node for an ancestor/descendant pair across the self-* ([C2] strip-for-compare)" in {
    // 3 ["1*"] is the tree-parent of 4 ["1","0"]. Their POSITIONS (["1"] vs
    // ["1","0"]) share prefix ["1"], whose fork is 3 itself — already present.
    // A naive raw-string compare ("1*" ≠ "1") would wrongly demand the root.
    Decomposer.isBranchClosed(Set(3, 4), nestedPaths) shouldBe true
  }

  it should "NOT let a non-branching node spoof the fork ([C2] fork must carry *)" in {
    // node 2 ["1"] shares the stripped position ["1"] with the real fork 3
    // ["1*"], but 2 does not branch. Adding 2 (not 3) must NOT satisfy {4,6}.
    Decomposer.isBranchClosed(Set(2, 4, 6), nestedPaths) shouldBe false
    Decomposer.isBranchClosed(Set(3, 4, 6), nestedPaths) shouldBe true
  }

  it should "force the root for nodes on different top-level branches" in {
    Decomposer.isBranchClosed(Set(1, 5), nestedPaths)       shouldBe false  // ["0"] vs ["1","0"]
    Decomposer.isBranchClosed(Set(0, 1, 5), nestedPaths)    shouldBe true
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Admissibility + single root (isAdmissible, fragmentRoot)
  // ═══════════════════════════════════════════════════════════════════════════

  // Linear tree 0→1→2 (A,B,C), reordered edges (0,1),(0,2): C re-parented under A.
  private val reorderPog = pog(0,
    List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)),
    List(e(0, 1), e(0, 2)))

  // Same tree, transitive edges (0,1),(1,2): {0,2} is non-convex.
  private val chainPog = pog(0,
    List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)),
    List(e(0, 1), e(1, 2)))

  // Branching root 0→{1,2}, both leaves depend on 0.
  private val branchPog = pog(0,
    List(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil)),
    List(e(0, 1), e(0, 2)))

  "Decomposer.isAdmissible" should "accept the reordered {A,C} (convex + branch-closed + single-rooted)" in {
    Decomposer.isAdmissible(Set(0, 2), reorderPog) shouldBe true
  }

  it should "reject a non-convex {A,C}" in {
    Decomposer.isAdmissible(Set(0, 2), chainPog) shouldBe false
  }

  it should "reject fork children {c0,c1} without their fork" in {
    Decomposer.isAdmissible(Set(1, 2), branchPog) shouldBe false
  }

  it should "reject the empty set" in {
    Decomposer.isAdmissible(Set.empty, reorderPog) shouldBe false
  }

  it should "accept the full vertex set (admissible, though enumerate drops it as trivial)" in {
    Decomposer.isAdmissible(Set(0, 1, 2), reorderPog) shouldBe true
  }

  it should "accept a singleton leaf" in {
    Decomposer.isAdmissible(Set(2), reorderPog) shouldBe true
  }

  "Decomposer.fragmentRoot" should "be the tree-topmost node of a reordered set" in {
    Decomposer.fragmentRoot(Set(0, 2), reorderPog) shouldBe Some(0)
  }

  it should "be the node itself for a singleton" in {
    Decomposer.fragmentRoot(Set(2), reorderPog) shouldBe Some(2)
  }

  it should "be None for a non-single-rooted set (sibling leaves)" in {
    Decomposer.fragmentRoot(Set(1, 2), branchPog) shouldBe None
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — Pre-set closure (vPre): justification, not minimality  [C3]
  // ═══════════════════════════════════════════════════════════════════════════

  "Decomposer.vPre" should "be empty when nothing depends into vH (vH = root)" in {
    Decomposer.vPre(Set(0), List(e(0, 1))) shouldBe Set.empty
  }

  it should "pull a direct dependency (cond 3)" in {
    // edge (0,1): node 1 depends on node 0; vH = {1}.
    Decomposer.vPre(Set(1), List(e(0, 1))) shouldBe Set(0)
  }

  it should "[INV-A] close upward under cond 4: a vPre node's dependency is in vPre" in {
    // edges 0→1→2, vH={2}: 1 by cond 3, then 0 by cond 4 (1∈vPre depends on 0).
    Decomposer.vPre(Set(2), List(e(0, 1), e(1, 2))) shouldBe Set(0, 1)
  }

  it should "[4.4] reach a tree-DESCENDANT of the fragment root that vH depends on" in {
    // tree 0→1→2→3, vH={1,3}, edge (2,3): node 2 (a descendant of root 1) must
    // run before the fragment ⇒ 2 ∈ vPre, though it sits below the root.
    Decomposer.vPre(Set(1, 3), List(e(2, 3))) shouldBe Set(2)
  }

  it should "ignore edges internal to vH (both endpoints inside)" in {
    // edge (0,1) with both in vH does not add 0 to vPre via this edge.
    Decomposer.vPre(Set(0, 1), List(e(0, 1))) shouldBe Set.empty
  }

  it should "[4.7] exclude an UNJUSTIFIED node (neither cond 3 nor cond 4) ⇒ it is not in vPre" in {
    // edge (0,1) feeds vH; the disjoint chain (8,9) reaches neither vH nor any
    // vPre node, so 8 and 9 are unjustified and stay out (they belong in vPost).
    Decomposer.vPre(Set(1), List(e(0, 1), e(8, 9))) shouldBe Set(0)
  }

  it should "[INV-B] cover every dependency of a vH node in vH ∪ vPre (cond 3)" in {
    // vH={1,2}; node 2 depends on 0 (external) and 1 (internal).
    val vH    = Set(1, 2)
    val edges = List(e(0, 2), e(1, 2))
    val vPre  = Decomposer.vPre(vH, edges)
    vPre shouldBe Set(0)                       // external dep pulled in
    val depsOf2 = edges.filter(_.to == 2).map(_.from).toSet
    depsOf2.subsetOf(vH ++ vPre) shouldBe true // 0 via vPre, 1 via vH
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — decompose: partition invariants
  // ═══════════════════════════════════════════════════════════════════════════

  // tree 0→1→2→3, edge (2,3): the [4.4] reorder shape as a full POG.
  private val descPullPog = pog(0,
    List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), List(3)), tn(3, Some(2), Nil)),
    List(e(2, 3)))

  "Decomposer.decompose" should "yield a disjoint partition covering all vertices" in {
    val d = Decomposer.decompose(Set(1, 3), descPullPog)
    (d.vH ++ d.vPre ++ d.vPost) shouldBe Set(0, 1, 2, 3)
    (d.vH & d.vPre)   shouldBe empty
    (d.vH & d.vPost)  shouldBe empty
    (d.vPre & d.vPost) shouldBe empty
  }

  it should "set vPost = V \\ (vH ∪ vPre) exactly" in {
    val d = Decomposer.decompose(Set(1, 3), descPullPog)
    d.vPost shouldBe (Set(0, 1, 2, 3) -- d.vH -- d.vPre)
  }

  it should "place the depended-on tree-descendant in vPre and the root in vPost" in {
    val d = Decomposer.decompose(Set(1, 3), descPullPog)
    d.vH   shouldBe Set(1, 3)
    d.vPre shouldBe Set(2)     // descendant of root 1, pulled before the fragment
    d.vPost shouldBe Set(0)    // the proof root: the fragment does not depend on it
  }

  it should "give the full vertex set an empty pre- and post-set" in {
    val d = Decomposer.decompose(Set(0, 1, 2, 3), descPullPog)
    d.vPre  shouldBe empty
    d.vPost shouldBe empty
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — Enumeration heuristic (structural, on Candidate)
  //   reproduces the CLAUDE.md shape table: accept = !branches || !hasHole
  // ═══════════════════════════════════════════════════════════════════════════

  private val chainLeaf   = cand(0, 0 -> 1, 1 -> 1, 2 -> 0)  // 1,1,0
  private val chainHole   = cand(0, 0 -> 1, 1 -> 1, 2 -> 1)  // 1,1,1
  private val branchLeaf  = cand(0, 0 -> 2, 1 -> 0, 2 -> 0)  // 2,0,0
  private val branchHole  = cand(0, 0 -> 2, 1 -> 0)          // 2,0

  "Decomposer.holeCount" should "be (Σmₙ) − (|vH|−1) across the four canonical shapes" in {
    Decomposer.holeCount(chainLeaf)  shouldBe 0   // 2 − 2
    Decomposer.holeCount(chainHole)  shouldBe 1   // 3 − 2
    Decomposer.holeCount(branchLeaf) shouldBe 0   // 2 − 2
    Decomposer.holeCount(branchHole) shouldBe 1   // 2 − 1
  }

  it should "count multiple open slots" in {
    // |vH|=3, Σmₙ = 2+3+0 = 5 ⇒ 5 − 2 = 3 holes.
    Decomposer.holeCount(cand(0, 0 -> 2, 1 -> 3, 2 -> 0)) shouldBe 3
  }

  "Decomposer.branches" should "detect any node with mₙ ≥ 2" in {
    Decomposer.branches(chainLeaf)  shouldBe false
    Decomposer.branches(branchLeaf) shouldBe true
  }

  "Decomposer.defaultHeuristic" should "accept chain→leaf, chain→hole, and branch-closed-to-leaves" in {
    Decomposer.defaultHeuristic(chainLeaf)  shouldBe true
    Decomposer.defaultHeuristic(chainHole)  shouldBe true
    Decomposer.defaultHeuristic(branchLeaf) shouldBe true
  }

  it should "reject ONLY branch-with-a-hole" in {
    Decomposer.defaultHeuristic(branchHole) shouldBe false
  }

  it should "handle single-node candidates: leaf accept, branching-hole reject, linear-hole accept" in {
    Decomposer.defaultHeuristic(cand(0, 0 -> 0)) shouldBe true   // leaf:    holes 0
    Decomposer.defaultHeuristic(cand(0, 0 -> 2)) shouldBe false  // branch:  holes 2
    Decomposer.defaultHeuristic(cand(0, 0 -> 1)) shouldBe true   // linear:  holes 1
  }

  it should "be equivalent to (!branches || !hasHole), and a `_ => true` heuristic disables filtering" in {
    val shapes = List(chainLeaf, chainHole, branchLeaf, branchHole)
    shapes.foreach { c =>
      Decomposer.defaultHeuristic(c) shouldBe (!Decomposer.branches(c) || !Decomposer.hasHole(c))
    }
    val allow: Candidate.Heuristic = _ => true
    allow(branchHole) shouldBe true
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Trivial exclusion + enumerate  [C4]
  // ═══════════════════════════════════════════════════════════════════════════

  // Tiny linear POG 0→1→2 with deps 0≺1≺2; proof root 0.
  private val linPog = pog(0,
    List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)),
    List(e(0, 1), e(1, 2)))

  "Decomposer.isTrivial" should "flag a root-rooted, hole-free candidate (the whole proof)" in {
    // {0,1,2}: root 0 = proofRoot, holeCount = 2 − 2 = 0 ⇒ trivial.
    Decomposer.isTrivial(cand(0, 0 -> 1, 1 -> 1, 2 -> 0), linPog) shouldBe true
  }

  it should "NOT flag a root-rooted candidate that still has a hole" in {
    // {0,1}: root 0 = proofRoot but holeCount = 2 − 1 = 1.
    Decomposer.isTrivial(cand(0, 0 -> 1, 1 -> 1), linPog) shouldBe false
  }

  it should "NOT flag a hole-free candidate rooted away from the proof root" in {
    // {1,2}: holeCount 0 but root 1 ≠ proofRoot.
    Decomposer.isTrivial(cand(1, 1 -> 1, 2 -> 0), linPog) shouldBe false
  }

  // Admissible V_H of linPog: {0},{1},{2},{0,1},{1,2},{0,1,2}. None branches, so
  // singletons {0},{1},{2} are dropped; {0,1,2} is trivial ⇒ only 2-node fragments remain.
  "Decomposer.enumerate" should "emit exactly the admissible, non-singleton, non-trivial fragments of a tiny chain" in {
    val (decomps, _) = Decomposer.enumerate(linPog, Decomposer.defaultHeuristic, 10_000)
    decomps.map(_.vH).toSet shouldBe Set(Set(0, 1), Set(1, 2))
  }

  it should "attach the correct pre/post sets to each emitted fragment" in {
    val (decomps, _) = Decomposer.enumerate(linPog, Decomposer.defaultHeuristic, 10_000)
    val byVH = decomps.iterator.map(d => d.vH -> d).toMap
    byVH(Set(1, 2)).vPre  shouldBe Set(0)      // node 1 depends on 0 (cond 3), 0 has no further deps
    byVH(Set(1, 2)).vPost shouldBe Set.empty
    byVH(Set(0, 1)).vPre  shouldBe Set.empty
    byVH(Set(0, 1)).vPost shouldBe Set(2)
  }

  // Branching POG 0→{1,2}, both leaves depend on 0; proof root 0. Here the
  // singleton filter bites ({1},{2}) and the heuristic bites ({0,1},{0,2} are
  // branch-with-a-hole); only the allow-all heuristic can emit the 2-node sets.
  it should "let the heuristic gate branch-with-a-hole (default ⊂ allow-all)" in {
    val allow: Candidate.Heuristic = _ => true
    val (deflt, _) = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)
    val (open,  _) = Decomposer.enumerate(branchPog, allow, 10_000)
    deflt.map(_.vH).toSet shouldBe Set.empty                                 // {1},{2} singletons; {0,1},{0,2} branch-with-hole
    open.map(_.vH).toSet  shouldBe Set(Set(0, 1), Set(0, 2))                 // singletons still dropped; {0,1,2} trivial
    deflt.map(_.vH).toSet.subsetOf(open.map(_.vH).toSet) shouldBe true
    // {0,1,2} is trivial (root 0, holes 0) ⇒ absent from BOTH.
    open.map(_.vH) should not contain Set(0, 1, 2)
  }

  it should "emit only admissible, non-trivial, heuristic-accepted decompositions" in {
    val (decomps, _) = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)
    decomps.foreach { d =>
      withClue(s"vH=${d.vH}: ") {
        Decomposer.isAdmissible(d.vH, branchPog) shouldBe true
        val c = cand(Decomposer.fragmentRoot(d.vH, branchPog).get,
                     d.vH.toSeq.map(id => id -> branchPog.nodes.find(_.node.id == id).get.node.outputObligations.size)*)
        Decomposer.isTrivial(c, branchPog)    shouldBe false
        Decomposer.defaultHeuristic(c)        shouldBe true
      }
    }
  }

  it should "emit valid disjoint partitions" in {
    val all = branchPog.nodes.map(_.node.id).toSet
    val (decomps, _) = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)
    decomps.foreach { d =>
      (d.vH ++ d.vPre ++ d.vPost) shouldBe all
      (d.vH & d.vPre) shouldBe empty
      (d.vH & d.vPost) shouldBe empty
      (d.vPre & d.vPost) shouldBe empty
    }
  }

  it should "report accepted == result size, examined == accepted + skipped, not timed out" in {
    val (decomps, rep) = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)
    rep.accepted shouldBe decomps.size
    rep.examined shouldBe (rep.accepted + rep.skipped)
    rep.examined should be >= rep.accepted
    rep.timedOut shouldBe false
  }

  it should "be deterministic for the same inputs" in {
    val a = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)._1.map(_.vH)
    val b = Decomposer.enumerate(branchPog, Decomposer.defaultHeuristic, 10_000)._1.map(_.vH)
    a shouldBe b
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Golden prop_14 (real phase-2 fixture data/pogs/Examples.json)
  // ═══════════════════════════════════════════════════════════════════════════
  //
  //   0 induction xs → {1,2}   m=2   ["*"]
  //   1 simp (nil leaf)        m=0   ["0"]
  //   2 simp → 3               m=1   ["1"]
  //   3 split_ifs → {4,6}      m=2   ["1*"]
  //   4 simp → 5               m=1   ["1","0"]
  //   5 exact ih (leaf)        m=0   ["1","0"]
  //   6 exact ih (leaf)        m=0   ["1","1"]
  //   edges: (0,2)(2,3)(3,4) modify, (0,5)(0,6) use

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  private lazy val prop14: ProofOrderingGraph =
    val pf = PogParser.parseFile(fixture)
    pf.pogs.head.ensuring(_.declName == "prop_14", "fixture drift: prop_14 expected first")

  private def mOf(p: ProofOrderingGraph, id: Int): Int =
    p.nodes.find(_.node.id == id).get.node.outputObligations.size

  private def candFor(p: ProofOrderingGraph, vH: Set[Int]): Candidate =
    cand(Decomposer.fragmentRoot(vH, p).get, vH.toSeq.map(id => id -> mOf(p, id))*)

  "Decomposer (golden prop_14)" should "admit the cons sub-chain {4,5} and decompose it exactly" in {
    Decomposer.isAdmissible(Set(4, 5), prop14) shouldBe true
    Decomposer.fragmentRoot(Set(4, 5), prop14) shouldBe Some(4)
    val d = Decomposer.decompose(Set(4, 5), prop14)
    d.vPre  shouldBe Set(0, 2, 3)
    d.vPost shouldBe Set(1, 6)
    Decomposer.defaultHeuristic(candFor(prop14, Set(4, 5))) shouldBe true   // no branch
  }

  it should "admit {2,3,4,5} but have the heuristic reject it (branch node 3, hole at child 6)" in {
    Decomposer.isAdmissible(Set(2, 3, 4, 5), prop14) shouldBe true
    val c = candFor(prop14, Set(2, 3, 4, 5))
    Decomposer.branches(c) shouldBe true
    Decomposer.holeCount(c) shouldBe 1
    Decomposer.defaultHeuristic(c) shouldBe false
  }

  it should "treat the whole proof {0..6} as admissible but trivial" in {
    val whole = (0 to 6).toSet
    Decomposer.isAdmissible(whole, prop14)            shouldBe true
    Decomposer.isTrivial(candFor(prop14, whole), prop14) shouldBe true
  }

  it should "admit {0,1} (root + nil branch) but reject it as branch-with-a-hole" in {
    Decomposer.isAdmissible(Set(0, 1), prop14) shouldBe true
    val c = candFor(prop14, Set(0, 1))
    Decomposer.holeCount(c)        shouldBe 1
    Decomposer.defaultHeuristic(c) shouldBe false
  }

  it should "never emit a branching fragment with a hole, and never the whole proof" in {
    val (decomps, rep) = Decomposer.enumerate(prop14, Decomposer.defaultHeuristic, 30_000)
    rep.timedOut shouldBe false
    decomps.foreach { d =>
      val c = candFor(prop14, d.vH)
      withClue(s"vH=${d.vH}: ") {
        (Decomposer.branches(c) && Decomposer.hasHole(c)) shouldBe false
        Decomposer.isTrivial(c, prop14)                   shouldBe false
      }
    }
    decomps.map(_.vH) should not contain (0 to 6).toSet
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 9 — Defensive / degenerate (fail fast over silently wrong)
  // ═══════════════════════════════════════════════════════════════════════════

  "Decomposer (degenerate)" should "FAIL FAST when a vH node is missing from branchPaths" in {
    an [Exception] should be thrownBy Decomposer.isBranchClosed(Set(0, 1), Map(0 -> bp("*")))
  }

  it should "FAIL FAST when a vH node is absent from the POG" in {
    an [Exception] should be thrownBy Decomposer.isAdmissible(Set(99), branchPog)
  }

  it should "emit nothing for a single-leaf proof (its only fragment is the trivial whole proof)" in {
    val leaf = pog(0, List(tn(0, None, Nil)), Nil)   // root 0, m=0
    val (decomps, rep) = Decomposer.enumerate(leaf, Decomposer.defaultHeuristic, 10_000)
    decomps      shouldBe empty
    rep.accepted shouldBe 0
    rep.timedOut shouldBe false
  }
