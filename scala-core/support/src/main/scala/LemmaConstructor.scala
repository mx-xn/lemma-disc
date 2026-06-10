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
  // premises — Lean auto-binds free type variables implicitly, so emitting
  // them explicitly just adds noise.
  private val typeUniversePattern = """^Type u_\w+$""".r
  private def isTypeUniverse(typ: String): Boolean =
    typeUniversePattern.matches(typ.trim)

  // Assembles the full lemma: minimal-support premises + Lem(Υ) → gF, rendered
  // with Lean binder syntax via `StatementFormatter`.
  def constructLemma(fragment: Fragment): LemmaObj =
    val support  = SupportCalc.computeSupport(fragment.tree)     // A ⊆ ΓF (minimal support)
    val premises = fragment.rootObligation.hypotheses             // filter ΓF to A, format as "name : type"
                     .filter(h => support(h.name))
                     .filterNot(h => isTypeUniverse(h.typ))
                     .map(h => s"${h.name} : ${h.typ}")
    val body       = computeLem(fragment.tree).getOrElse("True")  // Lem(Υ), or "True" when ⊤
    val conclusion = fragment.rootObligation.goal                 // gF
    val statement  = StatementFormatter.format(premises, body, conclusion)
    LemmaObj(fragment.fragmentId, fragment.sourceFile, fragment.declName,
             premises, body, conclusion, statement)
