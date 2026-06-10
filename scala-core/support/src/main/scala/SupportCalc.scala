object SupportCalc:
  def computeSupport(tree: PartialTree): Set[String] = tree match
    case Hole(_, _) =>
      Set.empty

    case Leaf(_, _, summary) =>
      summary.directlyUsed

    case Node(_, _, _, summary, children) =>
      val pulled = children.zipWithIndex.flatMap { case (child, i) =>
        val ai = computeSupport(child)
        val pi = summary.dependencyMaps(i)
        ai.flatMap(h => pi.getOrElse(h, Set.empty))
      }.toSet
      summary.directlyUsed ++ pulled
