import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import java.nio.file.*

/** Tests for Serializer.main — the public entry point that drives all private helpers.
 *
 *  Since every internal function (toHyp, toObl, toSum, reconstructTree, toFragment,
 *  the RawNode Reader, and the LemmaObj Writer) is private, they are exercised
 *  indirectly: we write a segments JSON to a temp file, call main, and assert on
 *  the produced lemmas JSON.  Each test targets a distinct aspect of the pipeline.
 */
class SerializerTest extends AnyFlatSpec with Matchers:

  // ── helper: run Serializer.main with an in-memory JSON string ─────────────
  private def run(inputJson: String): ujson.Value =
    val inFile  = Files.createTempFile("seg_", ".json")
    val outFile = Files.createTempFile("lem_", ".json")
    try
      Files.writeString(inFile, inputJson)
      Serializer.main(Array(inFile.toString, outFile.toString))
      ujson.read(Files.readString(outFile))
    finally
      Files.deleteIfExists(inFile)
      Files.deleteIfExists(outFile)

  // Convenience accessors on the returned JSON
  private def lemmas(v: ujson.Value): ujson.Arr  = v("lemmas").arr
  private def lemma0(v: ujson.Value): ujson.Value = lemmas(v)(0)

  // ── JSON building blocks ───────────────────────────────────────────────────
  // These mirror the segments.schema.json wire format (snake_case, "type" key).

  private def wHyp(name: String, typ: String) =
    ujson.Obj("name" -> name, "type" -> typ)

  private def wObl(hyps: List[ujson.Value], goal: String) =
    ujson.Obj("hypotheses" -> ujson.Arr(hyps*), "goal" -> goal)

  private def wSum(used: List[String], maps: List[ujson.Value]) =
    ujson.Obj("directly_used" -> ujson.Arr(used.map(ujson.Str(_))*),
              "dependency_maps" -> ujson.Arr(maps*))

  private def holeNode(id: Int, holeId: String, parentId: Option[Int], obl: ujson.Value) =
    ujson.Obj(
      "id" -> id, "kind" -> "hole", "hole_id" -> holeId,
      "parent_id" -> parentId.map(ujson.Num(_)).getOrElse(ujson.Null),
      "child_ids" -> ujson.Arr(),
      "obligation" -> obl
    )

  private def leafNode(id: Int, tactic: String, parentId: Option[Int],
                       obl: ujson.Value, sum: ujson.Value) =
    ujson.Obj(
      "id" -> id, "kind" -> "leaf", "tactic_text" -> tactic,
      "parent_id" -> parentId.map(ujson.Num(_)).getOrElse(ujson.Null),
      "child_ids" -> ujson.Arr(),
      "obligation" -> obl, "summary" -> sum
    )

  private def compositeNode(id: Int, tactic: String, parentId: Option[Int],
                             childIds: List[Int], obl: ujson.Value,
                             outObls: List[ujson.Value], sum: ujson.Value) =
    ujson.Obj(
      "id" -> id, "kind" -> "node", "tactic_text" -> tactic,
      "parent_id" -> parentId.map(ujson.Num(_)).getOrElse(ujson.Null),
      "child_ids" -> ujson.Arr(childIds.map(ujson.Num(_))*),
      "obligation" -> obl,
      "output_obligations" -> ujson.Arr(outObls*),
      "summary" -> sum
    )

  private def fragment(id: Int, src: String, decl: String,
                       rootId: Int, rootObl: ujson.Value,
                       nodes: List[ujson.Value]) =
    ujson.Obj(
      "fragment_id" -> id, "source_file" -> src, "decl_name" -> decl,
      "root_node_id" -> rootId, "root_obligation" -> rootObl,
      "nodes" -> ujson.Arr(nodes*)
    )

  private def segments(frags: List[ujson.Value]) =
    ujson.Obj("fragments" -> ujson.Arr(frags*)).render()

  // ═══════════════════════════════════════════════════════════════════════════
  // Hole fragment — exercises: RawHole reader, reconstructTree (hole branch),
  //                            toObl, toFragment, LemmaObj writer
  // ═══════════════════════════════════════════════════════════════════════════
  "Serializer.main" should "parse a single-hole fragment and emit correct lemma fields" in {
    // Hole tree: Lem = goal = "P", support = ∅, body="P", conclusion="P"
    val oblJson = wObl(Nil, "P")
    val input = segments(List(
      fragment(0, "Test.lean", "test_hole", 0, oblJson,
               List(holeNode(0, "ℓ1", None, oblJson)))
    ))
    val out = lemma0(run(input))
    out("fragment_id").num.toInt shouldBe 0
    out("source_file").str       shouldBe "Test.lean"
    out("decl_name").str         shouldBe "test_hole"
    out("premises").arr          shouldBe empty
    out("body").str              shouldBe "P"
    out("conclusion").str        shouldBe "P"
    out("statement").str         shouldBe "(h1 : P) : P"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Leaf fragment — exercises: RawLeaf reader, directly_used → Set conversion,
  //                            toSum, body="True" path in constructLemma
  // ═══════════════════════════════════════════════════════════════════════════
  it should "parse a single-leaf fragment: body=True, premises from support, statement wraps premise" in {
    // Leaf with directly_used=[h1] → support={h1} → premises=["h1 : Nat"]
    // body="True" → dropped from statement → "(h1 : Nat) → P"
    val h1 = wHyp("h1","Nat")
    val oblJson = wObl(List(h1), "P")
    val sum     = wSum(List("h1"), Nil)
    val input = segments(List(
      fragment(1, "Test.lean", "test_leaf", 0, oblJson,
               List(leafNode(0, "exact h1", None, oblJson, sum)))
    ))
    val out = lemma0(run(input))
    out("premises").arr.map(_.str).toList shouldBe List("h1 : Nat")
    out("body").str                       shouldBe "True"
    out("conclusion").str                 shouldBe "P"
    out("statement").str                  shouldBe "(h1 : Nat) : P"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Composite fragment — exercises: RawComposite reader, reconstructTree
  //                     (recursively builds children from child_ids),
  //                     output_obligations, computeLem on a Node with two holes
  // ═══════════════════════════════════════════════════════════════════════════
  it should "reconstruct a node-with-two-holes tree and compute Lem as conjunction of hole goals" in {
    // Node(constructor): U={}, no dep-maps, children=[Hole(P), Hole(Q)]
    // Lem = "P ∧ Q", support=∅, premises=[], statement="P ∧ Q → P ∧ Q"
    val rootObl = wObl(Nil, "P ∧ Q")
    val oblP    = wObl(Nil, "P")
    val oblQ    = wObl(Nil, "Q")
    val sum     = wSum(Nil, List(ujson.Obj(), ujson.Obj()))
    val input = segments(List(
      fragment(2, "Test.lean", "test_node", 0, rootObl, List(
        compositeNode(0, "constructor", None, List(1,2), rootObl, List(oblP, oblQ), sum),
        holeNode(1, "ℓ1", Some(0), oblP),
        holeNode(2, "ℓ2", Some(0), oblQ)
      ))
    ))
    val out = lemma0(run(input))
    out("premises").arr          shouldBe empty
    out("body").str              shouldBe "P ∧ Q"
    out("conclusion").str        shouldBe "P ∧ Q"
    out("statement").str         shouldBe "(h1 : P ∧ Q) : P ∧ Q"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Nodes listed out-of-order in the flat array — exercises that reconstructTree
  // uses the Map[Int,RawNode] lookup and is not sensitive to list order
  // ═══════════════════════════════════════════════════════════════════════════
  it should "reconstruct the tree correctly when the flat node list is in non-ID order" in {
    // Same fragment as above but nodes listed [hole2, hole1, root] instead of [root, hole1, hole2]
    val rootObl = wObl(Nil, "A ∧ B")
    val oblA    = wObl(Nil, "A")
    val oblB    = wObl(Nil, "B")
    val sum     = wSum(Nil, List(ujson.Obj(), ujson.Obj()))
    val input = segments(List(
      fragment(3, "Test.lean", "test_order", 0, rootObl, List(
        holeNode(2, "ℓ2", Some(0), oblB),           // listed first
        holeNode(1, "ℓ1", Some(0), oblA),           // listed second
        compositeNode(0, "constructor", None, List(1,2), rootObl, List(oblA, oblB), sum)  // root last
      ))
    ))
    val out = lemma0(run(input))
    out("body").str      shouldBe "A ∧ B"
    out("statement").str shouldBe "(h1 : A ∧ B) : A ∧ B"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Dependency maps — exercises: dependency_maps List[String] → Set conversion,
  //                              non-trivial support computation via π
  // ═══════════════════════════════════════════════════════════════════════════
  it should "apply dependency maps to pull child support into the parent support" in {
    // Root Γ=[h1:Nat, h2:Bool], goal="P"
    // Node: U={h1}, π₁={h2→["h1"]}, child=Leaf(directly_used=["h2"])
    // support: A_child={h2}, π₁(h2)={h1}, pulled={h1}, total={h1}∪{h1}={h1}
    // scope_vars=[], premises=["h1 : Nat"], body="True", statement="(h1 : Nat) : P"
    // h2 is not in support and "h2" is not referenced in conclusion "P" → dropped from scope_vars.
    val h1 = wHyp("h1","Nat")
    val h2 = wHyp("h2","Bool")
    val rootObl = wObl(List(h1, h2), "P")
    val childObl = wObl(List(h1, h2), "P")
    val nodeSummary = wSum(List("h1"), List(ujson.Obj("h2" -> ujson.Arr(ujson.Str("h1")))))
    val leafSummary = wSum(List("h2"), Nil)
    val input = segments(List(
      fragment(4, "Test.lean", "test_depmap", 0, rootObl, List(
        compositeNode(0, "intro", None, List(1), rootObl, List(childObl), nodeSummary),
        leafNode(1, "exact h2", Some(0), childObl, leafSummary)
      ))
    ))
    val out = lemma0(run(input))
    out("scope_vars").arr.map(_.str).toList shouldBe Nil
    out("premises").arr.map(_.str).toList   shouldBe List("h1 : Nat")
    out("body").str                         shouldBe "True"
    out("statement").str                    shouldBe "(h1 : Nat) : P"
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Multiple fragments — exercises: the fragments loop in main, each fragment
  //                                 independently processed, correct output count
  // ═══════════════════════════════════════════════════════════════════════════
  it should "process multiple fragments and emit one lemma per fragment in order" in {
    val obl0 = wObl(Nil, "True")
    val obl1 = wObl(List(wHyp("h","Nat")), "False")
    val sum1 = wSum(List("h"), Nil)
    val input = segments(List(
      fragment(0, "A.lean", "lemA", 0, obl0, List(holeNode(0, "ℓ", None, obl0))),
      fragment(1, "B.lean", "lemB", 0, obl1, List(leafNode(0, "exact h", None, obl1, sum1)))
    ))
    val out = run(input)
    lemmas(out).value.length shouldBe 2
    lemmas(out)(0)("fragment_id").num.toInt shouldBe 0
    lemmas(out)(0)("decl_name").str         shouldBe "lemA"
    lemmas(out)(1)("fragment_id").num.toInt shouldBe 1
    lemmas(out)(1)("decl_name").str         shouldBe "lemB"
    lemmas(out)(1)("premises").arr.map(_.str).toList shouldBe List("h : Nat")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Error handling — exercises: the unknown-kind branch in the RawNode reader
  // ═══════════════════════════════════════════════════════════════════════════
  it should "throw an exception when a node has an unrecognised 'kind' value" in {
    val badNode = ujson.Obj(
      "id" -> 0, "kind" -> "unknown_kind",
      "parent_id" -> ujson.Null, "child_ids" -> ujson.Arr(),
      "obligation" -> wObl(Nil, "P")
    )
    val input = segments(List(
      fragment(0, "T.lean", "f", 0, wObl(Nil,"P"), List(badNode))
    ))
    an [Exception] should be thrownBy run(input)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // End-to-end integration — all node kinds, dependency maps, new hypotheses,
  //                          and statement assembly in one realistic fragment
  // ═══════════════════════════════════════════════════════════════════════════
  it should "produce the correct lemma for a fragment combining all node kinds and non-trivial support" in {
    // Fragment models a proof step where:
    //   - Root tactic splits goal "P ∧ Q" into two sub-goals using "constructor"
    //   - Left branch closes immediately with "exact h1" (leaf); U_left={h1}
    //   - Right branch is left open as a hole
    //   - Root summary: U={}, π₁={h1→{h1}}, π₂={}
    //
    // Context at root: Γ=[h1:Nat, h2:Bool], goal="P ∧ Q"
    //
    // Support computation:
    //   A_leaf = {h1},  pulled through π₁={h1→{h1}} → {h1}
    //   A_hole = ∅,     pulled through π₂={}          → ∅
    //   A_root = U={} ∪ {h1} ∪ ∅ = {h1}
    //
    // Lem computation (Node):
    //   Leaf child → ⊤ (filtered out)
    //   Hole child → Some("Q"), output obl has same hyps as parent → newHyps=[]
    //   parts = ["Q"]
    //   body = "Q"
    //
    // Expected lemma:
    //   scope_vars = []  (h2 not in support and "h2" unreachable from "P ∧ Q" or body "Q")
    //   premises   = ["h1 : Nat"]
    //   body       = "Q"
    //   conclusion = "P ∧ Q"
    //   statement  = "(h1 : Nat) (h2 : Q) : P ∧ Q"  (h1 is taken → fresh body binder = h2)
    val h1      = wHyp("h1","Nat")
    val h2      = wHyp("h2","Bool")
    val rootObl = wObl(List(h1, h2), "P ∧ Q")
    val oblP    = wObl(List(h1, h2), "P")
    val oblQ    = wObl(List(h1, h2), "Q")

    // Root node summary: U={}, π₁={h1→[h1]}, π₂={}
    val rootSum = wSum(
      Nil,
      List(
        ujson.Obj("h1" -> ujson.Arr(ujson.Str("h1"))),
        ujson.Obj()
      )
    )
    val leafSum = wSum(List("h1"), Nil)

    val input = segments(List(
      fragment(10, "Conjunction.lean", "and_intro", 0, rootObl, List(
        compositeNode(0, "constructor", None, List(1,2), rootObl, List(oblP, oblQ), rootSum),
        leafNode(1, "exact h1", Some(0), oblP, leafSum),
        holeNode(2, "ℓ_Q", Some(0), oblQ)
      ))
    ))

    val out = lemma0(run(input))
    out("fragment_id").num.toInt          shouldBe 10
    out("source_file").str                shouldBe "Conjunction.lean"
    out("decl_name").str                  shouldBe "and_intro"
    out("scope_vars").arr.map(_.str).toList shouldBe Nil
    out("premises").arr.map(_.str).toList   shouldBe List("h1 : Nat")
    out("body").str                         shouldBe "Q"
    out("conclusion").str                   shouldBe "P ∧ Q"
    // Body has no top-level `→` → lifted as a single binder. h1 is taken → fresh name = h2.
    out("statement").str                    shouldBe "(h1 : Nat) (h2 : Q) : P ∧ Q"
  }
