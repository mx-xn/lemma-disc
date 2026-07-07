/** The dependency edges aᵢ ≺ aⱼ of paper Definition 2 (§2.1), name-level
 *  coarsened — the POG's edge set E. `Builder` assembles the graph via
 *
 *    Dependency.compute(nodes, footprints) : List[PogEdge]
 *
 *  which returns DEDUPLICATED `(from, to, kind)` edges over every root-to-leaf
 *  path. `compute` reads the TREE SHAPE (`parentId` / `childIds`, for paths and
 *  branch indices) and the supplied per-node `Footprint` map; it never inspects
 *  obligation contents — those were already distilled into footprints by
 *  `Footprint.compute`.
 *
 *  ── Paper Definition 2 ──────────────────────────────────────────────────────
 *
 *  Along a root-to-leaf path a₁,…,aₙ with footprints Φ(aₖ)=(Dₖ,Mₖ,_,ρₖ), extend
 *  ρ to a forward propagation ρ_{i→j} along the path. For i<j, aⱼ depends on aᵢ
 *  (aᵢ ≺ aⱼ) if either:
 *    1. (Modification) ∃ s∈Mᵢ with ρ_{i→j}(s) landing on some q∈Mⱼ; or
 *    2. (Use)          ∃ s∈Mᵢ with ρ_{i→j}(s) landing on some q∈Dⱼ;
 *  in each case with NO intermediate k (i<k<j) satisfying the same condition
 *  relative to aⱼ. If both hold for one (i,j), two distinct edges are emitted.
 *
 *  ── Load-bearing interpretations (settled in design review 2026-06-01, mirrored
 *     in DependencyTest's header as [P1]–[P4]; do NOT loosen toward the prose) ──
 *
 *    [P1] FORWARD PROPAGATION composes ρ of path nodes i … j-1 — node i's OWN ρ
 *         is applied, node j's is NOT (ρ_{i→i}=id, ρ_{i→j+1}=ρ_{j+1}∘ρ_{i→j}).
 *         At each step the branch index = position of the next-on-path child in
 *         `childIds`. A name ρ does not carry simply drops out (empty-default),
 *         so a literal name re-introduced downstream without a ρ link yields NO
 *         edge.
 *
 *    [P2] SOURCE MODIFIED SET  Mᵢ = modifiesHyps ∪ {"⊢" if modifiesGoal}. The
 *         goal token originates a dependency ONLY when modifies_goal — distinct
 *         from the unconditional ⊢→{⊢} that `Footprint` keeps in ρ for
 *         propagation.
 [P3] GOAL USE-EDGES FOR LEAVES. For non-leaf nodes D⊆Γ (hypotheses), so
 *         "⊢" is not a use-landing. For LEAF nodes (outputObligations empty),
 *         "⊢" is added to Dⱼ: a leaf must be applied at a specific goal, so it
 *         use-depends on the nearest preceding goal-modifier. See `uses` below.
 *
 *    as [P1]–[P4]; do NOT loosen toward the prose) ──
 *
 *    [P1] FORWARD PROPAGATION composes ρ of path nodes i … j-1 — node i's OWN ρ
 *         is applied, node j's is NOT (ρ_{i→i}=id, ρ_{i→j+1}=ρ_{j+1}∘ρ_{i→j}).
 *         At each step the branch index = position of the next-on-path child in
 *         `childIds`. A name ρ does not carry simply drops out (empty-default),
 *         so a literal name re-introduced downstream without a ρ link yields NO
 *         edge.
 *
 *    [P2] SOURCE MODIFIED SET  Mᵢ = modifiesHyps ∪ {"⊢" if modifiesGoal}. The
 *         goal token originates a dependency ONLY when modifies_goal — distinct
 *         from the unconditional ⊢→{⊢} that `Footprint` keeps in ρ for
 *         propagation.
 *
 *    [P3] GOAL EDGES ARE MODIFY-ONLY. Use-dependence needs q∈Dⱼ and D⊆Γ
 *         (hypotheses), so "⊢" is never a use-landing. Falls out for free below:
 *         ⊢ only ever appears in the modify-landing set.
 *
 *    [P4] "NO INTERMEDIATE k" IS PER-LANDING-NAME. A nearer source claims a
 *         landing name q; farther sources may still claim OTHER landing names.
 *         Realized by scanning sources nearest-first and removing already-claimed
 *         landing names — each edge is the nearest source per distinct q.
 *
 *  Complexity O(P · L³) for P paths of length ≤ L (a per-pair forward fold);
 *  proof trees are ≤ ~50 nodes, so this is comfortably fine (CLAUDE.md §Step 6).
 */
