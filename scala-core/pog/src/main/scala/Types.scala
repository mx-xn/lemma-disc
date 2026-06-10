import upickle.default.*
import upickle.implicits.key

// ─────────────────────────────────────────────────────────────────────────────
//  Phase-2 ADTs + upickle ReadWriter instances
//
//  • PART A  — trace-input ADTs:  mirror schemas/trace.schema.json
//  • PART B  — POG-output ADTs:   mirror schemas/pog.schema.json
//
//  All `ReadWriter`s are derived automatically except where the wire format
//  deviates from the case-class field shape: `Option[Int]`, `EdgeKind`,
//  `BranchPath`, and `PogNode` (see the comments at each declaration).
// ─────────────────────────────────────────────────────────────────────────────


//  Custom `Option[Int]` encoding (null ↔ None) — declared before any case
//  class that derives a ReadWriter mentioning `Option[Int]`.
//  upickle's default encodes Option as a 0/1-element array, which does NOT
//  match phase 1's "parent_id : integer | null" JSON.

given ReadWriter[Option[Int]] = readwriter[ujson.Value].bimap[Option[Int]](
  {
    case Some(n) => ujson.Num(n.toDouble)
    case None    => ujson.Null
  },
  {
    case ujson.Null => None
    case v          => Some(v.num.toInt)
  }
)


// ═══════════════════════════════════════════════════════════════════════════
//  PART A — trace-input ADTs  (mirror trace.schema.json)
// ═══════════════════════════════════════════════════════════════════════════

case class Hypothesis(
  name:                 String,
  @key("type") `type`:  String
) derives ReadWriter

case class Obligation(
  hypotheses:  List[Hypothesis],
  goal:        String
) derives ReadWriter

case class TacticSummary(
  @key("directly_used")   directlyUsed:   List[String],
  @key("dependency_maps") dependencyMaps: List[Map[String, List[String]]]
) derives ReadWriter

case class TacticNode(
  id:                                              Int,
  @key("tactic_text")        tacticText:           String,
  @key("input_obligation")   inputObligation:      Obligation,
  @key("output_obligations") outputObligations:    List[Obligation],
  summary:                                         TacticSummary,
  @key("parent_id")          parentId:             Option[Int],
  @key("child_ids")          childIds:             List[Int]
) derives ReadWriter

case class Declaration(
  name:                                       String,
  statement:                                  String,
  @key("root_tactic_id") rootTacticId:        Int,
  @key("tactic_nodes")   tacticNodes:         List[TacticNode]
) derives ReadWriter

case class LeanProofTrace(
  @key("source_file") sourceFile: String,
  declarations:                   List[Declaration]
) derives ReadWriter


// ═══════════════════════════════════════════════════════════════════════════
//  PART B — POG-output ADTs  (mirror pog.schema.json)
// ═══════════════════════════════════════════════════════════════════════════

//  Footprint (the POG-output ADT) and its `compute` algorithm are co-located
//  in Footprint.scala — the case class and its companion object must share a
//  file, and keeping the data type beside the computation that produces it
//  follows the "one file per major definition" principle.


//  BranchPath (the POG-output ADT) and its `compute` algorithm are co-located
//  in BranchPath.scala — the case class and its companion object must share a
//  file (same arrangement as Footprint). On the wire it is a bare JSON array of
//  strings (NOT wrapped in an object); see its ReadWriter there.


//  EdgeKind: bare JSON string ("modify" | "use") on the wire. Override
//  upickle's default sealed-trait encoding to avoid the {"$type": ...}
//  discriminator.
sealed trait EdgeKind
case object ModifyEdge extends EdgeKind
case object UseEdge    extends EdgeKind

given ReadWriter[EdgeKind] = readwriter[String].bimap[EdgeKind](
  {
    case ModifyEdge => "modify"
    case UseEdge    => "use"
  },
  {
    case "modify" => ModifyEdge
    case "use"    => UseEdge
    case s        => throw IllegalArgumentException(s"Unknown EdgeKind: $s")
  }
)


case class PogEdge(
  from: Int,
  to:   Int,
  kind: EdgeKind
) derives ReadWriter


//  PogNode: the wire format is FLAT — the TacticNode fields and the POG-
//  specific fields (footprint, branch_path) sit at the SAME level, with no
//  "node" wrapper. The case class composes a TacticNode for in-Scala
//  ergonomics; the custom ReadWriter inlines/extracts the TacticNode keys.
case class PogNode(
  node:        TacticNode,
  footprint:   Footprint,
  branchPath:  BranchPath
)

given ReadWriter[PogNode] = readwriter[ujson.Value].bimap[PogNode](
  pn => {
    val v = writeJs(pn.node)           // ujson.Obj of TacticNode fields
    v.obj("footprint")   = writeJs(pn.footprint)
    v.obj("branch_path") = writeJs(pn.branchPath)
    v
  },
  j => {
    val all     = j.obj
    val tnOnly  = ujson.Obj()
    all.foreach { case (k, v) =>
      if k != "footprint" && k != "branch_path" then tnOnly.obj.update(k, v)
    }
    PogNode(
      node       = read[TacticNode](tnOnly),
      footprint  = read[Footprint](all("footprint")),
      branchPath = read[BranchPath](all("branch_path"))
    )
  }
)


case class ProofOrderingGraph(
  @key("decl_name")       declName:       String,
  statement:                              String,
  @key("root_tactic_id")  rootTacticId:   Int,
  @key("root_obligation") rootObligation: Obligation,
  nodes:                                  List[PogNode],
  edges:                                  List[PogEdge]
) derives ReadWriter

case class PogFile(
  @key("source_file") sourceFile: String,
  pogs:                           List[ProofOrderingGraph]
) derives ReadWriter
