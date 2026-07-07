case class Hypothesis(name: String, typ: String)
case class Obligation(hypotheses: List[Hypothesis], goal: String)
case class TacticSummary(directlyUsed: Set[String], dependencyMaps: List[Map[String, Set[String]]])

sealed trait PartialTree
case class Hole(holeId: String, obligation: Obligation) extends PartialTree
case class Leaf(tacticText: String, obligation: Obligation, summary: TacticSummary) extends PartialTree
case class Node(
  tacticText: String,
  obligation: Obligation,
  outputObligations: List[Obligation],
  summary: TacticSummary,
  children: List[PartialTree]
) extends PartialTree

case class Fragment(
  fragmentId: Int,
  sourceFile: String,
  declName: String,
  rootObligation: Obligation,
  tree: PartialTree
)

case class LemmaObj(
  fragmentId: Int,
  sourceFile: String,
  declName: String,
  scopeVars: List[String],
  premises: List[String],
  body: String,
  conclusion: String,
  statement: String
)