object Dependency:

  /** Reserved token denoting the goal slot (shared with `Footprint`). */
  private val Goal = "⊢"

  def compute(nodes: List[TacticNode], footprints: Map[Int, Footprint]): List[PogEdge] =
    val byId = nodes.iterator.map(n => n.id -> n).toMap

    // Mᵢ [P2] and Dⱼ. footprints(id) fails fast if a node has no footprint.
    def modifies(id: Int): Set[String] =
      val f = footprints(id)
      if f.modifiesGoal then f.modifiesHyps + Goal else f.modifiesHyps
    // Leaf tactics (outputObligations = []) must be applied at a specific goal, so
    // they implicitly use the current goal state.  Adding "⊢" here relaxes [P3] for
    // leaves only: the nearest preceding goal-modifier gets a use-edge to the leaf,
    // preventing the Decomposer from skipping goal-shaping tactics in a fragment.
    def uses(id: Int): Set[String] =
      if byId(id).outputObligations.isEmpty then footprints(id).uses + Goal
      else footprints(id).uses

    // Forward image of `names` from path position i to j [P1]: fold through the
    // ρ of nodes at positions i, i+1, …, j-1, picking the branch that continues
    // along the path. Empty-default at every step (uncarried names drop out).
    def forwardImage(path: Vector[Int], i: Int, j: Int, names: Set[String]): Set[String] =
      var cur = names
      var k = i
      while k < j && cur.nonEmpty do
        val node   = byId(path(k))
        val branch = node.childIds.indexOf(path(k + 1))
        val rho    = footprints(path(k)).rho(branch)
        cur = cur.flatMap(s => rho.getOrElse(s, Set.empty))
        k += 1
      cur

    // Edges discovered along one root-to-leaf path, with per-name minimality [P4].
    def pathEdges(path: Vector[Int]): List[PogEdge] =
      val out = collection.mutable.ListBuffer.empty[PogEdge]
      for j <- path.indices.drop(1) do
        val landMod = modifies(path(j))
        val landUse = uses(path(j))          // may include Goal for leaf nodes [P3]
        val claimedMod = collection.mutable.Set.empty[String]
        val claimedUse = collection.mutable.Set.empty[String]
        var i = j - 1
        while i >= 0 do
          val reached = forwardImage(path, i, j, modifies(path(i)))
          val newMod  = (reached & landMod) -- claimedMod
          if newMod.nonEmpty then
            out += PogEdge(path(i), path(j), ModifyEdge); claimedMod ++= newMod
          val newUse  = (reached & landUse) -- claimedUse
          if newUse.nonEmpty then
            out += PogEdge(path(i), path(j), UseEdge); claimedUse ++= newUse
          i -= 1
      out.toList

    // Enumerate root-to-leaf paths; byId(child) fails fast on a dangling childId.
    def paths(id: Int, acc: Vector[Int]): List[Vector[Int]] =
      val node = byId(id)
      val here = acc :+ id
      if node.childIds.isEmpty then List(here)
      else node.childIds.flatMap(c => paths(c, here))

    val roots = nodes.filter(_.parentId.isEmpty)
    roots.flatMap(r => paths(r.id, Vector.empty)).flatMap(pathEdges).distinct
