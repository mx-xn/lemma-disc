object LemmaConstructor:
  // Lem(·) from §1. None = ⊤.
  def computeLem(tree: PartialTree): Option[String] = tree match
    // Lem(•ℓ[(Γℓ,gℓ)]) = gℓ
    case Hole(_, obl) =>
      Some(obl.goal)

    // Lem(a[(Γ,g)]) = ⊤  (leaf, no subgoals)
    case Leaf(_, _, _) =>
      None

    // Lem(a[(Γ,g)]⟨Υ₁,…,Υₘ⟩) = ∧_{i: Lem(Υᵢ)≠⊤} ((∧(Γᵢ\Γ)) → Lem(Υᵢ))
    //
    // The paper's `(∧(Γᵢ\Γ)) → …` becomes, in concrete Lean syntax, a chain of
    // individual binders: `(h1 : T1) → (h2 : T2) → …`. Joining the binders with `∧`
    // would be a type error — `∧` connects propositions, not name : type pairs.
    case Node(_, obl, outputObls, _, children) =>
      val parentNames = obl.hypotheses.map(_.name).toSet         // Γ (parent context)
      val parts = children.zipWithIndex.flatMap { case (child, i) =>
        computeLem(child).map { lemStr =>                         // skip ⊤ children
          val newHyps  = outputObls(i).hypotheses.filterNot(h => parentNames(h.name)) // Γᵢ \ Γ
          val binders  = newHyps.map(h => s"(${h.name} : ${h.typ})")
          if binders.isEmpty then lemStr                          // no new hyps → implication vanishes
          else binders.mkString(" → ") + " → " + lemStr
        }
      }
      if parts.isEmpty then None
      else if parts.length == 1 then Some(parts.head)
      // When conjoining multiple parts, wrap any implication to prevent ∧ from
      // stealing its right-hand side (∧ has higher precedence than → in Lean 4).
      else Some(parts.map(p => if p.contains("→") then s"($p)" else p).mkString(" ∧ "))

  // Universe-polymorphic type binders like `α : Type u_1` are dropped from
  // both premises and scope_vars — Lean auto-binds free type variables implicitly.
  private val typeUniversePattern = """^Type u_\w+$""".r
  private def isTypeUniverse(typ: String): Boolean =
    typeUniversePattern.matches(typ.trim)

  // Lean identifier characters (handles unicode letters, digits, apostrophe).
  private val identRe = """[A-Za-z_-￿][A-Za-z0-9_'-￿]*""".r
  private def freeIdents(s: String): Set[String] = identRe.findAllIn(s).toSet

  // Transitive closure of "name is reachable": start from identifiers mentioned in
  // seed strings, then repeatedly expand through hypothesis types whose names are
  // already reachable, until fixpoint.
  private def reachableNames(hyps: List[Hypothesis], seeds: Set[String]): Set[String] =
    val nameToTypeIdents = hyps.map(h => h.name -> freeIdents(h.typ)).toMap
    var needed = seeds
    var changed = true
    while changed do
      val before = needed.size
      for h <- hyps if needed(h.name) do needed ++= nameToTypeIdents(h.name)
      changed = needed.size != before
    needed

  // Assembles the full lemma: scope vars + minimal-support premises + Lem(Υ) → gF,
  // rendered with Lean binder syntax via `StatementFormatter`.
  def constructLemma(fragment: Fragment): LemmaObj =
    val support = SupportCalc.computeSupport(fragment.tree)       // A ⊆ ΓF (minimal support)
    val (supportHyps, nonSupportHyps) =
      fragment.rootObligation.hypotheses.partition(h => support(h.name))

    // Seed: identifiers appearing in the body, conclusion, and premise types.
    val seeds = freeIdents(fragment.rootObligation.goal) ++
                supportHyps.flatMap(h => freeIdents(h.typ))
    // (body is computed below, but for non-hole trees it's "True" and adds nothing.)
    val body       = computeLem(fragment.tree).getOrElse("True")
    val seeds2     = seeds ++ freeIdents(body)
    val reachable  = reachableNames(nonSupportHyps, seeds2)

    val scopeVars = nonSupportHyps
                      .filterNot(h => isTypeUniverse(h.typ))
                      // Rule 2: always keep type-class instances (inst* prefix).
                      // Rule 3: keep regular hyps only if name is transitively reachable.
                      .filter(h => h.name.startsWith("inst") || reachable(h.name))
                      .map(h => s"${h.name} : ${h.typ}")
    val premises  = supportHyps                                   // A: minimal support
                      .filterNot(h => isTypeUniverse(h.typ))
                      .map(h => s"${h.name} : ${h.typ}")
    val conclusion = fragment.rootObligation.goal                 // gF
    val statement  = StatementFormatter.format(scopeVars, premises, body, conclusion)
    LemmaObj(fragment.fragmentId, fragment.sourceFile, fragment.declName,
             scopeVars, premises, body, conclusion, statement)
