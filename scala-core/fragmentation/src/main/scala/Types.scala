import upickle.default.*
import upickle.implicits.key

// ─────────────────────────────────────────────────────────────────────────────
//  Phase-3 ADTs.
//
//  POG-input types (Obligation, Hypothesis, TacticSummary, PogNode, PogFile, …)
//  are REUSED from the `pog` module — it is a compile dependency and its ADTs
//  live in the default package, so they are already on the classpath here. We
//  only define the types phase 3 introduces:
//
//   • PART A — decomposition (§2.3):       Decomposition, Candidate, report, heuristic
//   • PART B — tactic effects (§2.3.1):    Action, Effect
//   • OUTPUT — fragment tree (§1, Lem(·)): TreeNode, Fragment, FragmentList
//
//  Only the OUTPUT types cross a phase boundary, so only they carry
//  `ReadWriter`s — they must serialize to `schemas/segments.schema.json`
//  exactly, since phase 4 (`support`) parses that shape by hand.
//
//  NOTE: every member here is a `class`/`trait`/`object` — there are NO
//  top-level `given`/`def`/`type` declarations. Those would compile to a
//  synthetic `Types$package` object that collides with the `pog` module's
//  identically-named one (both files are `Types.scala` in the default package),
//  hiding pog's givens at runtime. So the `TreeNode` ReadWriter and the
//  heuristic alias live in companion objects instead.
// ─────────────────────────────────────────────────────────────────────────────


// ═══════════════════════════════════════════════════════════════════════════
//  PART A — Phase-A decomposition (§2.3)
// ═══════════════════════════════════════════════════════════════════════════

/** A POG decomposition `(H_pre, H, H_post)`: the fragment's tactics `vH` (a
 *  convex + branch-closed vertex set of `G_T`), the tactics that must replay
 *  before it `vPre` (the dependency-ancestor closure of `vH` within `V\vH`),
 *  and everything else `vPost`. Vertices are POG node IDs. */
case class Decomposition(vH: Set[Int], vPre: Set[Int], vPost: Set[Int])

/** A candidate fragment emitted by Phase-A enumeration: a single-rooted,
 *  convex + branch-closed vertex set `V_H`, with each member tagged by its
 *  subgoal count `mₙ` (output-obligation count from the trace, NOT POG
 *  out-degree). Carrying `mₙ` inline keeps the [[Candidate.Heuristic]] purely
 *  structural — it needs neither obligations nor POG edges. */
case class Candidate(root: Int, subgoalCounts: Map[Int, Int]):
  def vH:   Set[Int] = subgoalCounts.keySet
  def size: Int      = subgoalCounts.size

object Candidate:
  /** A predicate selecting which candidate shapes become lemmas. The default
   *  rule rejects only branching-with-a-hole fragments; pass `_ => true` to
   *  disable filtering. Applied lazily during enumeration, before Phase B. */
  type Heuristic = Candidate => Boolean

/** Tally of an enumeration run, logged so a timed-out (capped) run is never
 *  mistaken for an exhaustive one. */
case class EnumerationReport(examined: Int, accepted: Int, skipped: Int, timedOut: Boolean)


// ═══════════════════════════════════════════════════════════════════════════
//  PART B — tactic effects (§2.3.1, Def 4–6)
// ═══════════════════════════════════════════════════════════════════════════

/** A primitive edit a tactic makes to an obligation on one output branch.
 *  Under phase-2 name-level coarsening these are literal (no position/template
 *  machinery): the goal is replaced wholesale and hypotheses are added/removed
 *  by name (a type change is a `Clear` followed by an `Introduce`). */
sealed trait Action
case class Clear(name: String)                           extends Action  // hypothesis removed from Γ
case class Introduce(hyp: Hypothesis)                    extends Action  // hypothesis added to Γ
case class Modify(prop: String, old: String, snew: String) extends Action
  // prop = "⊢"       → replace goal     (old = expected current goal,  for fail-fast check)
  // prop = hyp name  → replace hyp type (old = expected current type,  for fail-fast check)

/** The full diff a tactic applies to an obligation on one branch: an ordered
 *  bundle of [[Action]]s, replayed by `Effects.apply`. */
case class Effect(actions: List[Action])


// ═══════════════════════════════════════════════════════════════════════════
//  OUTPUT — fragment tree (mirror segments.schema.json)
// ═══════════════════════════════════════════════════════════════════════════

/** One node of a fragment's proof tree. The flat node list encodes the tree via
 *  `parentId`/`childIds`; the three cases are discriminated on the wire by a
 *  `"kind"` field (`hole` | `leaf` | `node`). */
sealed trait TreeNode:
  def id:         Int
  def parentId:   Option[Int]
  def childIds:   List[Int]
  def obligation: Obligation

