import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for `Builder` (Step 7) — the pure wiring layer that assembles a
 *  ProofOrderingGraph from the already-tested phase-2 components.
 *
 *  Builder adds NO graph mathematics (Footprint/BranchPath/Dependency each have
 *  their own exhaustive suites, including the prop_14 golden). What is NEW here,
 *  and what these tests pin, is the WIRING:
 *
 *    • each PogNode is paired with ITS OWN footprint and branch path, keyed BY
 *      ID (not by list position — node lists may be out of id-order with gaps);
 *    • node order and count are preserved (one PogNode per TacticNode);
 *    • the edge set is exactly Dependency's output;
 *    • root_obligation is the root node's input, resolved by id;
 *    • the top-level fields pass through verbatim; buildFile maps every decl.
 *
 *  Unlike DependencyTest (which injects footprints), these nodes carry REAL
 *  obligations/summaries, so Builder also serves as a small integration test of
 *  Footprint + BranchPath + Dependency composed together.
 */
class BuilderTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private def hyp(n: String, t: String): Hypothesis = Hypothesis(n, t)
  private def obl(goal: String, hs: Hypothesis*): Obligation = Obligation(hs.toList, goal)
  private def sum(used: List[String], deps: Map[String, List[String]]*): TacticSummary =
    TacticSummary(used, deps.toList)

  private def node(
    id: Int, text: String, in: Obligation, outs: List[Obligation],
    summary: TacticSummary, parent: Option[Int], children: List[Int]
  ): TacticNode = TacticNode(id, text, in, outs, summary, parent, children)

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP A — build: single-declaration wiring
  // ═══════════════════════════════════════════════════════════════════════════

  // Canonical linear chain (the doc's `intro h; rw h; rfl` shape): a modifier, a
  // pass-through, then a user of the same name. The pass-through does NOT cancel
  // (it modifies nothing), so the edge attributes to node 0 ⇒ exactly {(0,2)use}.
  private val rootObl = obl("G", hyp("h", "P"), hyp("x", "Nat"))
  private val linearChain: Declaration =
    Declaration("lin", "theorem lin : G", 0, List(
      node(0, "simp at h", rootObl,
        List(obl("G", hyp("h", "P'"), hyp("x", "Nat"))),
        sum(Nil, Map("h" -> List("h"), "x" -> List("x"))), None, List(1)),
      node(1, "ring_nf", obl("G", hyp("h", "P'"), hyp("x", "Nat")),
        List(obl("G", hyp("h", "P'"), hyp("x", "Nat"))),
        sum(Nil, Map("h" -> List("h"), "x" -> List("x"))), Some(0), List(2)),
      node(2, "exact h", obl("G", hyp("h", "P'"), hyp("x", "Nat")),
        Nil, sum(List("h")), Some(1), Nil)
    ))

  "Builder.build (canonical linear chain)" should "produce exactly the edge {(0,2) use}" in {
    Builder.build(linearChain).edges.toSet shouldBe Set(PogEdge(0, 2, UseEdge))
  }

  it should "preserve all three nodes in input order" in {
    Builder.build(linearChain).nodes.map(_.node.id) shouldBe List(0, 1, 2)
  }

  it should "lift the root node's input obligation to root_obligation" in {
    Builder.build(linearChain).rootObligation shouldBe rootObl
  }

  it should "pass the top-level decl fields through verbatim" in {
    val pog = Builder.build(linearChain)
    pog.declName     shouldBe "lin"
    pog.statement    shouldBe "theorem lin : G"
    pog.rootTacticId shouldBe 0
  }

  it should "pair each node with its OWN computed footprint (the modify/use split)" in {
    val byId = Builder.build(linearChain).nodes.iterator.map(p => p.node.id -> p).toMap
    byId(0).footprint.modifiesHyps shouldBe Set("h")   // simp at h retypes h
    byId(1).footprint.modifiesHyps shouldBe empty       // ring_nf changes nothing
    byId(2).footprint.uses         shouldBe Set("h")    // exact h uses h
  }

  it should "give every node on a linear chain an empty branch path" in {
    Builder.build(linearChain).nodes.foreach { p =>
      withClue(s"node ${p.node.id}: ") { p.branchPath shouldBe BranchPath(Nil) }
    }
  }

  // ── single-node leaf ─────────────────────────────────────────────────────────

  "Builder.build (single leaf)" should "yield one node, no edges, empty branch path, correct root_obligation" in {
    val in   = obl("P", hyp("h", "P"))
    val decl = Declaration("triv", "theorem triv : P", 0,
      List(node(0, "exact h", in, Nil, sum(List("h")), None, Nil)))
    val pog  = Builder.build(decl)
    pog.nodes.length                 shouldBe 1
    pog.edges                        shouldBe empty
    pog.nodes.head.branchPath        shouldBe BranchPath(Nil)
    pog.rootObligation               shouldBe in
    pog.nodes.head.footprint.uses    shouldBe Set("h")
  }

  // ── co-indexing guard: out-of-order list, id gaps, branching ─────────────────
  //
  // Tree:  5 (induction, branching) → children [2, 6]   (ids gapped, root id ≠ 0)
  //        2 (simp, nil leaf)
  //        6 (exact ih, cons leaf)
  // The node list is SCRAMBLED to [6, 5, 2]. A positional (vs id-keyed) wiring
  // bug would attach node 6 the root's footprint/branch path — caught here.

  private val branchingDecl: Declaration =
    Declaration("br", "theorem br : G", 5, List(
      node(6, "exact ih", obl("G2", hyp("ih", "IH")), Nil, sum(List("ih")), Some(5), Nil),
      node(5, "induction xs", obl("G", hyp("xs", "List α")),
        List(obl("G1"), obl("G2", hyp("ih", "IH"))),
        sum(List("xs"), Map.empty, Map("ih" -> List("xs"))), None, List(2, 6)),
      node(2, "simp", obl("G1"), Nil, sum(Nil), Some(5), Nil)
    ))

  "Builder.build (co-indexing)" should "preserve the scrambled input order [6, 5, 2]" in {
    Builder.build(branchingDecl).nodes.map(_.node.id) shouldBe List(6, 5, 2)
  }

  it should "attach each node's OWN footprint by id, never by list position" in {
    val byId = Builder.build(branchingDecl).nodes.iterator.map(p => p.node.id -> p).toMap
    byId.foreach { case (id, p) =>
      withClue(s"node $id footprint: ") {
        p.footprint shouldBe Footprint.compute(branchingDecl.tacticNodes.find(_.id == id).get)
      }
    }
  }

  it should "attach each node's branch path by id (root '*', child 0 '0', child 1 '1')" in {
    val byId = Builder.build(branchingDecl).nodes.iterator.map(p => p.node.id -> p.branchPath).toMap
    byId(5) shouldBe BranchPath(List("*"))   // branching root
    byId(2) shouldBe BranchPath(List("0"))   // childIds(0) of root
    byId(6) shouldBe BranchPath(List("1"))   // childIds(1) of root
  }

  it should "resolve root_obligation by id even when the root is not first in the list" in {
    // root_tactic_id = 5, but node 5 sits at index 1 of the scrambled list.
    Builder.build(branchingDecl).rootObligation shouldBe obl("G", hyp("xs", "List α"))
  }

  // ── fail-fast ─────────────────────────────────────────────────────────────────

  "Builder.build (degenerate)" should "fail fast when root_tactic_id names no node" in {
    val decl = Declaration("bad", "stmt", 99,
      List(node(0, "exact h", obl("P", hyp("h", "P")), Nil, sum(List("h")), None, Nil)))
    an [Exception] should be thrownBy Builder.build(decl)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP B — buildFile: file-level mapping
  // ═══════════════════════════════════════════════════════════════════════════

  private def stubDecl(name: String): Declaration =
    Declaration(name, s"theorem $name : P", 0,
      List(node(0, "exact h", obl("P", hyp("h", "P")), Nil, sum(List("h")), None, Nil)))

  "Builder.buildFile" should "preserve the source_file" in {
    Builder.buildFile(LeanProofTrace("LeanSrc/foo.lean", List(stubDecl("a")))).sourceFile shouldBe
      "LeanSrc/foo.lean"
  }

  it should "build one POG per declaration, preserving order" in {
    val trace = LeanProofTrace("f.lean", List(stubDecl("a"), stubDecl("b"), stubDecl("c")))
    Builder.buildFile(trace).pogs.map(_.declName) shouldBe List("a", "b", "c")
  }

  it should "map an empty declarations list to an empty pogs list" in {
    val pf = Builder.buildFile(LeanProofTrace("f.lean", Nil))
    pf.pogs       shouldBe empty
    pf.sourceFile shouldBe "f.lean"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP C — golden: the real prop_14 tree through the full Builder pipeline
  // ═══════════════════════════════════════════════════════════════════════════
  //
  //   0 induction xs   → {1 nil, 2 cons}      ["*"]
  //   1 simp [filter]  (nil leaf)             ["0"]
  //   2 simp [filter]  → 3                     ["1"]
  //   3 split_ifs      → {4, 6}                ["1*"]
  //   4 simp           → 5                      ["1","0"]
  //   5 exact ih       (leaf)                   ["1","0"]
  //   6 exact ih       (leaf)                   ["1","1"]
  //
  //   Edges (cross-checked against the DependencyTest golden): goal threading
  //   0→2→3→4 (modify) and the induction var reaching each `exact ih` (use).

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  private lazy val prop14: ProofOrderingGraph =
    Builder.build(Parser.parseFile(fixture).declarations.head)

  "Builder.build (golden prop_14)" should "guard against fixture drift" in {
    prop14.declName       shouldBe "prop_14"
    prop14.nodes.length   shouldBe 7
  }

  it should "match the hand-derived edge set" in {
    prop14.edges.toSet shouldBe Set(
      PogEdge(0, 2, ModifyEdge),
      PogEdge(2, 3, ModifyEdge),
      PogEdge(3, 4, ModifyEdge),
      PogEdge(0, 5, UseEdge),
      PogEdge(0, 6, UseEdge)
    )
  }

  it should "surface the hand-derived branch paths" in {
    val bp = prop14.nodes.iterator.map(p => p.node.id -> p.branchPath.segments).toMap
    bp(0) shouldBe List("*")
    bp(1) shouldBe List("0")
    bp(2) shouldBe List("1")
    bp(3) shouldBe List("1*")
    bp(5) shouldBe List("1", "0")
    bp(6) shouldBe List("1", "1")
  }
