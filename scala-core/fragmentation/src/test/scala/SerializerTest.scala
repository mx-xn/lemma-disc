import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import upickle.default.{read, write}

/** Tests for [[Serializer]] (step 9) — the I/O + CLI shell around the phase-3
 *  pipeline.
 *
 *  `Decomposer`, `Reconstructor`, and `FragmentBuilder` are exercised in their
 *  own suites; this suite covers only what those suites do NOT:
 *
 *  GROUP A — `buildAll`: in-memory pipeline integration + per-decl ID assignment
 *  GROUP B — `writeFile`: disk I/O (create dirs, overwrite, pretty-print, format)
 *  GROUP C — `run`: CLI dispatch (single file, batch, edge cases)
 *  GROUP D — Integration on `data/pogs/Examples.json` (schema-level invariants)
 *
 *  Correctness properties (referenced in group headers):
 *
 *  [S1] `buildAll` on an empty PogFile yields an empty FragmentList.
 *  [S2] Trivial fragments (full proof, no holes) are filtered regardless of heuristic.
 *  [S3] Fragment IDs are 0-indexed and restart at 0 for each new declaration.
 *  [S4] `pf.sourceFile` propagates to every emitted fragment's `sourceFile`.
 *  [S5] No fragment may both have a hole and have a branching CompositeNode (heuristic
 *       invariant; the jq check from CLAUDE.md verification section).
 *  [S6] For each `declName`, fragment IDs form the range 0..n-1 with no gaps.
 *  [S7] Every fragment has exactly one root node (parentId = None).
 *  [S8] `rootObligation` equals the root node's `obligation` on every fragment.
 */
