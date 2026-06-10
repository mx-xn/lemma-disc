import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import upickle.default.*

/** Integration tests for Parser.parseFile against the real phase-1 fixture
 *  `data/traces/MiniCodePropsLeanSrc/Examples.json`.
 *
 *  The fixture is large enough to exercise every shape produced by phase 1:
 *  reserved-word "type" keys on hypotheses, snake_case "directly_used" and
 *  "dependency_maps", null parent_ids, branching nodes (multiple outputs),
 *  leaf nodes (zero outputs), and the LeanProofTrace top-level wrapper.
 *
 *  Stats (verified via jq against the fixture on 2026-06-01):
 *    declarations   25
 *    tactic_nodes  222
 *    leaves         91
 *    roots          25
 *    branching      54
 *    non-null parent_ids 197
 */
class ParserTest extends AnyFlatSpec with Matchers:

  // Walk up from CWD looking for `data/traces/MiniCodePropsLeanSrc/Examples.json`.
  // Handles `sbt` invoked from either `scala-core/` or `scala-core/pog/`.
  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(
        s"Examples.json fixture not found above ${os.pwd}"))

  private lazy val parsed: LeanProofTrace = Parser.parseFile(fixture)


  // ── Smoke + header ────────────────────────────────────────────────────────

  "Parser.parseFile" should "parse Examples.json without throwing" in {
    noException should be thrownBy Parser.parseFile(fixture)
  }

  it should "preserve the top-level source_file" in {
    parsed.sourceFile shouldBe "LeanSrc/Examples.lean"
  }

  it should "parse all 25 declarations" in {
    parsed.declarations.length shouldBe 25
  }


  // ── Aggregate counts across all declarations ─────────────────────────────

  it should "parse all 222 tactic nodes across declarations" in {
    parsed.declarations.flatMap(_.tacticNodes).length shouldBe 222
  }

  it should "decode 91 leaf nodes (empty output_obligations)" in {
    val leaves = parsed.declarations.flatMap(_.tacticNodes)
                       .count(_.outputObligations.isEmpty)
    leaves shouldBe 91
  }

  it should "decode 25 root nodes (parent_id == null → None)" in {
    val roots = parsed.declarations.flatMap(_.tacticNodes)
                      .count(_.parentId.isEmpty)
    roots shouldBe 25
  }

  it should "decode 197 non-null parent_ids as Some(_)" in {
    val nonNull = parsed.declarations.flatMap(_.tacticNodes)
                        .count(_.parentId.isDefined)
    nonNull shouldBe 197
  }

  it should "find 54 branching nodes (> 1 output obligation)" in {
    val branching = parsed.declarations.flatMap(_.tacticNodes)
                          .count(_.outputObligations.length > 1)
    branching shouldBe 54
  }


  // ── First declaration: prop_14 ───────────────────────────────────────────
  //
  // Full tree shape (verified via jq):
  //
  //   0  induction xs            (branching: children 1, 2)
  //   ├─ 1  simp [filter]        (leaf — nil case)
  //   └─ 2  simp [filter]        (linear → 3)
  //      └─ 3  split_ifs with h  (branching: children 4, 6)
  //         ├─ 4  simp           (linear → 5)
  //         │  └─ 5  exact ih    (leaf)
  //         └─ 6  exact ih       (leaf)

  it should "parse prop_14 as the first declaration with 7 tactic nodes" in {
    val d = parsed.declarations.head
    d.name           shouldBe "prop_14"
    d.rootTacticId   shouldBe 0
    d.tacticNodes.length shouldBe 7
  }

  it should "parse prop_14's root (id=0) — branching `induction xs` with two children" in {
    val root = parsed.declarations.head.tacticNodes
                     .find(_.id == 0).getOrElse(fail("no node id=0"))
    root.tacticText       should startWith ("induction xs")
    root.parentId         shouldBe None
    root.childIds         shouldBe List(1, 2)
    root.outputObligations.length shouldBe 2
  }

  it should "parse prop_14's root hypothesis list with the reserved-word `type` key" in {
    val root = parsed.declarations.head.tacticNodes.head
    val hyps = root.inputObligation.hypotheses
    hyps.length shouldBe 4
    hyps.head.name   shouldBe "α"
    hyps.head.`type` shouldBe "Type u_1"
    root.inputObligation.goal shouldBe
      "filter p (xs ++ ys) = filter p xs ++ filter p ys"
  }

  it should "parse prop_14's root summary (directly_used + dependency_maps)" in {
    val sum = parsed.declarations.head.tacticNodes.head.summary
    sum.directlyUsed shouldBe List("xs")
    sum.dependencyMaps.length shouldBe 2
    // Branch 0 (nil): identity map over α, p, ys
    sum.dependencyMaps(0)("α")  shouldBe List("α")
    sum.dependencyMaps(0)("p")  shouldBe List("p")
    sum.dependencyMaps(0)("ys") shouldBe List("ys")
    // Branch 1 (cons): ih ↦ [xs, ys, p] — induction-hypothesis dependency fan-out
    sum.dependencyMaps(1)("ih") shouldBe List("xs", "ys", "p")
  }

  it should "parse prop_14 node 1 — `simp [filter]` leaf on the nil branch" in {
    val n = prop14NodeById(1)
    n.tacticText         shouldBe "simp [filter]"
    n.parentId           shouldBe Some(0)
    n.childIds           shouldBe List.empty[Int]
    n.outputObligations  shouldBe List.empty[Obligation]
    n.summary.directlyUsed   shouldBe List.empty[String]
    n.summary.dependencyMaps shouldBe List.empty[Map[String, List[String]]]
    // Note: induction's nil branch drops `xs` from Γ.
    val hypNames = n.inputObligation.hypotheses.map(_.name)
    hypNames shouldBe List("α", "p", "ys")
    n.inputObligation.goal shouldBe
      "filter p ([] ++ ys) = filter p [] ++ filter p ys"
  }

  it should "parse prop_14 node 2 — `simp [filter]` non-leaf on the cons branch with the inductive hypothesis in scope" in {
    val n = prop14NodeById(2)
    n.tacticText shouldBe "simp [filter]"
    n.parentId   shouldBe Some(0)
    n.childIds   shouldBe List(3)
    n.outputObligations.length shouldBe 1
    val hypNames = n.inputObligation.hypotheses.map(_.name)
    hypNames shouldBe List("α", "p", "ys", "x", "xs", "ih")
    // The IH hypothesis carries the full quantifier-free recurrence as its type.
    n.inputObligation.hypotheses.find(_.name == "ih").get.`type` shouldBe
      "filter p (xs ++ ys) = filter p xs ++ filter p ys"
    n.summary.directlyUsed shouldBe List.empty[String]
    n.summary.dependencyMaps(0)("ih") shouldBe List("ih")
  }

  it should "parse prop_14 node 3 — branching `split_ifs with h` with non-contiguous child ids [4, 6]" in {
    val n = prop14NodeById(3)
    n.tacticText            shouldBe "split_ifs with h"
    n.parentId              shouldBe Some(2)
    n.childIds              shouldBe List(4, 6)   // <- gap, child 5 is under 4
    n.outputObligations.length shouldBe 2
  }

  it should "parse prop_14 leaves 5 and 6 as `exact ih` at distinct depths" in {
    val n5 = prop14NodeById(5)
    val n6 = prop14NodeById(6)
    n5.tacticText shouldBe "exact ih"
    n5.parentId   shouldBe Some(4)               // depth 4
    n5.childIds   shouldBe List.empty[Int]
    n5.outputObligations shouldBe List.empty[Obligation]
    n6.tacticText shouldBe "exact ih"
    n6.parentId   shouldBe Some(3)               // depth 3 — same tactic text, different ancestor chain
    n6.childIds   shouldBe List.empty[Int]
    n6.outputObligations shouldBe List.empty[Obligation]
  }

  // ── Evidence for the future POG use-edges (0 → 5) and (0 → 6) ────────────
  //
  // Per Definition 2 (use-dep) — to be verified in DependencyTest.scala once
  // Step 6 lands — `induction xs` introduces `ih` into the cons branch, and
  // both `exact ih` leaves reference it.  This test asserts the *raw trace
  // evidence* the edge derivation will consume: it parses correctly, even
  // though Parser itself does not construct edges.
  //
  // Concretely:
  //   - Node 0's cons-branch output_obligations[1] introduces `ih` (and `x`):
  //     names appearing in Γ_1 but not in the root Γ_0.  Under the CLAUDE.md
  //     fallback recovery rule, these go into M_hyps for node 0.
  //   - Node 5 and node 6 (both `exact ih`) carry `directly_used = ["ih"]`,
  //     so D_5 = D_6 = {ih} (leaves: M = ∅, hence D = U).
  //   - The path-only-intermediate-k constraint is satisfied trivially:
  //     nodes 2 (simp [filter]), 3 (split_ifs), 4 (simp) do not list `ih`
  //     in their `directly_used` either, so no earlier k claims it.

  it should "carry the trace evidence for POG use-edges (0 → 5) and (0 → 6)" in {
    val n0 = prop14NodeById(0)
    val n5 = prop14NodeById(5)
    val n6 = prop14NodeById(6)

    // (1) Node 0 introduces `ih` (and `x`) in the cons branch — names that
    //     don't appear in the root's input context.
    val rootInputNames     = n0.inputObligation.hypotheses.map(_.name).toSet
    val consBranchOutNames = n0.outputObligations(1).hypotheses.map(_.name).toSet
    val introducedByInd    = consBranchOutNames -- rootInputNames
    introducedByInd should contain ("ih")
    introducedByInd should contain ("x")

    // (2) Both `exact ih` leaves use `ih` and only `ih`.
    n5.summary.directlyUsed shouldBe List("ih")
    n6.summary.directlyUsed shouldBe List("ih")

    // (3) Sanity — no node on the path between 0 and {5, 6} uses `ih`,
    //     which is what enables the "no intermediate k" clause to be
    //     satisfied for edges (0, 5) and (0, 6).
    val pathIds = List(2, 3, 4)
    pathIds.foreach { id =>
      withClue(s"node $id directly_used must not contain 'ih': ") {
        prop14NodeById(id).summary.directlyUsed should not contain "ih"
      }
    }
  }


  // ── prop_37 (idx 5): single-node `sorry` proof ───────────────────────────
  //
  // Smallest declaration in the fixture (1 tactic node, no children, no
  // outputs). Exercises the degenerate case of an unfinished proof.

  it should "parse prop_37 (idx 5) as a single-node `sorry` declaration" in {
    val d = parsed.declarations(5)
    d.name shouldBe "prop_37"
    d.tacticNodes.length shouldBe 1
    val n = d.tacticNodes.head
    n.id         shouldBe 0
    n.tacticText shouldBe "sorry"
    n.parentId   shouldBe None
    n.childIds   shouldBe List.empty[Int]
    n.outputObligations shouldBe List.empty[Obligation]
    n.summary.directlyUsed   shouldBe List.empty[String]
    n.summary.dependencyMaps shouldBe List.empty[Map[String, List[String]]]
  }


  // ── prop_85 (idx 24): last declaration, exercises non-sequential child_ids ─
  //
  // Its root's child_ids are [1, 6] — branch 0 occupies ids 1..5, branch 1
  // starts at id 6. Confirms that we don't assume childIds form a contiguous
  // numeric range.

  it should "parse prop_85 (idx 24, last) as a 17-node decl with non-sequential root child_ids [1, 6]" in {
    val d = parsed.declarations(24)
    d.name shouldBe "prop_85"
    d.rootTacticId shouldBe 0
    d.tacticNodes.length shouldBe 17
    val root = d.tacticNodes.find(_.id == 0).getOrElse(fail("no root"))
    root.tacticText should startWith ("induction xs generalizing ys")
    root.parentId  shouldBe None
    root.childIds  shouldBe List(1, 6)              // non-contiguous
    root.outputObligations.length shouldBe 2
    root.summary.directlyUsed shouldBe List("xs", "ys", "α", "β")
    // Branch 1 dep_map: x ↦ ["α"] (introduced element pulls from α)
    root.summary.dependencyMaps(1)("x")  shouldBe List("α")
    root.summary.dependencyMaps(1)("ih") shouldBe List("xs", "ys", "β")
  }

  // Helper used by the prop_14 per-node tests above.
  private def prop14NodeById(id: Int): TacticNode =
    parsed.declarations.head.tacticNodes
          .find(_.id == id).getOrElse(fail(s"no prop_14 node id=$id"))


  // ── Sanity invariants over the entire fixture ────────────────────────────

  it should "have every non-null parent_id reference an existing node id within the same declaration" in {
    parsed.declarations.foreach { d =>
      val ids = d.tacticNodes.map(_.id).toSet
      d.tacticNodes.foreach { n =>
        n.parentId.foreach { p =>
          withClue(s"decl ${d.name} node ${n.id} parent_id=$p: ") {
            ids should contain (p)
          }
        }
      }
    }
  }

  it should "have child_ids agree with parent_id pointers (tree invariant)" in {
    parsed.declarations.foreach { d =>
      val byId = d.tacticNodes.iterator.map(n => n.id -> n).toMap
      d.tacticNodes.foreach { n =>
        n.childIds.foreach { c =>
          withClue(s"decl ${d.name} node ${n.id} -> child $c: ") {
            byId(c).parentId shouldBe Some(n.id)
          }
        }
      }
    }
  }

  it should "have child_ids.length == output_obligations.length on every node" in {
    parsed.declarations.foreach { d =>
      d.tacticNodes.foreach { n =>
        withClue(s"decl ${d.name} node ${n.id}: ") {
          n.childIds.length shouldBe n.outputObligations.length
        }
      }
    }
  }


  // ── Round-trip ───────────────────────────────────────────────────────────

  it should "round-trip: write(parsed) re-read should equal parsed" in {
    val rewritten = write(parsed)
    val reparsed  = read[LeanProofTrace](rewritten)
    reparsed shouldBe parsed
  }


  // ── Error path ───────────────────────────────────────────────────────────

  it should "throw when given a path that does not exist" in {
    val bogus = os.pwd / "definitely-not-a-real-trace-file-zzz.json"
    an [Exception] should be thrownBy Parser.parseFile(bogus)
  }
