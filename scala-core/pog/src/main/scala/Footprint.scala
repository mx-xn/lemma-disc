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
 *
 *    • Introduced hypotheses (names in output but not in input Γ) are included
 *      in `modifies_hyps` and given self-map entries `h → {h}` in rho. Without
 *      this, tactics like `by_cases h` that only introduce new hyps have an empty
 *      `modifies` set, cannot be dependency-edge sources, and are excluded from
 *      vPre even when the fragment directly uses the introduced hypothesis.
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

    // M_hyps = input hyps dropped or retyped in SOME branch + newly introduced names.
    // M_goal = ∃i. gᵢ ≠ g.
    // Introduced names (in output but not in Γ) are included so that tactics like
    // `by_cases h` that only introduce new hyps can be dependency-edge sources —
    // otherwise they have modifies={} and are invisible to vPre.
    val (modifiesHyps, modifiesGoal) =
      node.outputObligations.foldLeft((Set.empty[String], false)) {
        case ((mh, mg), Obligation(hyps, gi)) =>
          val outNames = hyps.map(_.name).toSet
          val outType  = hyps.iterator.map(h => h.name -> h.`type`).toMap
          val modHere  = gammaNames.filter { n =>
            !outType.contains(n) || outType(n) != gammaType(n)
          }
          val introHere = outNames -- gammaNames
          (mh ++ modHere ++ introHere, mg || gi != goal)
      }

    // D = (directly_used ∩ names(Γ)) \ M_hyps — bounded to Γ, modified hyps removed.
    val uses = (node.summary.directlyUsed.toSet & gammaNames) -- modifiesHyps

    // ρᵢ = invert(πᵢ) ∪ {⊢ → {⊢}} ∪ {h → {h} for each introduced h}, co-indexed
    // with output branches. The self-maps for introduced names let forward propagation
    // carry them past the introducing tactic.  Leaves have no dependency_maps → Nil.
    val rho = node.summary.dependencyMaps.zip(node.outputObligations).map { (pi, outObl) =>
      val outNames  = outObl.hypotheses.map(_.name).toSet
      val selfMaps  = (outNames -- gammaNames).iterator.map(n => n -> Set(n)).toMap
      invert(pi).updated(Goal, Set(Goal)) ++ selfMaps
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
