// ─────────────────────────────────────────────────────────────────────────────
//  Phase B — Obligation Reconstruction (paper §2.3.1).
//
//  `reconstruct(decomp, pog)` labels every V_H node with the obligation its
//  tactic runs at and identifies every hole (open goal leaving the fragment).
//
//  Two passes:
//    1. Replay V_pre in DFS-preorder from pog.rootObligation → (Γ_F, g_F).
//    2. Replay V_H in DFS-preorder from (Γ_F, g_F) → per-node annotations + holes.
//
//  NodeAnnotation/HoleAnnotation/Reconstruction live here (not in Types.scala) to
//  avoid the top-level-declaration package collision — see Types.scala header note.
// ─────────────────────────────────────────────────────────────────────────────

case class NodeAnnotation(inputObligation: Obligation, outputObligations: List[Obligation])
case class HoleAnnotation(parentNodeId: Int, branchIndex: Int, obligation: Obligation)
case class Reconstruction(
  rootObligation:  Obligation,
  nodeAnnotations: Map[Int, NodeAnnotation],
  holes:           List[HoleAnnotation]
)

object Reconstructor:

  def reconstruct(decomp: Decomposition, pog: ProofOrderingGraph): Reconstruction =
    require(decomp.vH.nonEmpty, "V_H must be non-empty")
    val byId = pog.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap
    decomp.vH.foreach(id => require(byId.contains(id), s"V_H node $id not found in POG"))

    val fragRoot = Decomposer.fragmentRoot(decomp.vH, pog)
      .getOrElse(throw IllegalArgumentException("V_H has no unique fragment root"))

    val rootObligation              = replayPreSet(decomp.vPre, decomp.vH, fragRoot, byId, pog)
    val (annotations, holes)        = replayVH(decomp.vH, fragRoot, rootObligation, byId, pog)
    Reconstruction(rootObligation, annotations, holes)


  private def replayPreSet(
    vPre:     Set[Int],
    vH:       Set[Int],
    fragRoot: Int,
    byId:     Map[Int, TacticNode],
    pog:      ProofOrderingGraph
  ): Obligation =
    Linearizer.linearize(vPre, pog).foldLeft(pog.rootObligation) { (obl, nodeId) =>
      val node      = byId(nodeId)
      // Normal case: V_pre node is a tree-ancestor of fragRoot — pick the branch
      // whose subtree contains fragRoot.
      // Reordered pre-set: V_pre node is a tree-descendant of fragRoot. Admissibility
      // guarantees it can legitimately run before V_H, so apply its effect at the branch
      // whose subtree leads toward V_H.
      val branchIdx =
        val toward = node.childIds.indexWhere(c => isInSubtree(fragRoot, c, byId))
        if toward >= 0 then toward
        else node.childIds.indexWhere(c => subtreeHasVH(c, byId, vH))
      if branchIdx < 0 then obl
      else applyWithOrdering(node, branchIdx, obl)
    }


  private def replayVH(
    vH:       Set[Int],
    fragRoot: Int,
    rootObl:  Obligation,
    byId:     Map[Int, TacticNode],
    pog:      ProofOrderingGraph
  ): (Map[Int, NodeAnnotation], List[HoleAnnotation]) =
    val annotations = scala.collection.mutable.Map.empty[Int, NodeAnnotation]
    val holes       = List.newBuilder[HoleAnnotation]

    for nodeId <- Linearizer.linearize(vH, pog) do
      val node     = byId(nodeId)
      val inputObl =
        if nodeId == fragRoot then rootObl
        else
          val (parentId, branchIdx) = nearestVHAncestor(nodeId, byId, vH)
          annotations(parentId).outputObligations(branchIdx)
      val outputObls = node.outputObligations.indices.toList.map { i =>
        applyWithOrdering(node, i, inputObl)
      }
      annotations(nodeId) = NodeAnnotation(inputObl, outputObls)
      for (childId, branchIdx) <- node.childIds.zipWithIndex do
        if !subtreeHasVH(childId, byId, vH) then
          holes += HoleAnnotation(nodeId, branchIdx, outputObls(branchIdx))

    (annotations.toMap, holes.result())


  // Apply the effect of `node` at `branchIdx` to `currentObl`, then prefer the
  // recorded output's hypothesis ordering when the hypothesis set (names × types)
  // and goal are identical to the computed result. When sets differ, V_post effects
  // are in play and the computed result is semantically authoritative.
  // This satisfies [R5] exactly: Effects.apply gives the correct set; the recorded
  // output gives the canonical Lean ordering that Effects cannot reproduce (Introduce
  // always appends to end, but Lean may insert hypotheses mid-context).
  private def applyWithOrdering(node: TacticNode, branchIdx: Int, currentObl: Obligation): Obligation =
    val applied  = Effects.apply(Effects.derive(node, branchIdx), currentObl)
    val recorded = node.outputObligations(branchIdx)
    if applied.goal == recorded.goal &&
       applied.hypotheses.map(h => (h.name, h.`type`)).toSet ==
       recorded.hypotheses.map(h => (h.name, h.`type`)).toSet
    then recorded
    else applied

  private def isInSubtree(target: Int, root: Int, byId: Map[Int, TacticNode]): Boolean =
    target == root || byId(root).childIds.exists(c => isInSubtree(target, c, byId))

  private def subtreeHasVH(x: Int, byId: Map[Int, TacticNode], vH: Set[Int]): Boolean =
    vH.contains(x) || byId(x).childIds.exists(c => subtreeHasVH(c, byId, vH))

  private def nearestVHAncestor(
    id:   Int,
    byId: Map[Int, TacticNode],
    vH:   Set[Int]
  ): (Int, Int) =
    var cur = byId(id).parentId
    while cur.isDefined && !vH.contains(cur.get) do cur = byId(cur.get).parentId
    val parentId  = cur.getOrElse(throw IllegalStateException(s"No V_H ancestor for node $id"))
    val branchIdx = byId(parentId).childIds.indexWhere(c => c == id || isInSubtree(id, c, byId))
    (parentId, branchIdx)
