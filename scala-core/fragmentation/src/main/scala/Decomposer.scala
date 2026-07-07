import scala.collection.mutable

// ─────────────────────────────────────────────────────────────────────────────
//  Phase A — POG Decomposition (paper §2.3).
//
//  Purely STRUCTURAL: works on the POG's tree shape (parent/child), its
//  dependency edges E, and per-node subgoal counts mₙ (= output_obligations
//  size). No obligations and no tactic effects — those are Phase B (Reconstructor).
//
//  Each function takes the LEAST information that determines its result, so the
//  predicates stay independently testable (cf. DecomposerTest):
//    • convexity / pre-set        — depend only on edge reachability (kind ignored)
//    • branch closure             — depends only on branch paths (the `*` is
//                                   load-bearing: it identifies the fork node)
//    • root / admissibility / enumerate — need the whole POG (tree + edges + paths)
// ─────────────────────────────────────────────────────────────────────────────

object Decomposer:

  // ── admissibility of V_H (§2.3 conditions 1–2 + single root) ────────────────

  /** Convexity (cond 2): for any `a, c ∈ vH` and any directed path `a → … → c`
   *  in `G_T`, every node on the path lies in `vH`. Edge `kind` is irrelevant —
   *  only (from, to) reachability matters.
   *
   *  A node `b ∉ vH` violates convexity iff some `vH` node reaches it AND it
   *  reaches some `vH` node — then `b` sits on a directed `vH`→`vH` path. */
  def isConvex(vH: Set[Int], edges: List[PogEdge]): Boolean =
    if vH.size <= 1 then true
    else
      val succ = edges.groupMap(_.from)(_.to)
      val memo = mutable.Map.empty[Int, Set[Int]]
      def desc(x: Int): Set[Int] =                       // proper descendants (DAG ⇒ terminates)
        memo.getOrElseUpdate(x,
          succ.getOrElse(x, Nil).foldLeft(Set.empty[Int])((acc, c) => acc + c ++ desc(c)))
      val nodes = (edges.flatMap(e => List(e.from, e.to)) ++ vH).toSet
      nodes.forall { b =>
        vH.contains(b) || {
          val vHReachesB = vH.exists(a => desc(a).contains(b))
          val bReachesVH = desc(b).exists(vH.contains)
          !(vHReachesB && bReachesVH)
        }
      }

  /** Branch closure (cond 1): for `aᵢ, aⱼ ∈ vH` whose tree positions differ, the
   *  fork node where their branch paths diverge must also be in `vH`.
   *
   *  Positions are compared with the self-branch `*` stripped from the last
   *  segment (so `["1*"]` and `["1","0"]` share prefix `["1"]`, forcing nothing
   *  extra), but the required fork must be the actual BRANCHING node — matched by
   *  its STORED path carrying `*` (`["1*"]`, or `["*"]` at the root). Branch
   *  paths are not unique per node, so the `*` is what singles out the one fork
   *  in a chain region. */
  def isBranchClosed(vH: Set[Int], branchPaths: Map[Int, BranchPath]): Boolean =
    val stored = vH.iterator.map(id => id -> branchPaths(id).segments).toMap  // fail-fast
    val storedSet = stored.values.toSet
    val ids = vH.toIndexedSeq
    val positions = stored.view.mapValues(stripStar).toMap
    val pairs = for i <- ids.indices.iterator; j <- (i + 1 until ids.size).iterator yield (ids(i), ids(j))
    pairs.forall { (a, b) =>
      positions(a) == positions(b) || storedSet.contains(forkPath(commonPrefix(positions(a), positions(b))))
    }

  /** A branch path's tree position: drop the trailing `*` from the last segment
   *  (an empty result, from the root marker `["*"]`, collapses to `Nil`). */
  private def stripStar(segments: List[String]): List[String] =
    segments match
      case init :+ last if last.endsWith("*") =>
        val base = last.dropRight(1)
        if base.isEmpty then init else init :+ base
      case other => other

  /** The stored branch path of the fork node at a divergence position: the `*`
   *  fused onto the last segment, or `["*"]` when the fork is the root. */
  private def forkPath(position: List[String]): List[String] =
    position match
      case Nil          => List("*")
      case init :+ last => init :+ (last + "*")

  private def commonPrefix(a: List[String], b: List[String]): List[String] =
    a.zip(b).takeWhile((x, y) => x == y).map(_._1)

  /** The fragment root: the unique node of `vH` that is a tree-ancestor of every
   *  other node of `vH`. `None` when `vH` is empty or not single-rooted. */
  def fragmentRoot(vH: Set[Int], pog: ProofOrderingGraph): Option[Int] =
    if vH.isEmpty then None
    else
      val byId = pog.nodes.iterator.map(p => p.node.id -> p.node).toMap
      def ancestors(id: Int): Set[Int] =                 // fail-fast if id ∉ pog
        val acc = mutable.Set.empty[Int]
        var cur = byId(id).parentId
        while cur.isDefined do
          acc += cur.get
          cur = byId(cur.get).parentId
        acc.toSet
      val anc   = vH.iterator.map(id => id -> ancestors(id)).toMap
      val roots = vH.filter(id => anc(id).intersect(vH).isEmpty)
      Option.when(roots.size == 1 && vH.forall(o => o == roots.head || anc(o).contains(roots.head)))(roots.head)

  /** `vH` is admissible iff it is non-empty, convex, branch-closed, and
   *  single-rooted. */
  def isAdmissible(vH: Set[Int], pog: ProofOrderingGraph): Boolean =
    val branchPaths = pog.nodes.iterator.map(p => p.node.id -> p.branchPath).toMap
    vH.nonEmpty &&
      isConvex(vH, pog.edges) &&
      isBranchClosed(vH, branchPaths) &&
      fragmentRoot(vH, pog).isDefined

  // ── pre-set / post-set (§2.3 conditions 3–4) ────────────────────────────────

  /** The pre-set `vPre ⊆ V \ vH`: every node justified by cond 3 (H directly
   *  depends on it: `∃ edge (n, h)`, `h ∈ vH`) or cond 4 (a `vPre` node depends
   *  on it: `∃ edge (n, p)`, `p ∈ vPre`). On the POG DAG this least fixpoint is
   *  the unique dependency-ancestor closure of `vH` reached through non-`vH`
   *  nodes — an unjustified node never enters. */
  def vPre(vH: Set[Int], edges: List[PogEdge]): Set[Int] =
    var pre     = Set.empty[Int]
    var changed = true
    while changed do
      changed = false
      for PogEdge(from, to, _) <- edges
      if !vH.contains(from) && !pre.contains(from) && (vH.contains(to) || pre.contains(to))
      do
        pre += from
        changed = true
    pre

  /** Partition `V` into the decomposition `(vH, vPre, vPost)` with
   *  `vPost = V \ (vH ∪ vPre)`. */
  def decompose(vH: Set[Int], pog: ProofOrderingGraph): Decomposition =
    val all  = pog.nodes.map(_.node.id).toSet
    val pre  = vPre(vH, pog.edges)
    Decomposition(vH, pre, all -- vH -- pre)

  // ── enumeration heuristic (CLAUDE.md §"Enumeration heuristic") ──────────────

  /** Open subgoal slots: `(Σ_{n∈vH} mₙ) − (|vH| − 1)` — the total subgoals minus
   *  the `|vH| − 1` slots filled by non-root `vH` nodes. */
  def holeCount(c: Candidate): Int = c.subgoalCounts.values.sum - (c.size - 1)

  /** `holeCount(c) > 0`: a fragment whose selected nodes leave open slots. */
  def hasHole(c: Candidate): Boolean = holeCount(c) > 0

  /** Some `vH` node splits its goal into ≥2 subgoals (`mₙ ≥ 2`). */
  def branches(c: Candidate): Boolean = c.subgoalCounts.values.exists(_ >= 2)

  /** The default lemma-shape filter: accept unless the fragment both branches and
   *  has a hole (`!branches || !hasHole`). */
  def defaultHeuristic: Candidate.Heuristic = c => !branches(c) || !hasHole(c)

  /** A trivial fragment re-proves the original goal, so its `Lem(·)` is the
   *  theorem that already exists: rooted at the proof root with no holes. Dropped
   *  by `enumerate` independent of the (swappable) heuristic. */
  def isTrivial(c: Candidate, pog: ProofOrderingGraph): Boolean =
    c.root == pog.rootTacticId && holeCount(c) == 0

  /** A single-tactic fragment encodes no reusable structure. Dropped by
   *  `enumerate` independent of the (swappable) heuristic. */
  def isSingleton(c: Candidate): Boolean = c.size == 1

  // ── enumeration (§2.3 Phase A driver) ───────────────────────────────────────

  /** Enumerate admissible, non-trivial, heuristic-accepted decompositions of the
   *  POG, lazily, under a wall-clock `timeoutMs` budget. Returns the accepted
   *  decompositions plus an [[EnumerationReport]] so a capped run is never
   *  mistaken for an exhaustive one.
   *
   *  Candidate `vH` sets are drawn from the powerset of the node ids and gated by
   *  [[isAdmissible]]; `examined` counts the admissible sets reached by the
   *  heuristic, partitioned into `accepted` (emitted) and `skipped` (trivial or
   *  rejected), so `examined == accepted + skipped`. */
  def enumerate(
    pog:       ProofOrderingGraph,
    heuristic: Candidate.Heuristic,
    timeoutMs: Long
  ): (List[Decomposition], EnumerationReport) =
    val ids      = pog.nodes.filter(p => p.node.tacticText.trim != "admit").map(_.node.id).toIndexedSeq
    val mById    = pog.nodes.iterator.map(p => p.node.id -> p.node.outputObligations.size).toMap
    val deadline = System.currentTimeMillis + timeoutMs
    val out      = mutable.ListBuffer.empty[Decomposition]
    var examined = 0
    var accepted = 0
    var skipped  = 0
    var timedOut = false

    val total = 1L << ids.size
    var bits  = 1L                                       // skip the empty set
    while bits < total && !timedOut do
      if System.currentTimeMillis >= deadline then timedOut = true
      else
        val vH = ids.indices.collect { case i if (bits & (1L << i)) != 0 => ids(i) }.toSet
        if isAdmissible(vH, pog) then
          examined += 1
          val root = fragmentRoot(vH, pog).get
          val c    = Candidate(root, vH.iterator.map(id => id -> mById(id)).toMap)
          if !isTrivial(c, pog) && !isSingleton(c) && heuristic(c) then
            out += decompose(vH, pog)
            accepted += 1
          else skipped += 1
        bits += 1

    (out.toList, EnumerationReport(examined, accepted, skipped, timedOut))