/** A residual obligation `(Γℓ, gℓ)` left open where the selected fragment stops
 *  and the original proof continued. Always childless. */
case class HoleNode(
  id:         Int,
  holeId:     String,
  parentId:   Option[Int],
  obligation: Obligation
) extends TreeNode:
  def childIds: List[Int] = Nil

/** An H-node that produced no residuals — a tactic closing its branch to an
 *  original leaf. Always childless. */
case class LeafNode(
  id:         Int,
  tacticText: String,
  parentId:   Option[Int],
  obligation: Obligation,
  summary:    TacticSummary
) extends TreeNode:
  def childIds: List[Int] = Nil

/** An internal H-node: a tactic with one slot per output obligation, each
 *  filled by a child (a sub-proof in `V_H`) or a hole. `childIds` is co-indexed
 *  with `outputObligations`. */
case class CompositeNode(
  id:                Int,
  tacticText:        String,
  parentId:          Option[Int],
  childIds:          List[Int],
  obligation:        Obligation,
  outputObligations: List[Obligation],
  summary:           TacticSummary
) extends TreeNode

object TreeNode:
  //  Encoded with an explicit `"kind"` tag matching the schema's `const`
  //  discriminator — NOT upickle's default `{"$type": …}` — and Option[Int]
  //  parents as `int | null`. Lives in the companion so derivation on Fragment
  //  finds it without a top-level given (see the file header note).
  private def parentToJson(p: Option[Int]): ujson.Value =
    p.fold(ujson.Null)(i => ujson.Num(i.toDouble))

  private def parentFromJson(j: ujson.Value): Option[Int] = j match
    case ujson.Null => None
    case v          => Some(v.num.toInt)

  private def idsToJson(ids: List[Int]): ujson.Value =
    ujson.Arr(ids.map(i => ujson.Num(i.toDouble))*)

  given ReadWriter[TreeNode] = readwriter[ujson.Value].bimap[TreeNode](
    {
      case n: HoleNode => ujson.Obj(
        "id"         -> ujson.Num(n.id.toDouble),
        "kind"       -> ujson.Str("hole"),
        "hole_id"    -> ujson.Str(n.holeId),
        "parent_id"  -> parentToJson(n.parentId),
        "child_ids"  -> ujson.Arr(),
        "obligation" -> writeJs(n.obligation)
      )
      case n: LeafNode => ujson.Obj(
        "id"          -> ujson.Num(n.id.toDouble),
        "kind"        -> ujson.Str("leaf"),
        "tactic_text" -> ujson.Str(n.tacticText),
        "parent_id"   -> parentToJson(n.parentId),
        "child_ids"   -> ujson.Arr(),
        "obligation"  -> writeJs(n.obligation),
        "summary"     -> writeJs(n.summary)
      )
      case n: CompositeNode => ujson.Obj(
        "id"                 -> ujson.Num(n.id.toDouble),
        "kind"               -> ujson.Str("node"),
        "tactic_text"        -> ujson.Str(n.tacticText),
        "parent_id"          -> parentToJson(n.parentId),
        "child_ids"          -> idsToJson(n.childIds),
        "obligation"         -> writeJs(n.obligation),
        "output_obligations" -> ujson.Arr(n.outputObligations.map(writeJs(_))*),
        "summary"            -> writeJs(n.summary)
      )
    },
    j =>
      val id  = j("id").num.toInt
      val obl = read[Obligation](j("obligation"))
      j("kind").str match
        case "hole" =>
          HoleNode(id, j("hole_id").str, parentFromJson(j("parent_id")), obl)
        case "leaf" =>
          LeafNode(id, j("tactic_text").str, parentFromJson(j("parent_id")), obl,
                   read[TacticSummary](j("summary")))
        case "node" =>
          CompositeNode(
            id, j("tactic_text").str, parentFromJson(j("parent_id")),
            j("child_ids").arr.map(_.num.toInt).toList, obl,
            j("output_obligations").arr.map(read[Obligation](_)).toList,
            read[TacticSummary](j("summary")))
        case k =>
          throw IllegalArgumentException(s"Unknown TreeNode kind: $k")
  )

/** One candidate lemma: a fragment rooted at obligation `(ΓF, gF)`, with its
 *  proof tree flattened into `nodes` (tree shape via parent/child IDs). */
case class Fragment(
  @key("fragment_id")     fragmentId:     Int,
  @key("source_file")     sourceFile:     String,
  @key("decl_name")       declName:       String,
  @key("root_node_id")    rootNodeId:     Int,
  @key("root_obligation") rootObligation: Obligation,
  nodes:                                  List[TreeNode]
) derives ReadWriter

/** Phase-3 output: the flat list of all extracted fragments. */
case class FragmentList(fragments: List[Fragment]) derives ReadWriter
