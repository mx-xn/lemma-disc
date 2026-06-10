/** Assembles the Proof Ordering Graph G_T = (V, E) for a declaration (paper
 *  §2.1) by composing the already-tested phase-2 components:
 *
 *    Footprint.compute   — per-node Φ(a, Γ, g) = (D, M, ρ)
 *    BranchPath.compute   — per-node B(a)
 *    Dependency.compute   — the edge set E (aᵢ ≺ aⱼ, Definition 2)
 *
 *  `Builder` adds NO new graph mathematics; it is the pure wiring layer that
 *  pairs each `TacticNode` with ITS OWN footprint and branch path (keyed BY ID,
 *  not by list position — node lists may be out of id-order with gaps, as
 *  prop_85 in the fixture is), preserves node order, and lifts the root
 *  obligation to the POG level for phase-3 convenience.
 *
 *  Fail-fast posture (shared with `BranchPath`/`Dependency`): a `root_tactic_id`
 *  that names no node is corrupt input — `build` throws rather than silently
 *  dropping the root obligation.
 */
object Builder:

  /** Build the POG for a single declaration. */
  def build(decl: Declaration): ProofOrderingGraph =
    val footprints  = decl.tacticNodes.iterator.map(n => n.id -> Footprint.compute(n)).toMap
    val branchPaths = BranchPath.compute(decl.tacticNodes)
    val edges       = Dependency.compute(decl.tacticNodes, footprints)

    // One PogNode per TacticNode, in input order; footprint/branchPath looked
    // up by id so a positional mismatch is impossible.
    val pogNodes = decl.tacticNodes.map(n => PogNode(n, footprints(n.id), branchPaths(n.id)))

    val rootObligation = decl.tacticNodes
      .find(_.id == decl.rootTacticId)
      .getOrElse(throw new NoSuchElementException(
        s"root_tactic_id=${decl.rootTacticId} names no node in declaration '${decl.name}'"))
      .inputObligation

    ProofOrderingGraph(
      declName       = decl.name,
      statement      = decl.statement,
      rootTacticId   = decl.rootTacticId,
      rootObligation = rootObligation,
      nodes          = pogNodes,
      edges          = edges
    )

  /** Build every declaration in a phase-1 trace file, preserving the source
   *  path and declaration order. */
  def buildFile(trace: LeanProofTrace): PogFile =
    PogFile(trace.sourceFile, trace.declarations.map(build))
