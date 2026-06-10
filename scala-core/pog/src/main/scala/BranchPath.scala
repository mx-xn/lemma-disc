import upickle.default.*

/** The branch path B(a) of paper §2.1 and the algorithm that recovers it from
 *  the proof tree.
 *
 *    "The branch path B(a) of a is the sequence of branch indices chosen at the
 *     branching ancestors of a, with an asterisk suffix `*` appended if a is
 *     itself branching. Tactics lying on a linear chain (no branching ancestors
 *     and not themselves branching) share the same branch path."
 *
 *  A *branching tactic* emits more than one residual obligation; a *branching
 *  ancestor* of a is an ancestor that is branching.
 *
 *  The `BranchPath` case class is the POG-output ADT (mirrors pog.schema.json,
 *  a bare JSON string array — see its ReadWriter in Types.scala);
 *  `BranchPath.compute` is its producer. `compute` is a pure function of the
 *  TREE SHAPE only: it reads `outputObligations.size`, `parentId`, and
 *  `childIds`; it never inspects obligation contents or the tactic summary.
 *
 *  `*` PLACEMENT — settled in design review (2026-06-01): the asterisk is MERGED
 *  INTO THE LAST INDEX (`["0*"]`, not `["0", "*"]`), matching pog.schema.json,
 *  the Types.scala comment, and the CLAUDE.md design-notes table. (The Step-5
 *  CLAUDE.md *snippet* appends it as a separate element — that is superseded.)
 *  A branching ancestor still contributes its PLAIN index to descendants; the
 *  `*` decorates only the branching node itself and never propagates downward.
 */
case class BranchPath(segments: List[String])

object BranchPath:

  /** Bare JSON array of strings on the wire (NOT wrapped in an object). */
  given ReadWriter[BranchPath] = readwriter[List[String]].bimap[BranchPath](
    _.segments,
    BranchPath(_)
  )

  private def isBranching(n: TacticNode): Boolean = n.outputObligations.size > 1

  /** Branch path for every node in one declaration, keyed by node id. */
  def compute(nodes: List[TacticNode]): Map[Int, BranchPath] =
    val byId = nodes.iterator.map(n => n.id -> n).toMap

    nodes.iterator.map { n =>
      // Branch indices at branching ancestors, collected leaf→root then
      // reversed to root→node order.
      val rev = collection.mutable.ListBuffer.empty[String]
      var cur = n
      while cur.parentId.isDefined do
        val parent = byId(cur.parentId.get)   // fail-fast if the tree is corrupt
        if isBranching(parent) then
          rev += parent.childIds.indexOf(cur.id).toString
        cur = parent
      val indices = rev.toList.reverse

      // Append `*` to the LAST index if this node itself branches; an empty
      // index sequence (e.g. a branching root) collapses to just ["*"].
      val segments =
        if !isBranching(n) then indices
        else indices match
          case Nil          => List("*")
          case init :+ last => init :+ (last + "*")

      n.id -> BranchPath(segments)
    }.toMap
