import upickle.default.*
import upickle.implicits.key

/** The coarsened tactic footprint Φ(a, Γ, g) = (D, M, µ, ρ) (paper Definition 2,
 *  §2.1) and the algorithm that recovers it from phase-1 data.
 *
 *  The `Footprint` case class is the POG-output ADT (mirrors the `Footprint`
 *  definition in pog.schema.json); `Footprint.compute` is its smart producer.
 *  They live together because a case class and its companion object must share
 *  a source file.
 *
 *  Positions µ are dropped (name-level coarsening — see FUTURE.md).
 *
 *  `compute` is a pure function of a single node's input/output obligations and
 *  summary; it never reads the tree (`parent_id` / `child_ids`).
 *
 *  Recovery rules (see CLAUDE.md §"Recovering the Footprint"), with the two
 *  corrections settled in design review — both load-bearing, do not revert:
 *
 *    • rho INVERTS phase-1's `dependency_maps`. Those are oriented
 *      output-name → input-names (backward); the schema and the Step-6 forward
 *      propagation need input-name → {output-names}, so we transpose.
 *
 *    • rho's goal entry "⊢" → {"⊢"} is UNCONDITIONAL on every non-leaf branch.
 *      Goal PROPAGATION (always identity) is distinct from goal MODIFICATION
 *      (`modifies_goal`); gating the entry on modification would break
 *      goal-threading composition through intermediate tactics.
 */
case class Footprint(
  uses:                                Set[String],
  @key("modifies_hyps") modifiesHyps:  Set[String],
  @key("modifies_goal") modifiesGoal:  Boolean,
  rho:                                 List[Map[String, Set[String]]]
) derives ReadWriter

object Footprint:

  /** Reserved token denoting the goal slot inside ρ (the goal has no hyp name). */
  private val Goal = "⊢"

  def compute(node: TacticNode): Footprint =
    val gamma      = node.inputObligation.hypotheses
    val goal       = node.inputObligation.goal
    val gammaNames = gamma.map(_.name).toSet
    val gammaType  = gamma.iterator.map(h => h.name -> h.`type`).toMap

    // M_hyps = input hyps dropped or retyped in SOME branch; M_goal = ∃i. gᵢ ≠ g.
    // (Introductions never count — paper Def 2: M ⊆ {g} ∪ Γ.)
    val (modifiesHyps, modifiesGoal) =
      node.outputObligations.foldLeft((Set.empty[String], false)) {
        case ((mh, mg), Obligation(hyps, gi)) =>
          val outType = hyps.iterator.map(h => h.name -> h.`type`).toMap
          val modHere = gammaNames.filter { n =>
            !outType.contains(n) || outType(n) != gammaType(n)
          }
          (mh ++ modHere, mg || gi != goal)
      }

    // D = (directly_used ∩ names(Γ)) \ M_hyps — bounded to Γ, modified hyps removed.
    val uses = (node.summary.directlyUsed.toSet & gammaNames) -- modifiesHyps

    // ρᵢ = invert(πᵢ) ∪ {⊢ → {⊢}}, co-indexed with output branches.
    // Leaves have no dependency_maps, hence rho = Nil.
    val rho = node.summary.dependencyMaps.map { pi =>
      invert(pi).updated(Goal, Set(Goal))
    }

    Footprint(uses, modifiesHyps, modifiesGoal, rho)

  /** Transpose a phase-1 dependency map (output-name → input-names) into the
   *  forward name map (input-name → {output-names it propagates to}). */
  private def invert(pi: Map[String, List[String]]): Map[String, Set[String]] =
    pi.iterator
      .flatMap { case (out, ins) => ins.iterator.map(in => in -> out) }
      .toList
      .groupBy(_._1)
      .view.mapValues(_.iterator.map(_._2).toSet).toMap
