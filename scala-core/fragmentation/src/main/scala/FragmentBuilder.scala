// ─────────────────────────────────────────────────────────────────────────────
//  Step 8 — Fragment assembly (paper §2.3.1).
//
//  `build` takes a Decomposition and its POG, runs Phase B (Reconstructor) to
//  obtain per-node and per-hole obligations, then assembles the flat Fragment:
//
//    • Each V_H node with mₙ = 0 → LeafNode.
//    • Each V_H node with mₙ ≥ 1 → CompositeNode; its childIds are co-indexed
//      with outputObligations: slot i is the nearest V_H descendant in that
//      branch's subtree (re-parented relative to T), or a fresh HoleNode if
//      no V_H node appears in that subtree.
//    • Hole integer ids start at vH.max + 1 to avoid aliasing V_H ids.
// ─────────────────────────────────────────────────────────────────────────────

object FragmentBuilder:

  def build(
    decomp:     Decomposition,
    pog:        ProofOrderingGraph,
    sourceFile: String,
    fragmentId: Int
  ): Fragment =
    val recon    = Reconstructor.reconstruct(decomp, pog)
    val byId     = pog.nodes.iterator.map(pn => pn.node.id -> pn.node).toMap
    val fragRoot = Decomposer.fragmentRoot(decomp.vH, pog).get

    // (fragmentParentId, slotIndex) for every non-root V_H node.
    val parentSlot: Map[Int, (Int, Int)] =
      (decomp.vH - fragRoot).iterator
        .map(id => id -> nearestVHAncestorSlot(id, decomp.vH, byId))
        .toMap

    // (parentId, slot) → V_H child id; covers only filled slots.
    val vhChildAt: Map[(Int, Int), Int] =
      parentSlot.iterator.map { case (id, ps) => ps -> id }.toMap

    // Fresh HoleNodes in recon.holes order for determinism.
    val baseHoleId = decomp.vH.max + 1
    val holeEntries: List[((Int, Int), HoleNode)] =
      recon.holes.zipWithIndex.map { case (ann, i) =>
        (ann.parentNodeId, ann.branchIndex) ->
          HoleNode(baseHoleId + i, s"hole_$i", Some(ann.parentNodeId), ann.obligation)
      }
    val holeAt:   Map[(Int, Int), HoleNode] = holeEntries.toMap
    val holeList: List[HoleNode]            = holeEntries.map(_._2)

    val tacticNodes: List[TreeNode] =
      Linearizer.linearize(decomp.vH, pog).map { id =>
        val node   = byId(id)
        val ann    = recon.nodeAnnotations(id)
        val parent = parentSlot.get(id).map(_._1)
        if node.outputObligations.isEmpty then
          LeafNode(id, node.tacticText, parent, ann.inputObligation, node.summary)
        else
          val childIds = node.outputObligations.indices.toList.map { slot =>
            vhChildAt.getOrElse((id, slot), holeAt((id, slot)).id)
          }
          CompositeNode(id, node.tacticText, parent, childIds,
                        ann.inputObligation, ann.outputObligations, node.summary)
      }

    Fragment(fragmentId, sourceFile, pog.declName, fragRoot,
             recon.rootObligation, tacticNodes ++ holeList)


  // Walk up the original proof tree from `id` until reaching a V_H node;
  // return that ancestor's id and which of its output slots leads toward `id`.
  private def nearestVHAncestorSlot(
    id:   Int,
    vH:   Set[Int],
    byId: Map[Int, TacticNode]
  ): (Int, Int) =
    var cur = byId(id).parentId
    while cur.isDefined && !vH.contains(cur.get) do cur = byId(cur.get).parentId
    val parentId  = cur.getOrElse(throw IllegalStateException(s"No V_H ancestor for node $id"))
    val slotIndex = byId(parentId).childIds.indexWhere(c => c == id || isInSubtree(id, c, byId))
    (parentId, slotIndex)

  private def isInSubtree(target: Int, root: Int, byId: Map[Int, TacticNode]): Boolean =
    target == root || byId(root).childIds.exists(c => isInSubtree(target, c, byId))
