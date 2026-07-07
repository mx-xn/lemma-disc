// ─────────────────────────────────────────────────────────────────────────────
//  Phase B helper — original proof order restricted to a vertex set (§2.3.1).
//
//  `linearize(ids, pog)` returns the elements of `ids` in DFS preorder of the
//  proof tree (the order the original proof executes its tactics). The
//  Reconstructor calls this twice: once for V_pre (to reach (Γ_F, g_F)) and
//  once for V_H (to label every node and hole in the fragment).
//
//  Correctness: the original proof respects every edge in E, so restricting
//  its order to any subset S respects every edge internal to S — making this
//  the canonical linearization of the induced subgraph on S (Theorem 1).
// ─────────────────────────────────────────────────────────────────────────────

object Linearizer:

  def linearize(ids: Set[Int], pog: ProofOrderingGraph): List[Int] =
    if ids.isEmpty then return Nil
    val byId = pog.nodes.iterator.map(p => p.node.id -> p.node).toMap
    ids.foreach(id => require(byId.contains(id), s"Node $id not found in POG"))
    val result = List.newBuilder[Int]
    def dfs(id: Int): Unit =
      if ids.contains(id) then result += id
      byId(id).childIds.foreach(dfs)
    dfs(pog.rootTacticId)
    val out = result.result()
    // Some proof trees are forests (LeanDojo extracts disconnected subtrees for
    // inline `have ... := by ...` bodies). Fragments rooted in those subtrees
    // cannot be replayed correctly from pog.rootObligation, so we reject them.
    require(out.size == ids.size,
      s"${ids.size - out.size} node(s) unreachable from proof root: ${(ids -- out.toSet).take(5)}")
    out
