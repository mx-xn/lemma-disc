import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for `Dependency.compute` (Step 6) — the dependency edges aᵢ ≺ aⱼ of
 *  paper Definition 2 (§2.1), name-level coarsened. This is the POG's edge set
 *  E; `Builder` assembles it via
 *
 *    Dependency.compute(nodes: List[TacticNode], footprints: Map[Int, Footprint])
 *      : List[PogEdge]
 *
 *  Edges are deduplicated `(from, to, kind)` tuples over ALL root-to-leaf paths.
 *  `kind ∈ {ModifyEdge, UseEdge}`; if BOTH hold for one (i,j), two edges emit.
 *
 *  ── Paper Definition 2 (the two dependency conditions) ──────────────────────
 *
 *  Along a root-to-leaf path a₁,…,aₙ with footprints Φ(aₖ)=(Dₖ,Mₖ,_,ρₖ), extend
 *  ρ to a forward propagation ρ_{i→j} along the path. For i<j, aⱼ ≺ aᵢ if either
 *    1. (Modification) ∃ s∈Mᵢ with ρ_{i→j}(s) landing on some q∈Mⱼ, and no
 *       intermediate k (i<k<j) satisfies the same condition relative to aⱼ; or
 *    2. (Use) ∃ s∈Mᵢ with ρ_{i→j}(s) landing on some q∈Dⱼ, same "no intermediate
 *       k" minimality.
 *
 *  ── Load-bearing interpretations (settled in design review 2026-06-01; the
 *     expected values below depend on each — do NOT "fix" toward looser prose) ──
 *
 *    [P1] FORWARD PROPAGATION = compose ρ of nodes i … j-1 along the path. To
 *         test aᵢ ≺ aⱼ, seed the modified name s at node i's input, then apply
 *         ρ_i (at the branch index = position of the next-on-path child in
 *         `childIds`), ρ_{i+1}, …, ρ_{j-1}. Node i's OWN ρ is applied; node j's
 *         is NOT. (ρ_{i→i}=id; ρ_{i→j+1}=ρ_{j+1}∘ρ_{i→j} in paper indices.)
 *         Verified against the prop_14 golden (Group 9): xs propagates to
 *         {xs, ih} across the cons branch, reaching `exact ih`. Pinned directly
 *         by Group 6.1 (rename through node i's own ρ) and 6.4 (branch select).
 *
 *    [P2] SOURCE MODIFIED SET  Mᵢ = modifiesHyps ∪ {"⊢" if modifiesGoal}. The
 *         goal token "⊢" originates a dependency ONLY when modifies_goal=true,
 *         even though `Footprint` keeps ⊢→{⊢} in ρ UNCONDITIONALLY (propagation
 *         ≠ modification — the very distinction FootprintTest pins). Group 1.5.
 *
 *    [P3] GOAL USE-EDGES FOR LEAVES. For non-leaf nodes, "⊢" is never a
 *         use-landing (D⊆Γ). For LEAF nodes (outputObligations empty), "⊢" IS
 *         added to Dⱼ: leaf use-depends on nearest preceding goal-modifier.
 *         Non-leaf goal→goal threading is still MODIFY-only. Groups 3.2, 4.2, 9.
 *
 *    [P4] "NO INTERMEDIATE k" IS PER-LANDING-NAME. An intermediate k cancels a
 *         witness only when it ALSO lands on the SAME q (the `claimedFor(j)`
 *         set of CLAUDE.md Step 6). Independent names do not cross-cancel:
 *         Group 4.4 keeps both use(2,3)[via h] and use(1,3)[via k]; the prop_14
 *         use-edges 0→5/0→6 survive because the intervening goal modifiers land
 *         on ⊢, not on `ih`. Group 9 also now has 0→1/4→5/3→6 use-edges for the
 *         three leaf nodes (relaxed [P3] for leaves).
 *
 *  `compute` is a function of the TREE SHAPE (parentId/childIds for paths and
 *  branch indices) and the supplied `footprints` map; obligation CONTENTS and
 *  the tactic summary are recovered upstream by `Footprint.compute`, so the
 *  hand-built nodes here carry dummy obligations and the footprints are injected
 *  directly for full control.
 */
class DependencyTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private val dummyObl = Obligation(Nil, "g")
  private val Goal      = "⊢"  // reserved goal-slot token

  /** Node by TREE SHAPE only; output count tracks child count (the well-formed
   *  invariant). Summary is a dummy — footprints are injected, not derived. */
  private def tn(id: Int, parent: Option[Int], children: List[Int]): TacticNode =
    TacticNode(
      id                = id,
      tacticText        = "tac",
      inputObligation   = dummyObl,
      outputObligations = List.fill(children.size)(dummyObl),
      summary           = TacticSummary(Nil, Nil),
      parentId          = parent,
      childIds          = children
    )

  /** Hand-built footprint (the value `Footprint.compute` would otherwise yield).
   *  rho is co-indexed with output branches; leaves/targets may omit it. */
  private def fp(
    uses:    Set[String]                    = Set.empty,
    modHyps: Set[String]                    = Set.empty,
    modGoal: Boolean                        = false,
    rho:     List[Map[String, Set[String]]] = Nil
  ): Footprint = Footprint(uses, modHyps, modGoal, rho)

  /** Identity forward map for `names` plus the always-present goal entry — the
   *  shape `Footprint.compute` produces for a tactic that carries hyps through
   *  unchanged. */
  private def carry(names: String*): Map[String, Set[String]] =
    names.iterator.map(n => n -> Set(n)).toMap + (Goal -> Set(Goal))

  /** Run compute and collapse to an order-insensitive edge set. */
  private def run(nodes: List[TacticNode], fps: Map[Int, Footprint]): Set[PogEdge] =
    Dependency.compute(nodes, fps).toSet


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — No dependency / degenerate (source gating, disjointness)
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (none)" should "return no edges for an empty node list" in {
    run(Nil, Map.empty) shouldBe empty
  }

  it should "return no edges for a single root leaf" in {
    val ns = List(tn(0, None, Nil))
    run(ns, Map(0 -> fp(uses = Set("h")))) shouldBe empty
  }

  it should "emit nothing when the would-be source modifies nothing (Mᵢ=∅)" in {
    // node 0 only propagates h; node 1 uses h. With M₀=∅, node 0 can originate
    // no dependency, so there is no edge despite the downstream use.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(rho = List(carry("h"))),
      1 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe empty
  }

  it should "emit nothing for disjoint footprints (modifies h1, downstream uses h2)" in {
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h1"), rho = List(carry("h1"))),
      1 -> fp(uses = Set("h2"))
    )
    run(ns, fps) shouldBe empty
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — Basic use-dependence on a linear chain
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (use)" should "link a modifier to a downstream user of the same name" in {
    // canonical: a₁ modifies h, a₂ uses h.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, UseEdge))
  }

  it should "emit one use-edge when only one of the source's modified names is used" in {
    // source modifies {h, k}; target uses only h ⇒ a single use-edge.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h", "k"), rho = List(carry("h", "k"))),
      1 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, UseEdge))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Basic modify-dependence on a linear chain
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (modify)" should "link two successive modifiers of the same hyp" in {
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(modHyps = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, ModifyEdge))
  }

  it should "emit both MODIFY and USE for goal→goal when target is a leaf ([P3] relaxed for leaves)" in {
    // node 1 is a leaf (Nil children): uses(1) includes "⊢", so both modify-dep
    // (0 modifies goal, lands on modifies(1)=⊢) and use-dep (lands on uses(1)=⊢) fire.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modGoal = true, rho = List(carry())),  // carry() = just ⊢→{⊢}
      1 -> fp(modGoal = true)
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, ModifyEdge), PogEdge(0, 1, UseEdge))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — "No intermediate k" minimality (per-landing-name, [P4])
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (minimality)" should
    "attribute a use to the LATEST modifier: mod h, mod h, use h ⇒ (1,2)mod + (2,3)use, not (1,3)" in {
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      2 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, ModifyEdge), PogEdge(1, 2, UseEdge))
  }

  it should "chain three goal modifiers: (0,1)+(1,2) modify, plus (1,2) use for the leaf" in {
    // node 2 is a leaf (Nil children): it gets both 1→2 modify (goal→goal) and
    // 1→2 use (leaf claims ⊢); node 0 is blocked on both names by node 1.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil))
    val fps = Map(
      0 -> fp(modGoal = true, rho = List(carry())),
      1 -> fp(modGoal = true, rho = List(carry())),
      2 -> fp(modGoal = true)
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, ModifyEdge), PogEdge(1, 2, ModifyEdge), PogEdge(1, 2, UseEdge))
  }

  it should "span an unrelated intermediate: mod h, (touch nothing), use h ⇒ (0,2)use" in {
    // node 1 modifies nothing but propagates h forward, so it does NOT cancel.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(rho = List(carry("h"))),
      2 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 2, UseEdge))
  }

  it should "cancel PER-NAME, not per-pair: mod{h,k}, mod{h}, use{h,k} keeps both use(2,3)[h] and use(1,3)[k]" in {
    // The decisive [P4] case. node 1 re-modifies h (claims the h-witness for 2→3)
    // but never touches k, so k's dependency on node 0 survives as use(1,3)... here
    // (0,2) in 0-indexed ids.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h", "k"), rho = List(carry("h", "k"))),
      1 -> fp(modHyps = Set("h"),      rho = List(carry("h", "k"))),
      2 -> fp(uses = Set("h", "k"))
    )
    run(ns, fps) shouldBe Set(
      PogEdge(0, 1, ModifyEdge),  // h: successive modifiers
      PogEdge(1, 2, UseEdge),     // h: latest modifier (node 1) → user
      PogEdge(0, 2, UseEdge)      // k: node 1 never touches k ⇒ node 0 still reaches it
    )
  }

  it should "keep only the latest modifier across a long chain: mod,mod,mod,use ⇒ (0,1)(1,2)mod + (2,3)use" in {
    val ns = List(
      tn(0, None, List(1)), tn(1, Some(0), List(2)),
      tn(2, Some(1), List(3)), tn(3, Some(2), Nil)
    )
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      2 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      3 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(
      PogEdge(0, 1, ModifyEdge), PogEdge(1, 2, ModifyEdge), PogEdge(2, 3, UseEdge)
    )
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — Both kinds for one (i,j) ⇒ two distinct edges
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (both kinds)" should "emit a modify- AND a use-edge for the same pair" in {
    // node 0 modifies {h, k}; node 1 modifies h (M₁∋h) and uses k (D₁∋k).
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h", "k"), rho = List(carry("h", "k"))),
      1 -> fp(uses = Set("k"), modHyps = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, ModifyEdge), PogEdge(0, 1, UseEdge))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — Forward propagation & branch selection ([P1])
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (propagation)" should "follow a RENAME through the source's own ρ (h→h')" in {
    // node 0's OWN ρ renames h↦h'; node 1 uses h'. Confirms ρ_i is applied.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(Map("h" -> Set("h'"), Goal -> Set(Goal)))),
      1 -> fp(uses = Set("h'"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, UseEdge))
  }

  it should "NOT link on a literal-name coincidence when ρ does not carry the name" in {
    // node 0 modifies h but h has no residual dependent (absent from ρ); the
    // downstream `h` is an unrelated, freshly-named hyp ⇒ no edge.
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(Map(Goal -> Set(Goal)))),  // h not a key
      1 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe empty
  }

  it should "follow a SPLIT in ρ (induction-like xs→{xs,ih}) to a user of the split name" in {
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("xs"), rho = List(Map("xs" -> Set("xs", "ih"), Goal -> Set(Goal)))),
      1 -> fp(uses = Set("ih"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, UseEdge))
  }

  it should "select the correct branch's ρ at a branching source" in {
    // node 0 branches: branch 0 (→node 1) maps h↦h; branch 1 (→node 2) maps h↦h2.
    // Both leaves use h2 ⇒ only the branch-1 path (node 2) gets an edge.
    val ns = List(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(
        Map("h" -> Set("h"),  Goal -> Set(Goal)),   // branch 0 → node 1
        Map("h" -> Set("h2"), Goal -> Set(Goal))    // branch 1 → node 2
      )),
      1 -> fp(uses = Set("h2")),
      2 -> fp(uses = Set("h2"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 2, UseEdge))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Tree structure: multiple paths, dedup, cross-branch isolation
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (tree)" should "link a branching source to a user on EACH branch" in {
    val ns = List(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil))
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"), carry("h"))),
      1 -> fp(uses = Set("h")),
      2 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(0, 1, UseEdge), PogEdge(0, 2, UseEdge))
  }

  it should "DEDUPLICATE an edge discovered on several root-to-leaf paths" in {
    // 0→1→{2,3}: edge (0,1) lies on both leaf paths but must appear once.
    val ns = List(
      tn(0, None, List(1)), tn(1, Some(0), List(2, 3)),
      tn(2, Some(1), Nil), tn(3, Some(1), Nil)
    )
    val fps = Map(
      0 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      1 -> fp(uses = Set("h"), rho = List(carry("h"), carry("h"))),
      2 -> fp(),
      3 -> fp()
    )
    val raw = Dependency.compute(ns, fps)
    raw.size shouldBe raw.distinct.size                  // no duplicates in the raw list
    raw.toSet shouldBe Set(PogEdge(0, 1, UseEdge))
  }

  it should "NOT link two SIBLINGS (no common root-to-leaf path)" in {
    // root → {1, 2}; node 1 modifies h, node 2 uses h. They never co-occur on a
    // path ⇒ no edge.
    val ns = List(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil))
    val fps = Map(
      0 -> fp(rho = List(carry("h"), carry("h"))),
      1 -> fp(modHyps = Set("h")),
      2 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe empty
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Determinism / structural invariants
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (structure)" should "be independent of input-list order" in {
    val ns = List(
      tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)
    )
    val fps = Map(
      0 -> fp(modHyps = Set("h", "k"), rho = List(carry("h", "k"))),
      1 -> fp(modHyps = Set("h"),      rho = List(carry("h", "k"))),
      2 -> fp(uses = Set("h", "k"))
    )
    run(ns, fps) shouldBe run(ns.reverse, fps)
  }

  it should "orient `from`=ANCESTOR even when ids are non-monotonic (i<j is depth, not id)" in {
    // ancestor id 9 → descendant id 2. The edge must be (9,2), not id-sorted.
    val ns = List(tn(9, None, List(2)), tn(2, Some(9), Nil))
    val fps = Map(
      9 -> fp(modHyps = Set("h"), rho = List(carry("h"))),
      2 -> fp(uses = Set("h"))
    )
    run(ns, fps) shouldBe Set(PogEdge(9, 2, UseEdge))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 9 — Golden: the real prop_14 tree from the phase-1 fixture
  // ═══════════════════════════════════════════════════════════════════════════
  //
  //   0 induction xs   → {1 (nil), 2 (cons)}      modifies xs + goal
  //   1 simp [filter]  (nil leaf)
  //   2 simp [filter]  → 3                          modifies goal
  //   3 split_ifs      → {4, 6}                     modifies goal
  //   4 simp           → 5                           modifies goal
  //   5 exact ih       (leaf, uses ih)
  //   6 exact ih       (leaf, uses ih)
  //
  //   Goal threading gives consecutive MODIFY edges 0→2→3→4. The induction var
  //   xs propagates into `ih` (rho split), so each `exact ih` USE-depends on the
  //   induction node 0 — and the intervening goal modifiers (2,3,4) land on ⊢,
  //   never on `ih`, so under per-name minimality [P4] they do NOT cancel 0→5/0→6.
  //   Relaxed [P3]: each leaf also use-depends on the nearest preceding goal-modifier:
  //   node 1 (nil leaf) → 0→1 use; node 5 (exact ih leaf) → 4→5 use; node 6 → 3→6 use.

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  "Dependency.compute (golden prop_14)" should "match the hand-derived edge set of all 7 nodes" in {
    val prop14 = Parser.parseFile(fixture).declarations.head
    prop14.name shouldBe "prop_14"   // guard against fixture drift

    val fps = prop14.tacticNodes.iterator.map(n => n.id -> Footprint.compute(n)).toMap
    run(prop14.tacticNodes, fps) shouldBe Set(
      PogEdge(0, 2, ModifyEdge),
      PogEdge(2, 3, ModifyEdge),
      PogEdge(3, 4, ModifyEdge),
      PogEdge(0, 1, UseEdge),   // leaf 1 (nil branch): nearest goal-modifier is 0
      PogEdge(4, 5, UseEdge),   // leaf 5 (exact ih): nearest goal-modifier is 4
      PogEdge(3, 6, UseEdge),   // leaf 6 (exact ih): nearest goal-modifier is 3
      PogEdge(0, 5, UseEdge),   // leaf 5: ih use-dep traces back to induction (0)
      PogEdge(0, 6, UseEdge)    // leaf 6: ih use-dep traces back to induction (0)
    )
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 10 — Defensive / degenerate (fail fast over silently wrong, per
  //            BranchPathTest's documented posture)
  // ═══════════════════════════════════════════════════════════════════════════

  "Dependency.compute (degenerate)" should "emit no edges when every footprint is empty" in {
    val ns = List(
      tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil)
    )
    val fps = Map(0 -> fp(rho = List(carry())), 1 -> fp(rho = List(carry())), 2 -> fp())
    run(ns, fps) shouldBe empty
  }

  it should "FAIL FAST on a dangling childId (corrupt tree)" in {
    // node 0 claims child 1, but node 1 is absent from the list. ParserTest
    // guarantees children resolve, so a dangling pointer is corrupt input.
    val ns = List(tn(0, None, List(1)))
    an [Exception] should be thrownBy
      Dependency.compute(ns, Map(0 -> fp(modHyps = Set("h"), rho = List(carry("h")))))
  }

  it should "FAIL FAST when a node is missing from the footprints map" in {
    val ns = List(tn(0, None, List(1)), tn(1, Some(0), Nil))
    an [Exception] should be thrownBy
      Dependency.compute(ns, Map(0 -> fp(modHyps = Set("h"), rho = List(carry("h")))))
  }