class SerializerTest extends AnyFlatSpec with Matchers:

  // ── POG builders (same helpers as FragmentBuilderTest) ──────────────────────

  private def hyp(name: String, typ: String): Hypothesis = Hypothesis(name, typ)
  private def obl(hyps: List[Hypothesis], goal: String): Obligation = Obligation(hyps, goal)
  private val noSum   = TacticSummary(Nil, Nil)
  private val dummyFp = Footprint(Set.empty, Set.empty, false, Nil)

  private def tn(id: Int, parent: Option[Int], children: List[Int],
                 in: Obligation, outs: List[Obligation],
                 text: String = "tac"): TacticNode =
    TacticNode(id, text, in, outs, noSum, parent, children)

  private def mkPog(rootId: Int, nodes: List[TacticNode],
                    edges: List[PogEdge], name: String): ProofOrderingGraph =
    val bps = BranchPath.compute(nodes)
    ProofOrderingGraph(name, s"theorem $name : g", rootId,
      nodes.find(_.id == rootId).get.inputObligation,
      nodes.map(n => PogNode(n, dummyFp, bps(n.id))), edges)

  private def e(from: Int, to: Int): PogEdge = PogEdge(from, to, UseEdge)

  // ── POG fixtures ─────────────────────────────────────────────────────────────
  //
  //  introChain: 0 → 1 → 2    edges: (0,1),(1,2),(0,2)
  //    Non-singleton admissible non-trivial V_H sets (default heuristic): {0,1},{1,2}
  //    {0},{1},{2} are singletons (dropped); {0,2} is non-convex; {0,1,2} is trivial.
  //    → 2 fragments.
  //
  //  branchFork: 0 → {1, 2}   edges: (0,1),(0,2)
  //    {1},{2} are singletons (dropped); {0},{0,1},{0,2} fail the default heuristic
  //    (branches + hole); {1,2} is inadmissible (no common root); {0,1,2} is trivial.
  //    → 0 fragments (default). With `_ => true`: {0,1},{0,2} accepted ({0} is a singleton). → 2 fragments.
  //
  //  leafPog: 0 (leaf, mₙ=0)
  //    Only V_H = {0} is admissible, and it is trivial (root=proofRoot, holeCount=0).
  //    → 0 fragments.

  private val ic0in  = obl(Nil, "∀x:Nat, P x")
  private val ic0out = obl(List(hyp("h", "Nat")), "P h")
  private val ic1out = obl(List(hyp("h", "Nat")), "Q")

  private val introChain = mkPog(0, List(
    tn(0, None,    List(1), ic0in,  List(ic0out), "intro h"),
    tn(1, Some(0), List(2), ic0out, List(ic1out), "rw"),
    tn(2, Some(1), Nil,     ic1out, Nil,          "exact")
  ), List(e(0,1), e(1,2), e(0,2)), "intro_chain")

  private val bfIn   = obl(List(hyp("h", "A∧B")), "C")
  private val bfOut0 = obl(List(hyp("h", "A∧B"), hyp("h1", "A")), "C")
  private val bfOut1 = obl(List(hyp("h", "A∧B"), hyp("h2", "B")), "C")

  private val branchFork = mkPog(0, List(
    tn(0, None,    List(1,2), bfIn,   List(bfOut0, bfOut1), "cases h"),
    tn(1, Some(0), Nil,       bfOut0, Nil,                  "exact h1"),
    tn(2, Some(0), Nil,       bfOut1, Nil,                  "exact h2")
  ), List(e(0,1), e(0,2)), "branch_fork")

  private val leafPog = mkPog(0, List(tn(0, None, Nil, ic0in, Nil, "exact")), Nil, "leaf_pog")

  // ── PogFile helpers ──────────────────────────────────────────────────────────

  private def pogFile(source: String, pogs: ProofOrderingGraph*): PogFile =
    PogFile(source, pogs.toList)

  private def writePogFile(pf: PogFile, at: os.Path): Unit =
    os.write.over(at, write(pf), createFolders = true)

  // ── fixture for GROUP D ──────────────────────────────────────────────────────

  // 5 seconds per POG: generous for typical proof sizes in Examples.json (avg ~9
  // nodes, max ~20) while keeping total test time under a minute for 25 POGs.
  private val IntegrationTimeoutMs: Long = 5_000L

  private lazy val pogFixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException("data/pogs/Examples.json not found"))

  private lazy val examplesPf: PogFile = PogParser.parseFile(pogFixture)

  private lazy val examplesFragments: List[Fragment] =
    Serializer.buildAll(examplesPf, timeoutMs = IntegrationTimeoutMs).fragments

  // Persistent sample used across GROUP B writeFile tests.
  private lazy val sampleFl: FragmentList =
    Serializer.buildAll(pogFile("f.lean", introChain))


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP A — buildAll: in-memory conversion  [S1–S4]
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer.buildAll (empty PogFile)" should
    "[A1] produce an empty FragmentList when the PogFile contains no POGs  [S1]" in {
    Serializer.buildAll(PogFile("f.lean", Nil)).fragments shouldBe Nil
  }

  "Serializer.buildAll (trivial-only POG)" should
    "[A2] produce no fragments when the only candidate is the trivial full-proof set  [S2]" in {
    // leafPog: one leaf node; V_H={0} is trivial (root=proofRoot, holeCount=0).
    Serializer.buildAll(pogFile("f.lean", leafPog)).fragments shouldBe Nil
  }

  "Serializer.buildAll (introChain)" should
    "[A3] produce exactly 2 non-trivial accepted fragments for the 3-node linear chain" in {
    Serializer.buildAll(pogFile("f.lean", introChain)).fragments should have size 2
  }

  "Serializer.buildAll (two-POG PogFile)" should
    "[A4] restart fragment IDs at 0 for each new declaration  [S3]" in {
    // introChain → 2 fragments; branchFork (default heuristic) → 0 fragments
    // (all candidates are singletons, trivial, or branch+hole).
    val fl    = Serializer.buildAll(pogFile("f.lean", introChain, branchFork))
    val icIds = fl.fragments.filter(_.declName == "intro_chain").map(_.fragmentId).sorted
    val bfIds = fl.fragments.filter(_.declName == "branch_fork").map(_.fragmentId).sorted
    icIds shouldBe List(0, 1)
    bfIds shouldBe Nil
  }

  it should "[A5] accept more fragments with `_ => true` heuristic than with the default" in {
    // Default: singletons {0},{1},{2} dropped; {0,1},{0,2} are branch+hole (rejected). → 0.
    // No-filter: {0,1},{0,2} accepted; singletons {0},{1},{2} still dropped; {0,1,2} trivial. → 2.
    val default  = Serializer.buildAll(pogFile("f.lean", branchFork)).fragments.size
    val noFilter = Serializer.buildAll(pogFile("f.lean", branchFork), _ => true).fragments.size
    default  shouldBe 0
    noFilter shouldBe 2
  }

  it should "[A6] propagate PogFile.sourceFile to every emitted fragment's sourceFile  [S4]" in {
    val src = "MyRepo/Proofs.lean"
    val fl  = Serializer.buildAll(PogFile(src, List(introChain)))
    fl.fragments should not be empty
    fl.fragments.foreach { frag =>
      withClue(s"fragment ${frag.fragmentId}: ") { frag.sourceFile shouldBe src }
    }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP B — writeFile: disk I/O
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer.writeFile" should
    "[B1] write JSON that re-reads to the original FragmentList" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(sampleFl, out)
    read[FragmentList](os.read(out)) shouldBe sampleFl
  }

  it should "[B2] create missing parent directories" in {
    val out = os.temp.dir() / "a" / "b" / "c" / "out.json"
    Serializer.writeFile(sampleFl, out)
    os.exists(out)                   shouldBe true
    read[FragmentList](os.read(out)) shouldBe sampleFl
  }

  it should "[B3] overwrite an existing file" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(FragmentList(Nil), out)
    Serializer.writeFile(sampleFl, out)
    read[FragmentList](os.read(out)) shouldBe sampleFl
  }

  it should "[B4] produce pretty-printed JSON with 'fragments' as the only top-level key" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(sampleFl, out)
    val text = os.read(out)
    text                                  should include ("\n")
    ujson.read(text).obj.keys.toSet shouldBe Set("fragments")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP C — run: CLI dispatch
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer.run (single file)" should
    "[C1] convert one POG JSON to a re-readable segments JSON with the expected fragment count" in {
    val dir = os.temp.dir()
    val in  = dir / "in.json"
    val out = dir / "out.json"
    writePogFile(pogFile("f.lean", introChain), in)
    Serializer.run(Array(in.toString, out.toString))
    val fl = read[FragmentList](os.read(out))
    fl.fragments should have size 2
  }

  "Serializer.run (batch)" should
    "[C2] mirror the input subdir structure into the output dir" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "segments"    // does not exist yet
    writePogFile(pogFile("a/a.lean", introChain), inDir / "a" / "a.json")
    writePogFile(pogFile("b/b.lean", leafPog),    inDir / "b" / "b.json")
    Serializer.run(Array(inDir.toString, outDir.toString))
    os.exists(outDir / "a" / "a.json")                                  shouldBe true
    os.exists(outDir / "b" / "b.json")                                  shouldBe true
    read[FragmentList](os.read(outDir / "a" / "a.json")).fragments should have size 2
    read[FragmentList](os.read(outDir / "b" / "b.json")).fragments shouldBe Nil
  }

  it should "[C3] ignore non-.json files in the input tree" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "segments"
    writePogFile(pogFile("f.lean", introChain), inDir / "f.json")
    os.write(inDir / "notes.txt", "ignore me")
    Serializer.run(Array(inDir.toString, outDir.toString))
    os.exists(outDir / "f.json")    shouldBe true
    os.exists(outDir / "notes.txt") shouldBe false
  }

  it should "[C4] produce no output and not throw on an empty input dir" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "segments"
    noException should be thrownBy Serializer.run(Array(inDir.toString, outDir.toString))
    (os.exists(outDir) && os.walk(outDir).nonEmpty) shouldBe false
  }

  "Serializer.run (bad args)" should
    "[C5] throw IllegalArgumentException for 0, 1, or 3 arguments" in {
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array.empty)
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array("only-one"))
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array("a", "b", "c"))
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP D — Integration on data/pogs/Examples.json  [S5–S8]
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer (integration on Examples.json)" should
    "[D1] run the full pipeline without throwing" in {
    noException should be thrownBy
      Serializer.buildAll(examplesPf, timeoutMs = IntegrationTimeoutMs)
  }

  it should "[D2] write a lossless round-trip: disk output re-reads equal to in-memory result" in {
    val fl  = Serializer.buildAll(examplesPf, timeoutMs = IntegrationTimeoutMs)
    val out = os.temp.dir() / "Examples.json"
    Serializer.writeFile(fl, out)
    read[FragmentList](os.read(out)) shouldBe fl
  }

  it should "[D3] produce a non-empty fragment list" in {
    examplesFragments should not be empty
  }

  it should "[D4] contain no fragment that both has a hole and a branching node  [S5]" in {
    // This is the exact jq check from CLAUDE.md §Verification: the result must be 0.
    val violating = examplesFragments.filter { frag =>
      val hasHole   = frag.nodes.exists(_.isInstanceOf[HoleNode])
      val hasBranch = frag.nodes.exists {
        case c: CompositeNode => c.childIds.length > 1
        case _                => false
      }
      hasHole && hasBranch
    }
    withClue("fragments violating the heuristic (have both a hole and a branch): ") {
      violating shouldBe Nil
    }
  }

  it should "[D5] set a non-empty sourceFile and declName on every fragment" in {
    examplesFragments.foreach { frag =>
      withClue(s"fragment ${frag.fragmentId} of '${frag.declName}': ") {
        frag.sourceFile should not be empty
        frag.declName   should not be empty
      }
    }
  }

  it should "[D6] assign fragment IDs 0..n-1 with no gaps per declName  [S6]" in {
    val byDecl = examplesFragments.groupBy(_.declName)
    for (decl, frags) <- byDecl do
      withClue(s"decl '$decl': ") {
        frags.map(_.fragmentId).sorted shouldBe (0 until frags.size).toList
      }
  }

  it should "[D7] have exactly one root node (parentId=None) per fragment  [S7]" in {
    examplesFragments.foreach { frag =>
      withClue(s"fragment ${frag.fragmentId} of '${frag.declName}': ") {
        frag.nodes.count(_.parentId.isEmpty) shouldBe 1
      }
    }
  }

  it should "[D8] have rootObligation equal to the root node's obligation  [S8]" in {
    examplesFragments.foreach { frag =>
      val root = frag.nodes.find(_.parentId.isEmpty)
        .getOrElse(fail(s"no root node in fragment ${frag.fragmentId} of '${frag.declName}'"))
      withClue(s"fragment ${frag.fragmentId} of '${frag.declName}': ") {
        frag.rootObligation shouldBe root.obligation
      }
    }
  }
