// ─────────────────────────────────────────────────────────────────────────────
//  Phase B — Tactic Effects (paper §2.3.1, Def 4–6, name-level coarsened).
//
//  `deriveAll(node)` is the primary API: returns one Effect per output branch
//  (empty list for leaves). `derive(node, i)` is the per-branch building block.
//
//  `apply(effect, obl)` replays an Effect against an Obligation.
//
//  Derivation order within a single Effect (see CLAUDE.md §"Action ADT"):
//    Clears (input order) → type-change Modifies (input order) →
//    Introduces (output order) → goal Modify (last).
//  This ordering guarantees each Modify's `old` pre-condition is unambiguous
//  at the time it is processed by `apply`.
// ─────────────────────────────────────────────────────────────────────────────

object Effects:

  def derive(node: TacticNode, branchIndex: Int): Effect =
    require(
      branchIndex >= 0 && branchIndex < node.outputObligations.size,
      s"branch index $branchIndex out of range (node has ${node.outputObligations.size} outputs)"
    )
    val in  = node.inputObligation
    val out = node.outputObligations(branchIndex)

    val inNames   = in.hypotheses.map(_.name).toSet
    val outNames  = out.hypotheses.map(_.name).toSet
    val outByName = out.hypotheses.iterator.map(h => h.name -> h).toMap

    val clears = in.hypotheses
      .filter(h => !outNames.contains(h.name))
      .map(h => Clear(h.name))

    val typeModifies = in.hypotheses
      .filter(h => outByName.get(h.name).exists(_.`type` != h.`type`))
      .map(h => Modify(h.name, h.`type`, outByName(h.name).`type`))

    val introduces = out.hypotheses
      .filter(h => !inNames.contains(h.name))
      .map(Introduce(_))

    val goalModify = Option.when(in.goal != out.goal)(Modify("⊢", in.goal, out.goal)).toList

    Effect(clears ++ typeModifies ++ introduces ++ goalModify)

  def deriveAll(node: TacticNode): List[Effect] =
    node.outputObligations.indices.map(derive(node, _)).toList

  def apply(effect: Effect, obl: Obligation): Obligation =
    effect.actions.foldLeft(obl)(applyAction)

  private def applyAction(obl: Obligation, action: Action): Obligation = action match
    case Clear(name) =>
      val idx = obl.hypotheses.indexWhere(_.name == name)
      require(idx >= 0, s"Clear: hypothesis '$name' not found in Γ")
      Obligation(obl.hypotheses.patch(idx, Nil, 1), obl.goal)

    case Introduce(h) =>
      Obligation(obl.hypotheses :+ h, obl.goal)

    case Modify("⊢", old, snew) =>
      require(obl.goal == old, s"Modify goal: expected '$old', found '${obl.goal}'")
      Obligation(obl.hypotheses, snew)

    case Modify(prop, old, snew) =>
      val idx = obl.hypotheses.indexWhere(_.name == prop)
      require(idx >= 0, s"Modify: hypothesis '$prop' not found in Γ")
      val h = obl.hypotheses(idx)
      require(h.`type` == old, s"Modify '$prop': expected type '$old', found '${h.`type`}'")
      Obligation(obl.hypotheses.updated(idx, h.copy(`type` = snew)), obl.goal)
