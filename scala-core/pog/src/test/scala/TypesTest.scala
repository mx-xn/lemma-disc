import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import upickle.default.*

/** Tests for `Types.scala` — verifies the upickle `ReadWriter` instances
 *  defined alongside each ADT.  Covers both:
 *    1. trace-input types  (mirror phase-1 JSON: trace.schema.json)
 *    2. POG-output types   (mirror pog.schema.json)
 *
 *  Each non-trivial type is checked on two axes:
 *    - JSON SHAPE  — exact keys / value layout on the wire
 *    - ROUND-TRIP  — write(read(write(x))) is the identity
 */
class TypesTest extends AnyFlatSpec with Matchers:

  // ── helpers ────────────────────────────────────────────────────────────────

  private def roundTrip[T: ReadWriter](value: T): T = read[T](write(value))
  private def shapeOf[T: ReadWriter](value: T): ujson.Value = ujson.read(write(value))

  // ═══════════════════════════════════════════════════════════════════════════
  // PART A — trace-input ADTs (mirror phase 1 JSON)
  // ═══════════════════════════════════════════════════════════════════════════

  // ── Hypothesis ─────────────────────────────────────────────────────────────
  // The Scala field is named `type` (reserved word, backtick-escaped); on the
  // wire it must be the JSON key "type".

  "Hypothesis" should "read the JSON key 'type' into the (backticked) `type` field" in {
    val h = read[Hypothesis]("""{"name": "h", "type": "Nat"}""")
    h.name        shouldBe "h"
    h.`type`      shouldBe "Nat"
  }

  it should "write the JSON key 'type' (NOT 'typ' or '`type`')" in {
    val j = shapeOf(Hypothesis("h", "Nat"))
    j.obj.keys.toSet shouldBe Set("name", "type")
    j("type").str    shouldBe "Nat"
  }

  it should "round-trip Unicode in both name and type (α, →)" in {
    val h = Hypothesis("α", "α → Bool")
    roundTrip(h) shouldBe h
  }

  it should "round-trip empty strings (defensive — schema doesn't ban them)" in {
    val h = Hypothesis("", "")
    roundTrip(h) shouldBe h
  }

  // ── Obligation ─────────────────────────────────────────────────────────────

  "Obligation" should "read with an empty hypotheses list" in {
    read[Obligation]("""{"hypotheses": [], "goal": "P"}""") shouldBe
      Obligation(Nil, "P")
  }

  it should "preserve hypothesis ORDER through a round-trip" in {
    val obl = Obligation(
      List(Hypothesis("h1", "P"), Hypothesis("h2", "Q"), Hypothesis("h3", "R")),
      "P ∧ Q ∧ R"
    )
    val rt = roundTrip(obl)
    rt                         shouldBe obl
    rt.hypotheses.map(_.name)  shouldBe List("h1", "h2", "h3")  // not a set
  }

  it should "round-trip a realistic obligation with Unicode types" in {
    val obl = Obligation(
      List(
        Hypothesis("α",  "Type u_1"),
        Hypothesis("p",  "α → Bool"),
        Hypothesis("xs", "List α"),
        Hypothesis("ys", "List α")
      ),
      "filter p (xs ++ ys) = filter p xs ++ filter p ys"
    )
    roundTrip(obl) shouldBe obl
  }

  // ── TacticSummary ──────────────────────────────────────────────────────────

  "TacticSummary" should "read snake_case JSON keys" in {
    val s = read[TacticSummary](
      """{"directly_used": ["h1"], "dependency_maps": [{"h2": ["h1"]}]}""")
    s.directlyUsed     shouldBe List("h1")
    s.dependencyMaps   shouldBe List(Map("h2" -> List("h1")))
  }

  it should "write snake_case JSON keys (not camelCase)" in {
    val j = shapeOf(TacticSummary(List("h"), Nil))
    j.obj.keys.toSet shouldBe Set("directly_used", "dependency_maps")
  }

  it should "round-trip an empty summary (leaf-node case)" in {
    val s = TacticSummary(Nil, Nil)
    roundTrip(s) shouldBe s
  }

  it should "round-trip dependency_maps with empty inner lists" in {
    // newly-introduced hyp with no parent dependencies → maps to []
    val s = TacticSummary(Nil, List(Map("x" -> Nil, "ih" -> Nil)))
    roundTrip(s) shouldBe s
  }

  it should "preserve the ORDER of dependency_maps (co-indexed with branches)" in {
    // Two branches: each map must end up at the right index after round-trip
    val s = TacticSummary(
      List("xs"),
      List(
        Map("α" -> List("α"), "p"  -> List("p"),  "ys" -> List("ys")),
        Map("α" -> List("α"), "x"  -> List("xs"), "xs" -> List("xs"), "ih" -> List("xs"))
      )
    )
    val rt = roundTrip(s)
    rt                          shouldBe s
    rt.dependencyMaps.length    shouldBe 2
    rt.dependencyMaps(0).keySet shouldBe Set("α", "p", "ys")
    rt.dependencyMaps(1).keySet shouldBe Set("α", "x", "xs", "ih")
  }

  // ── TacticNode ─────────────────────────────────────────────────────────────

  "TacticNode" should "use all the expected snake_case JSON keys" in {
    val n = TacticNode(0, "intro h",
      Obligation(Nil, "P → P"),
      List(Obligation(List(Hypothesis("h", "P")), "P")),
      TacticSummary(Nil, List(Map("h" -> List("h")))),
      None, List(1))
    val j = shapeOf(n)
    j.obj.keys.toSet shouldBe Set(
      "id", "tactic_text", "input_obligation", "output_obligations",
      "summary", "parent_id", "child_ids"
    )
  }

  it should "map parent_id: null ↔ None (root node)" in {
    val n = TacticNode(0, "tac", Obligation(Nil, "P"), Nil,
      TacticSummary(Nil, Nil), None, Nil)
    val j = shapeOf(n)
    j("parent_id")             shouldBe ujson.Null
    roundTrip(n).parentId      shouldBe None
  }

  it should "map parent_id: <int> ↔ Some(int) (non-root node)" in {
    val n = TacticNode(5, "tac", Obligation(Nil, "P"), Nil,
      TacticSummary(Nil, Nil), Some(2), Nil)
    val j = shapeOf(n)
    j("parent_id").num.toInt           shouldBe 2
    roundTrip(n).parentId              shouldBe Some(2)
  }

  it should "round-trip a LEAF (empty output_obligations & child_ids)" in {
    val n = TacticNode(6, "exact ih",
      Obligation(List(Hypothesis("ih", "P = Q")), "P = Q"),
      Nil,
      TacticSummary(List("ih"), Nil),
      Some(3), Nil)
    val rt = roundTrip(n)
    rt                       shouldBe n
    rt.outputObligations     shouldBe empty
    rt.childIds              shouldBe empty
    rt.summary.dependencyMaps shouldBe empty
  }

  it should "round-trip a BRANCHING node (multiple outputs co-indexed with child_ids)" in {
    val obl1 = Obligation(Nil, "P []")
    val obl2 = Obligation(List(Hypothesis("ih", "P xs")), "P (x :: xs)")
    val n = TacticNode(0, "induction xs",
      Obligation(List(Hypothesis("xs", "List α")), "P xs"),
      List(obl1, obl2),
      TacticSummary(List("xs"), List(Map(), Map("ih" -> List("xs")))),
      None, List(1, 4))
    val rt = roundTrip(n)
    rt                              shouldBe n
    rt.outputObligations.length     shouldBe 2
    rt.childIds                     shouldBe List(1, 4)  // order matters
    rt.summary.dependencyMaps.length shouldBe 2
  }

  it should "round-trip a LINEAR-CHAIN intermediate node (1 output, 1 child)" in {
    val n = TacticNode(2, "rw h",
      Obligation(List(Hypothesis("h", "a = b")), "P a"),
      List(Obligation(List(Hypothesis("h", "a = b")), "P b")),
      TacticSummary(List("h"), List(Map("h" -> List("h")))),
      Some(1), List(3))
    roundTrip(n) shouldBe n
  }

  // ── Declaration ────────────────────────────────────────────────────────────

  "Declaration" should "use snake_case for root_tactic_id and tactic_nodes" in {
    val d = Declaration("foo", "theorem foo : P", 0,
      List(TacticNode(0, "exact h",
        Obligation(List(Hypothesis("h", "P")), "P"),
        Nil, TacticSummary(List("h"), Nil), None, Nil)))
    val j = shapeOf(d)
    j.obj.keys.toSet shouldBe Set("name", "statement", "root_tactic_id", "tactic_nodes")
    roundTrip(d)     shouldBe d
  }

  it should "round-trip with multiple tactic_nodes in a declaration" in {
    val n0 = TacticNode(0, "intro h",
      Obligation(Nil, "P → P"),
      List(Obligation(List(Hypothesis("h", "P")), "P")),
      TacticSummary(Nil, List(Map("h" -> List("h")))),
      None, List(1))
    val n1 = TacticNode(1, "exact h",
      Obligation(List(Hypothesis("h", "P")), "P"),
      Nil, TacticSummary(List("h"), Nil), Some(0), Nil)
    val d = Declaration("identity", "theorem id : P → P", 0, List(n0, n1))
    val rt = roundTrip(d)
    rt                          shouldBe d
    rt.tacticNodes.map(_.id)    shouldBe List(0, 1)  // order preserved
  }

  // ── LeanProofTrace ─────────────────────────────────────────────────────────

  "LeanProofTrace" should "use snake_case for source_file" in {
    val t = LeanProofTrace("LeanSrc/foo.lean", Nil)
    shapeOf(t).obj.keys.toSet shouldBe Set("source_file", "declarations")
  }

  it should "round-trip an empty declarations list" in {
    val t = LeanProofTrace("foo.lean", Nil)
    roundTrip(t) shouldBe t
  }

  it should "round-trip multiple declarations in order" in {
    val d1 = Declaration("a", "stmt_a", 0, Nil)
    val d2 = Declaration("b", "stmt_b", 0, Nil)
    val t  = LeanProofTrace("foo.lean", List(d1, d2))
    val rt = roundTrip(t)
    rt                            shouldBe t
    rt.declarations.map(_.name)   shouldBe List("a", "b")
  }

  it should "parse a realistic trace fragment with leaves, branching, ρ, and Unicode" in {
    // Mirrors the shape of /nas/lemma-disc/data/traces/MiniCodePropsLeanSrc/Examples.json:
    // an `induction xs` tactic with two branches (nil and cons).
    val json = """{
      "source_file": "LeanSrc/Examples.lean",
      "declarations": [{
        "name": "prop_14",
        "statement": "theorem prop_14 : ...",
        "root_tactic_id": 0,
        "tactic_nodes": [
          {
            "id": 0,
            "tactic_text": "induction xs with\n| nil => _*_\n| cons x xs ih => _*_",
            "input_obligation": {
              "hypotheses": [
                {"name": "α",  "type": "Type u_1"},
                {"name": "p",  "type": "α → Bool"},
                {"name": "xs", "type": "List α"},
                {"name": "ys", "type": "List α"}
              ],
              "goal": "filter p (xs ++ ys) = filter p xs ++ filter p ys"
            },
            "output_obligations": [
              {
                "hypotheses": [
                  {"name": "α",  "type": "Type u_1"},
                  {"name": "p",  "type": "α → Bool"},
                  {"name": "ys", "type": "List α"}
                ],
                "goal": "filter p ([] ++ ys) = filter p [] ++ filter p ys"
              },
              {
                "hypotheses": [
                  {"name": "α",  "type": "Type u_1"},
                  {"name": "p",  "type": "α → Bool"},
                  {"name": "ys", "type": "List α"},
                  {"name": "x",  "type": "α"},
                  {"name": "xs", "type": "List α"},
                  {"name": "ih", "type": "filter p (xs ++ ys) = filter p xs ++ filter p ys"}
                ],
                "goal": "filter p (x :: xs ++ ys) = filter p (x :: xs) ++ filter p ys"
              }
            ],
            "summary": {
              "directly_used": ["xs"],
              "dependency_maps": [
                {"α": ["α"], "p": ["p"], "ys": ["ys"]},
                {"α": ["α"], "p": ["p"], "ys": ["ys"],
                 "x": ["xs"], "xs": ["xs"], "ih": ["xs"]}
              ]
            },
            "parent_id": null,
            "child_ids": [1, 2]
          }
        ]
      }]
    }"""
    val t = read[LeanProofTrace](json)
    t.sourceFile                       shouldBe "LeanSrc/Examples.lean"
    t.declarations.length              shouldBe 1
    val d = t.declarations.head
    d.name                             shouldBe "prop_14"
    d.rootTacticId                     shouldBe 0
    d.tacticNodes.length               shouldBe 1
    val n = d.tacticNodes.head
    n.id                               shouldBe 0
    n.parentId                         shouldBe None
    n.childIds                         shouldBe List(1, 2)
    n.outputObligations.length         shouldBe 2
    n.outputObligations(0).hypotheses.length shouldBe 3
    n.outputObligations(1).hypotheses.length shouldBe 6
    n.summary.directlyUsed             shouldBe List("xs")
    n.summary.dependencyMaps.length    shouldBe 2
    n.summary.dependencyMaps(1)("ih")  shouldBe List("xs")
  }

  it should "do a deep read→write→read round-trip on the realistic fragment" in {
    val json = """{
      "source_file": "f.lean",
      "declarations": [{
        "name": "t", "statement": "stmt", "root_tactic_id": 0,
        "tactic_nodes": [
          {"id": 0, "tactic_text": "induction xs",
           "input_obligation": {"hypotheses": [{"name": "xs", "type": "List α"}], "goal": "P xs"},
           "output_obligations": [
             {"hypotheses": [], "goal": "P []"},
             {"hypotheses": [{"name": "ih", "type": "P xs"}], "goal": "P (x::xs)"}
           ],
           "summary": {"directly_used": ["xs"], "dependency_maps": [{}, {"ih": ["xs"]}]},
           "parent_id": null, "child_ids": [1, 2]}
        ]
      }]
    }"""
    val once  = read[LeanProofTrace](json)
    val twice = read[LeanProofTrace](write(once))
    twice shouldBe once
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PART B — POG-output ADTs (mirror pog.schema.json)
  // ═══════════════════════════════════════════════════════════════════════════

  // ── Footprint ──────────────────────────────────────────────────────────────

  "Footprint" should "use snake_case JSON keys" in {
    val f = Footprint(Set("h1"), Set("h2"), modifiesGoal = true, Nil)
    shapeOf(f).obj.keys.toSet shouldBe
      Set("uses", "modifies_hyps", "modifies_goal", "rho")
  }

  it should "serialize Set[String] fields as JSON arrays" in {
    val f = Footprint(Set("h1", "h2"), Set("h3"), modifiesGoal = false, Nil)
    val j = shapeOf(f)
    j("uses").arr.map(_.str).toSet           shouldBe Set("h1", "h2")
    j("modifies_hyps").arr.map(_.str).toSet  shouldBe Set("h3")
    j("modifies_goal").bool                  shouldBe false        // JSON boolean, not string
  }

  it should "round-trip an all-empty footprint (leaf-like node)" in {
    val f = Footprint(Set.empty, Set.empty, modifiesGoal = false, Nil)
    roundTrip(f) shouldBe f
  }

  it should "round-trip rho with the literal '⊢' (goal-slot) entries" in {
    val f = Footprint(
      uses          = Set("h"),
      modifiesHyps  = Set.empty,
      modifiesGoal  = true,
      rho           = List(Map("h" -> Set("h"), "⊢" -> Set("⊢")))
    )
    val rt = roundTrip(f)
    rt                       shouldBe f
    rt.rho.head.keys         should contain ("⊢")
    rt.rho.head("⊢")         shouldBe Set("⊢")
  }

  it should "round-trip rho with multiple branches (one map per branch)" in {
    val f = Footprint(
      uses          = Set.empty,
      modifiesHyps  = Set("xs"),
      modifiesGoal  = false,
      rho           = List(
        Map("α" -> Set("α"), "p" -> Set("p"), "ys" -> Set("ys")),
        Map("α" -> Set("α"), "x" -> Set("x"), "xs" -> Set("xs"))
      )
    )
    val rt = roundTrip(f)
    rt              shouldBe f
    rt.rho.length   shouldBe 2  // branch order matters even if Set values are unordered
  }

  it should "round-trip rho whose values are empty sets (name dropped, no successor)" in {
    val f = Footprint(Set.empty, Set("xs"), false, List(Map("xs" -> Set.empty)))
    roundTrip(f) shouldBe f
  }

  // ── BranchPath ─────────────────────────────────────────────────────────────
  // Schema: branch_path is a bare JSON array of strings — NOT wrapped in an
  // object. The Scala case class wraps a List[String], so the ReadWriter
  // must lift/lower across that wrapper.

  "BranchPath" should "serialize as a BARE JSON array (not {segments: [...]})" in {
    val j = shapeOf(BranchPath(List("1", "0*")))
    j shouldBe a [ujson.Arr]
    j.arr.map(_.str).toList shouldBe List("1", "0*")
  }

  it should "round-trip an empty path (linear-chain non-branching node)" in {
    val bp = BranchPath(Nil)
    roundTrip(bp)            shouldBe bp
    shapeOf(bp).arr          shouldBe empty
  }

  it should "round-trip a single '*' (branching root, no branching ancestors)" in {
    // Note: ["*"] is semantically distinct from [] — it tags `n` as branching.
    roundTrip(BranchPath(List("*")))  shouldBe BranchPath(List("*"))
  }

  it should "round-trip the doc's two-level example ['1', '0*']" in {
    roundTrip(BranchPath(List("1", "0*"))) shouldBe BranchPath(List("1", "0*"))
  }

  it should "read a bare JSON array directly" in {
    read[BranchPath]("""["0", "1", "0*"]""") shouldBe BranchPath(List("0", "1", "0*"))
  }

  // ── EdgeKind ───────────────────────────────────────────────────────────────
  // Schema: kind is one of the bare strings "modify" or "use". upickle's
  // default sealed-trait encoding ("{$type: ...}") is NOT what we want.

  "EdgeKind" should "serialize ModifyEdge as the bare string \"modify\"" in {
    shapeOf[EdgeKind](ModifyEdge) shouldBe ujson.Str("modify")
  }

  it should "serialize UseEdge as the bare string \"use\"" in {
    shapeOf[EdgeKind](UseEdge) shouldBe ujson.Str("use")
  }

  it should "read \"modify\" as ModifyEdge" in {
    read[EdgeKind]("\"modify\"") shouldBe ModifyEdge
  }

  it should "read \"use\" as UseEdge" in {
    read[EdgeKind]("\"use\"") shouldBe UseEdge
  }

  it should "throw on an unknown EdgeKind string" in {
    an [Exception] should be thrownBy read[EdgeKind]("\"unknown\"")
  }

  it should "NOT emit upickle's $type discriminator" in {
    val written = write[EdgeKind](ModifyEdge)
    written should not include "$type"
    written should not include "ModifyEdge"
    written shouldBe "\"modify\""
  }

  // ── PogEdge ────────────────────────────────────────────────────────────────

  "PogEdge" should "use exactly the keys 'from', 'to', 'kind'" in {
    val j = shapeOf(PogEdge(0, 3, ModifyEdge))
    j.obj.keys.toSet shouldBe Set("from", "to", "kind")
  }

  it should "round-trip a ModifyEdge" in {
    val e = PogEdge(0, 3, ModifyEdge)
    val rt = roundTrip(e)
    rt                  shouldBe e
    val j = shapeOf(e)
    j("kind").str       shouldBe "modify"
  }

  it should "round-trip a UseEdge" in {
    val e = PogEdge(2, 5, UseEdge)
    roundTrip(e) shouldBe e
  }

  // ── PogNode (the tricky one — JSON layout is FLAT) ─────────────────────────
  // schema/pog.schema.json:PogNode has all TacticNode fields AND footprint/
  // branch_path at the SAME level — there must be no "node" / "tactic_node"
  // wrapper key, even though the Scala class composes a TacticNode.

  "PogNode" should "serialize FLAT — no 'node' or 'tactic_node' wrapper key" in {
    val tn = TacticNode(0, "intro h", Obligation(Nil, "P"), Nil,
                        TacticSummary(Nil, Nil), None, Nil)
    val fp = Footprint(Set.empty, Set.empty, modifiesGoal = false, Nil)
    val bp = BranchPath(Nil)
    val j  = shapeOf(PogNode(tn, fp, bp))

    j.obj.keys.toSet shouldBe Set(
      "id", "tactic_text", "input_obligation", "output_obligations",
      "summary", "parent_id", "child_ids",                 // TacticNode fields
      "footprint", "branch_path"                            // POG-specific
    )
    // Defensive: explicitly assert NO wrapper
    j.obj.contains("node")         shouldBe false
    j.obj.contains("tactic_node")  shouldBe false
    j.obj.contains("tn")           shouldBe false
  }

  it should "inline TacticNode fields with their snake_case JSON keys" in {
    val tn = TacticNode(7, "rfl",
      Obligation(List(Hypothesis("h", "a = a")), "a = a"),
      Nil, TacticSummary(List("h"), Nil), Some(3), Nil)
    val pn = PogNode(tn,
      Footprint(Set("h"), Set.empty, modifiesGoal = false, Nil),
      BranchPath(List("0")))
    val j  = shapeOf(pn)
    j("id").num.toInt          shouldBe 7
    j("tactic_text").str       shouldBe "rfl"
    j("parent_id").num.toInt   shouldBe 3
    j("child_ids").arr         shouldBe empty
    j("branch_path").arr.map(_.str).toList shouldBe List("0")
    j("footprint")("uses").arr.map(_.str).toSet shouldBe Set("h")
  }

  it should "round-trip a LEAF PogNode" in {
    val tn = TacticNode(0, "rfl", Obligation(Nil, "P = P"), Nil,
                        TacticSummary(Nil, Nil), None, Nil)
    val pn = PogNode(tn,
      Footprint(Set.empty, Set.empty, modifiesGoal = false, Nil),
      BranchPath(Nil))
    roundTrip(pn) shouldBe pn
  }

  it should "round-trip a BRANCHING PogNode with full footprint + branch path" in {
    val obl1 = Obligation(Nil, "P []")
    val obl2 = Obligation(List(Hypothesis("ih", "P xs")), "P (x :: xs)")
    val tn = TacticNode(0, "induction xs",
      Obligation(List(Hypothesis("xs", "List α")), "P xs"),
      List(obl1, obl2),
      TacticSummary(List("xs"), List(Map(), Map("ih" -> List("xs")))),
      None, List(1, 2))
    val fp = Footprint(
      uses         = Set.empty,
      modifiesHyps = Set("xs"),
      modifiesGoal = true,
      rho          = List(
        Map("xs" -> Set.empty,    "⊢" -> Set("⊢")),
        Map("xs" -> Set("xs"),    "⊢" -> Set("⊢"))
      )
    )
    val bp = BranchPath(List("*"))
    val pn = PogNode(tn, fp, bp)
    roundTrip(pn) shouldBe pn
  }

  it should "READ a flat PogNode JSON directly (decoder symmetry)" in {
    val json = """{
      "id": 0, "tactic_text": "rfl",
      "input_obligation": {"hypotheses": [], "goal": "a = a"},
      "output_obligations": [],
      "summary": {"directly_used": [], "dependency_maps": []},
      "parent_id": null, "child_ids": [],
      "footprint": {"uses": [], "modifies_hyps": [], "modifies_goal": false, "rho": []},
      "branch_path": []
    }"""
    val pn = read[PogNode](json)
    pn.node.id              shouldBe 0
    pn.node.tacticText      shouldBe "rfl"
    pn.node.parentId        shouldBe None
    pn.footprint.modifiesGoal shouldBe false
    pn.branchPath.segments  shouldBe empty
  }

  // ── ProofOrderingGraph ─────────────────────────────────────────────────────

  "ProofOrderingGraph" should "use snake_case keys decl_name / root_tactic_id / root_obligation" in {
    val j = shapeOf(ProofOrderingGraph("foo", "stmt", 0, Obligation(Nil, "P"), Nil, Nil))
    j.obj.keys.toSet shouldBe
      Set("decl_name", "statement", "root_tactic_id", "root_obligation", "nodes", "edges")
  }

  it should "round-trip an empty POG (no nodes, no edges)" in {
    val pog = ProofOrderingGraph("foo", "stmt", 0, Obligation(Nil, "P"), Nil, Nil)
    roundTrip(pog) shouldBe pog
  }

  it should "round-trip a complete POG with one node and one edge" in {
    val rootObl = Obligation(List(Hypothesis("h", "P")), "Q")
    val tn      = TacticNode(0, "exact h", rootObl, Nil,
                             TacticSummary(List("h"), Nil), None, Nil)
    val pn      = PogNode(tn,
                          Footprint(Set("h"), Set.empty, modifiesGoal = false, Nil),
                          BranchPath(Nil))
    val edge    = PogEdge(0, 1, UseEdge)
    val pog     = ProofOrderingGraph("foo", "theorem foo : ...", 0,
                                     rootObl, List(pn), List(edge))
    roundTrip(pog) shouldBe pog
  }

  it should "preserve nodes and edges ORDER through a round-trip" in {
    val rootObl = Obligation(Nil, "P")
    def mkPn(id: Int) = PogNode(
      TacticNode(id, s"tac$id", rootObl, Nil, TacticSummary(Nil, Nil), None, Nil),
      Footprint(Set.empty, Set.empty, modifiesGoal = false, Nil),
      BranchPath(Nil)
    )
    val pog = ProofOrderingGraph("d", "stmt", 0, rootObl,
      List(mkPn(0), mkPn(1), mkPn(2)),
      List(PogEdge(0, 1, ModifyEdge), PogEdge(1, 2, UseEdge), PogEdge(0, 2, UseEdge))
    )
    val rt = roundTrip(pog)
    rt                                shouldBe pog
    rt.nodes.map(_.node.id)           shouldBe List(0, 1, 2)
    rt.edges.map(e => (e.from, e.to)) shouldBe List((0,1), (1,2), (0,2))
  }

  // ── PogFile ────────────────────────────────────────────────────────────────

  "PogFile" should "use snake_case key source_file" in {
    val j = shapeOf(PogFile("LeanSrc/foo.lean", Nil))
    j.obj.keys.toSet shouldBe Set("source_file", "pogs")
  }

  it should "round-trip with an empty pogs list" in {
    val pf = PogFile("foo.lean", Nil)
    roundTrip(pf) shouldBe pf
  }

  it should "round-trip with multiple POGs preserving order" in {
    val pf = PogFile("foo.lean", List(
      ProofOrderingGraph("a", "stmt_a", 0, Obligation(Nil, "P"), Nil, Nil),
      ProofOrderingGraph("b", "stmt_b", 0, Obligation(Nil, "Q"), Nil, Nil)
    ))
    val rt = roundTrip(pf)
    rt                       shouldBe pf
    rt.pogs.map(_.declName)  shouldBe List("a", "b")
  }
