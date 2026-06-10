import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Tests for `BranchPath.compute` (Step 5) — the branch path B(a) of paper §2.1.
 *
 *  Paper definition (Definition 2 preamble, §2.1):
 *
 *    "The branch path B(a) of a is the sequence of branch indices chosen at the
 *     branching ancestors of a, with an asterisk suffix `*` appended if a is
 *     itself branching. Tactics lying on a linear chain (no branching ancestors
 *     and not themselves branching) share the same branch path."
 *
 *  where a *branching tactic* is one that emits more than one residual
 *  obligation, and a *branching ancestor* of a is an ancestor that is branching.
 *
 *  `compute` is a pure function of the *tree shape only*: it reads
 *  `outputObligations.size` (to decide branching), `parentId`, and `childIds`
 *  (to recover branch indices). It never inspects obligations' contents or the
 *  tactic summary. Signature:
 *
 *    BranchPath.compute(nodes: List[TacticNode]): Map[Int, BranchPath]
 *
 *  Returns one entry per node id in the input list.
 *
 *  ── RESOLVED DISCREPANCY — `*` placement (do NOT "fix" toward the snippet) ──
 *
 *    The Step-5 CLAUDE.md *code snippet* appends `*` as a SEPARATE list element
 *    (`prefix ++ List("*")`), which would give a branching child-0 node the path
 *    `["0", "*"]`. That is WRONG. Three independent sources — the pog.schema.json
 *    example (`["1", "0*"]`), the `Types.scala` `BranchPath` comment
 *    (`List("1", "0*")`), and the CLAUDE.md design-notes worked table — all say
 *    the `*` is MERGED INTO THE LAST INDEX, giving `["0*"]`. The schema is the
 *    wire contract, so we follow the merge reading (decided in design review,
 *    2026-06-01). Precisely:
 *
 *      indices = branch index at each branching ancestor, root→node order
 *      if a is branching:
 *          if indices.isEmpty  →  List("*")               // e.g. branching root
 *          else                →  indices.init :+ (indices.last + "*")
 *      else                    →  indices
 *
 *    CONSEQUENCE worth its own assertion (Groups 4.3, 8): a branching ancestor
 *    contributes its *plain* index to descendants. A node b with B(b)=["0*"] has
 *    children whose paths start with plain "0" (e.g. ["0","0"]) — the `*`
 *    decorates only b itself and never propagates downward.
 */
