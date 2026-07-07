import upickle.default.*
import upickle.implicits.key

object Serializer:

  // --- Wire types: mirror JSON exactly so upickle can auto-derive ---
  // Only plain case classes here (no sealed-trait members) so derives ReadWriter
  // generates untagged readers — no "$type" discriminator in the JSON.

  private case class WHypothesis(
    name: String,
    @key("type") typ: String
  ) derives ReadWriter

  private case class WObligation(
    hypotheses: List[WHypothesis],
    goal: String
  ) derives ReadWriter

  private case class WTacticSummary(
    @key("directly_used")   directlyUsed:     List[String],
    @key("dependency_maps") dependencyMaps:   List[Map[String, List[String]]]
  ) derives ReadWriter

  private case class RawFragment(
    @key("fragment_id")     fragmentId:      Int,
    @key("source_file")     sourceFile:      String,
    @key("decl_name")       declName:        String,
    @key("root_node_id")    rootNodeId:      Int,
    @key("root_obligation") rootObligation:  WObligation,
    nodes: List[ujson.Value]   // kept as raw JSON; dispatched manually on "kind"
  ) derives ReadWriter

  // --- Conversion: wire types → Types.scala ADTs ---

  private def toHyp(w: WHypothesis)    = Hypothesis(w.name, w.typ)
  private def toObl(w: WObligation)    = Obligation(w.hypotheses.map(toHyp), w.goal)
  private def toOblJ(j: ujson.Value)   = toObl(read[WObligation](j))
  private def toSumJ(j: ujson.Value)   =
    val w = read[WTacticSummary](j)
    TacticSummary(w.directlyUsed.toSet, w.dependencyMaps.map(_.view.mapValues(_.toSet).toMap))

  // Rebuild the recursive PartialTree from the flat node list.
  // Nodes are kept as ujson.Value to avoid upickle sealed-trait tagged-reader issues;
  // fields are extracted manually and dispatched on the inline "kind" field.
  private def toFragment(raw: RawFragment): Fragment =
    val nodeMap: Map[Int, ujson.Value] = raw.nodes.map(n => n("id").num.toInt -> n).toMap

    def reconstruct(id: Int): PartialTree =
      val json = nodeMap(id)
      val obl  = toOblJ(json("obligation"))
      json("kind").str match
        case "hole" =>
          Hole(json("hole_id").str, obl)
        case "leaf" =>
          Leaf(json("tactic_text").str, obl, toSumJ(json("summary")))
        case "node" =>
          val childIds = json("child_ids").arr.map(_.num.toInt).toList
          val outObls  = json("output_obligations").arr.map(toOblJ).toList
          val sum      = toSumJ(json("summary"))
          Node(json("tactic_text").str, obl, outObls, sum, childIds.map(reconstruct))
        case k =>
          throw Exception(s"Unknown node kind: $k")

    Fragment(raw.fragmentId, raw.sourceFile, raw.declName,
             toObl(raw.rootObligation), reconstruct(raw.rootNodeId))

  // --- Output serialization: LemmaObj → lemmas.schema.json ---

  private given Writer[LemmaObj] = writer[ujson.Value].comap { l =>
    ujson.Obj(
      "fragment_id" -> l.fragmentId,
      "source_file" -> l.sourceFile,
      "decl_name"   -> l.declName,
      "scope_vars"  -> l.scopeVars,
      "premises"    -> l.premises,
      "body"        -> l.body,
      "conclusion"  -> l.conclusion,
      "statement"   -> l.statement
    )
  }

  // --- Entry point ---

  def main(args: Array[String]): Unit =
    val inputJson  = if args.nonEmpty then scala.io.Source.fromFile(args(0)).mkString
                     else scala.io.Source.stdin.mkString
    val parsed     = ujson.read(inputJson)
    val fragments  = parsed("fragments").arr
                       .map(f => toFragment(read[RawFragment](f))).toList
    val lemmas     = fragments.map(LemmaConstructor.constructLemma)
    val outputJson = ujson.Obj("lemmas" -> ujson.Arr(lemmas.map(writeJs[LemmaObj])*))
    val rendered   = outputJson.render(indent = 2)
    if args.length >= 2 then
      val pw = java.io.PrintWriter(args(1))
      pw.print(rendered)
      pw.close()
    else println(rendered)