class BranchPathTest extends AnyFlatSpec with Matchers:

  // ── builders ────────────────────────────────────────────────────────────────

  private val dummyObl     = Obligation(Nil, "g")
  private val dummySummary = TacticSummary(Nil, Nil)

  /** Build a node by TREE SHAPE only. The output-obligation count is tied to the
   *  child count (`childIds.size`), so `isBranching ⟺ childIds.size > 1` — the
   *  well-formed invariant ParserTest already asserts
   *  (`child_ids.length == output_obligations.length`). Obligation contents and
   *  the summary are dummies — `compute` must ignore them. */
  private def tn(id: Int, parent: Option[Int], children: List[Int]): TacticNode =
    TacticNode(
      id                = id,
      tacticText        = "tac",
      inputObligation   = dummyObl,
      outputObligations = List.fill(children.size)(dummyObl),
      summary           = dummySummary,
      parentId          = parent,
      childIds          = children
    )

  /** Run compute and project to id → raw segment lists for easy assertions. */
  private def paths(nodes: TacticNode*): Map[Int, List[String]] =
    BranchPath.compute(nodes.toList).view.mapValues(_.segments).toMap


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 1 — Linear chains (no branching anywhere ⇒ empty path everywhere)
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (linear)" should "give [] for a single root-only leaf (`sorry`)" in {
    paths(tn(0, None, Nil)) shouldBe Map(0 -> Nil)
  }

  it should "give [] for every node of a 3-node linear chain 0→1→2" in {
    val ns = Seq(tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), Nil))
    paths(ns*) shouldBe Map(0 -> Nil, 1 -> Nil, 2 -> Nil)
  }

  it should "give [] across a long linear chain (linear nodes share one path)" in {
    val ns = Seq(
      tn(0, None, List(1)), tn(1, Some(0), List(2)), tn(2, Some(1), List(3)),
      tn(3, Some(2), List(4)), tn(4, Some(3), Nil)
    )
    paths(ns*).values.toSet shouldBe Set(Nil)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 2 — A single branching point
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (single branch)" should "mark a branching root `*` and index its leaves 0,1" in {
    val ns = Seq(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil))
    paths(ns*) shouldBe Map(0 -> List("*"), 1 -> List("0"), 2 -> List("1"))
  }

  it should "index a 3-way branch as 0,1,2 (indices may exceed 1)" in {
    val ns = Seq(
      tn(0, None, List(1, 2, 3)),
      tn(1, Some(0), Nil), tn(2, Some(0), Nil), tn(3, Some(0), Nil)
    )
    paths(ns*) shouldBe
      Map(0 -> List("*"), 1 -> List("0"), 2 -> List("1"), 3 -> List("2"))
  }

  it should "leave linear ancestors above a non-root branch empty (0 linear, 1 branches)" in {
    // 0→1→{2,3}: node 0 is linear (one output) so it contributes nothing; node 1
    // branches but has no branching ANCESTOR ⇒ empty prefix ⇒ ["*"].
    val ns = Seq(
      tn(0, None, List(1)), tn(1, Some(0), List(2, 3)),
      tn(2, Some(1), Nil), tn(3, Some(1), Nil)
    )
    paths(ns*) shouldBe
      Map(0 -> Nil, 1 -> List("*"), 2 -> List("0"), 3 -> List("1"))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 3 — Branch index = POSITION in childIds, not the node id
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (index source)" should "index by childIds position with NON-CONTIGUOUS ids [1,6]" in {
    // prop_85's root shape: child id 1 → index "0", child id 6 → index "1".
    val ns = Seq(tn(0, None, List(1, 6)), tn(1, Some(0), Nil), tn(6, Some(0), Nil))
    paths(ns*) shouldBe Map(0 -> List("*"), 1 -> List("0"), 6 -> List("1"))
  }

  it should "honor childIds ORDER, not numeric sort (childIds=[6,1])" in {
    val ns = Seq(tn(0, None, List(6, 1)), tn(6, Some(0), Nil), tn(1, Some(0), Nil))
    paths(ns*) shouldBe Map(0 -> List("*"), 6 -> List("0"), 1 -> List("1"))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 4 — Nested branching + the `*`-merge (the resolved discrepancy)
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (nested)" should "match the design-notes table: 0→{1→{3,4}, 2}, 1 branches" in {
    val ns = Seq(
      tn(0, None, List(1, 2)),
      tn(1, Some(0), List(3, 4)),   // child 0 of 0, itself branching
      tn(2, Some(0), Nil),          // child 1 of 0
      tn(3, Some(1), Nil), tn(4, Some(1), Nil)
    )
    paths(ns*) shouldBe Map(
      0 -> List("*"),
      1 -> List("0*"),              // ["0"] + self-branch, MERGED into last index
      2 -> List("1"),
      3 -> List("0", "0"),
      4 -> List("0", "1")
    )
  }

  it should "merge `*` onto a NON-zero index (branch on the second child)" in {
    // 0→{1, 2→{3,4}}, node 2 branches ⇒ B(2)=["1*"].
    val ns = Seq(
      tn(0, None, List(1, 2)),
      tn(1, Some(0), Nil),
      tn(2, Some(0), List(3, 4)),
      tn(3, Some(2), Nil), tn(4, Some(2), Nil)
    )
    paths(ns*) shouldBe Map(
      0 -> List("*"),
      1 -> List("0"),
      2 -> List("1*"),
      3 -> List("1", "0"),
      4 -> List("1", "1")
    )
  }

  it should "put `*` only on the LAST segment at three nested levels, and pass PLAIN indices down" in {
    // 0→{1→{3→{5,6}, 4}, 2}; nodes 0,1,3 branch.
    val ns = Seq(
      tn(0, None, List(1, 2)),
      tn(1, Some(0), List(3, 4)),
      tn(2, Some(0), Nil),
      tn(3, Some(1), List(5, 6)),
      tn(4, Some(1), Nil),
      tn(5, Some(3), Nil), tn(6, Some(3), Nil)
    )
    val p = paths(ns*)
    p shouldBe Map(
      0 -> List("*"),
      1 -> List("0*"),
      2 -> List("1"),
      3 -> List("0", "0*"),          // `*` on the last segment only
      4 -> List("0", "1"),
      5 -> List("0", "0", "0"),      // ancestor 3 contributes PLAIN "0", not "0*"
      6 -> List("0", "0", "1")
    )
    // Explicit contrast: branching node 3 is "0*", but its descendants carry "0".
    p(3).last shouldBe "0*"
    p(5).take(2) shouldBe List("0", "0")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 5 — Linear segments between branches inherit their branch's path
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (linear-within-branch)" should
    "share one path across a linear run between two branches; only branching ancestors add indices" in {
    // 0→{1, 2→7→8→{9,10}}; nodes 2,7 linear, 0 and 8 branch.
    val ns = Seq(
      tn(0, None, List(1, 2)),
      tn(1, Some(0), Nil),
      tn(2, Some(0), List(7)),       // child 1 of 0, linear
      tn(7, Some(2), List(8)),       // linear
      tn(8, Some(7), List(9, 10)),   // branches
      tn(9, Some(8), Nil), tn(10, Some(8), Nil)
    )
    val p = paths(ns*)
    p shouldBe Map(
      0  -> List("*"),
      1  -> List("0"),
      2  -> List("1"),
      7  -> List("1"),               // shares 2's path — only branching ancestor is 0
      8  -> List("1*"),
      9  -> List("1", "0"),
      10 -> List("1", "1")
    )
    p(2) shouldBe p(7)               // linear-chain-sharing within a branch
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 6 — `isBranching` boundary (driven by output count: > 1)
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (branching boundary)" should "NOT star a 1-output node" in {
    val ns = Seq(tn(0, None, List(1)), tn(1, Some(0), Nil))
    paths(ns*)(0) shouldBe Nil       // exactly one output ⇒ not branching
  }

  it should "NOT star a 0-output leaf" in {
    paths(tn(0, None, Nil))(0) shouldBe Nil
  }

  it should "star a 2-output node" in {
    val ns = Seq(tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), Nil))
    paths(ns*)(0) shouldBe List("*")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 7 — Structure / determinism
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (structure)" should "return exactly one entry per node id" in {
    val ns = Seq(
      tn(0, None, List(1, 2)), tn(1, Some(0), Nil), tn(2, Some(0), List(3)),
      tn(3, Some(2), Nil)
    )
    paths(ns*).keySet shouldBe Set(0, 1, 2, 3)
  }

  it should "be independent of input-list order (reversed list ⇒ identical map)" in {
    // compute builds an id→node index internally, so list order must not matter.
    val ns = List(
      tn(0, None, List(1, 2)),
      tn(1, Some(0), Nil),
      tn(2, Some(0), List(3, 4)),
      tn(3, Some(2), Nil), tn(4, Some(2), Nil)
    )
    BranchPath.compute(ns) shouldBe BranchPath.compute(ns.reverse)
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 8 — Golden: the real prop_14 tree from the phase-1 fixture
  // ═══════════════════════════════════════════════════════════════════════════
  //
  //   0  induction xs        (branching → 1, 2)
  //   ├─ 1  simp [filter]    (leaf, nil branch)
  //   └─ 2  simp [filter]    (linear → 3)
  //      └─ 3  split_ifs     (branching → 4, 6)
  //         ├─ 4  simp       (linear → 5)
  //         │  └─ 5  exact ih (leaf)
  //         └─ 6  exact ih   (leaf)

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  "BranchPath.compute (golden prop_14)" should "match the hand-derived branch paths of all 7 nodes" in {
    val prop14 = Parser.parseFile(fixture).declarations.head
    prop14.name shouldBe "prop_14"   // guard against fixture drift

    val p = BranchPath.compute(prop14.tacticNodes).view.mapValues(_.segments).toMap
    p shouldBe Map(
      0 -> List("*"),
      1 -> List("0"),
      2 -> List("1"),
      3 -> List("1*"),               // on branch 1 of node 0, itself branching
      4 -> List("1", "0"),
      5 -> List("1", "0"),           // linear child of 4 — shares 4's path
      6 -> List("1", "1")
    )
    p(4) shouldBe p(5)               // linear-chain-sharing on real data
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP 9 — Defensive / degenerate input
  // ═══════════════════════════════════════════════════════════════════════════

  "BranchPath.compute (degenerate)" should "return an empty map for an empty node list" in {
    BranchPath.compute(Nil) shouldBe Map.empty[Int, BranchPath]
  }

  it should "FAIL FAST on a dangling parentId (corrupt tree)" in {
    // ParserTest guarantees every parent_id resolves within the declaration, so a
    // dangling pointer is corrupt input. We choose loud failure over a silently
    // wrong path rather than defensively coding around an impossible state.
    val orphan = tn(0, parent = Some(99), children = Nil)
    an [Exception] should be thrownBy BranchPath.compute(List(orphan))
  }
