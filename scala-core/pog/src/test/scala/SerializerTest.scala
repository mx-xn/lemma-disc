import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import upickle.default.{read, write}

/** Tests for `Serializer` (Step 8) — the I/O + CLI shell around the (already
 *  round-trip-tested) `ReadWriter[PogFile]`.
 *
 *  TypesTest exhaustively pins in-memory serialization of every ADT; this suite
 *  covers only what TypesTest does NOT: disk I/O (`writeFile` — parent-dir
 *  creation, overwrite, pretty-print), CLI dispatch (`run` — single vs batch,
 *  recursive subdir mirroring, bad-arg handling), and a real-data end-to-end
 *  against the phase-1 fixture.
 */
class SerializerTest extends AnyFlatSpec with Matchers:

  // ── fixtures / helpers ───────────────────────────────────────────────────────

  /** A minimal one-declaration trace, used both as a value and (via `write`) as
   *  on-disk trace JSON for the CLI tests. */
  private def trace(source: String, declName: String = "foo"): LeanProofTrace =
    LeanProofTrace(source, List(
      Declaration(declName, s"theorem $declName : P", 0, List(
        TacticNode(0, "exact h",
          Obligation(List(Hypothesis("h", "P")), "P"),
          Nil, TacticSummary(List("h"), Nil), None, Nil)
      ))
    ))

  private val samplePf: PogFile = Builder.buildFile(trace("LeanSrc/foo.lean"))

  private def writeTrace(t: LeanProofTrace, at: os.Path): Unit =
    os.write.over(at, write(t), createFolders = true)

  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "traces" / "MiniCodePropsLeanSrc" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw new RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP A — writeFile: disk I/O
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer.writeFile" should "write JSON that re-reads to the original PogFile" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(samplePf, out)
    read[PogFile](os.read(out)) shouldBe samplePf
  }

  it should "create missing parent directories" in {
    val out = os.temp.dir() / "a" / "b" / "c" / "out.json"
    Serializer.writeFile(samplePf, out)
    os.exists(out)              shouldBe true
    read[PogFile](os.read(out)) shouldBe samplePf
  }

  it should "overwrite an existing file" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(Builder.buildFile(trace("first.lean")), out)
    Serializer.writeFile(samplePf, out)
    read[PogFile](os.read(out)) shouldBe samplePf
  }

  it should "pretty-print (indented, multi-line) with the schema's top-level keys" in {
    val out = os.temp.dir() / "out.json"
    Serializer.writeFile(samplePf, out)
    val text = os.read(out)
    text                    should include ("\n")            // not a single dense line
    ujson.read(text).obj.keys.toSet shouldBe Set("source_file", "pogs")
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP B — run: CLI dispatch
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer.run (single file)" should "convert one trace file to one POG file" in {
    val dir = os.temp.dir()
    val in  = dir / "in.json"
    val out = dir / "out.json"
    writeTrace(trace("LeanSrc/foo.lean"), in)
    Serializer.run(Array(in.toString, out.toString))
    read[PogFile](os.read(out)) shouldBe Builder.buildFile(trace("LeanSrc/foo.lean"))
  }

  "Serializer.run (batch)" should "mirror the input subdir structure into the output dir" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "pogs"          // does not exist yet
    writeTrace(trace("RepoA/foo.lean", "a"), inDir / "RepoA" / "foo.json")
    writeTrace(trace("RepoB/bar.lean", "b"), inDir / "RepoB" / "bar.json")

    Serializer.run(Array(inDir.toString, outDir.toString))

    os.exists(outDir / "RepoA" / "foo.json") shouldBe true
    os.exists(outDir / "RepoB" / "bar.json") shouldBe true
    read[PogFile](os.read(outDir / "RepoA" / "foo.json")).pogs.head.declName shouldBe "a"
    read[PogFile](os.read(outDir / "RepoB" / "bar.json")).pogs.head.declName shouldBe "b"
  }

  it should "ignore non-.json files in the input tree" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "pogs"
    writeTrace(trace("RepoA/foo.lean"), inDir / "RepoA" / "foo.json")
    os.write(inDir / "RepoA" / "notes.txt", "ignore me")

    Serializer.run(Array(inDir.toString, outDir.toString))

    os.exists(outDir / "RepoA" / "foo.json")  shouldBe true
    os.exists(outDir / "RepoA" / "notes.txt") shouldBe false
  }

  it should "produce no output and not throw on an empty input dir" in {
    val inDir  = os.temp.dir()
    val outDir = os.temp.dir() / "pogs"
    noException should be thrownBy Serializer.run(Array(inDir.toString, outDir.toString))
    (os.exists(outDir) && os.walk(outDir).nonEmpty) shouldBe false
  }

  "Serializer.run (bad args)" should "throw on the wrong argument count" in {
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array.empty)
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array("only-one"))
    an [IllegalArgumentException] should be thrownBy Serializer.run(Array("a", "b", "c"))
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP C — end-to-end against the real phase-1 fixture
  // ═══════════════════════════════════════════════════════════════════════════

  "Serializer (end-to-end)" should "convert Examples.json to a re-readable 25-POG file" in {
    val out = os.temp.dir() / "Examples.json"
    Serializer.run(Array(fixture.toString, out.toString))

    val pf = read[PogFile](os.read(out))
    pf shouldBe Builder.buildFile(Parser.parseFile(fixture))   // disk round-trip is lossless
    pf.pogs.length shouldBe 25
    pf.pogs.foreach { p =>
      withClue(s"POG ${p.declName} should have ≥1 node: ") { p.nodes should not be empty }
    }
  }

  it should "carry prop_14's edges and prop_37's empty edge set through serialization" in {
    val out = os.temp.dir() / "Examples.json"
    Serializer.run(Array(fixture.toString, out.toString))
    val pf = read[PogFile](os.read(out))

    val prop14 = pf.pogs.find(_.declName == "prop_14").getOrElse(fail("no prop_14"))
    prop14.edges.toSet shouldBe Set(
      PogEdge(0, 2, ModifyEdge), PogEdge(2, 3, ModifyEdge), PogEdge(3, 4, ModifyEdge),
      PogEdge(0, 5, UseEdge),    PogEdge(0, 6, UseEdge)
    )

    val prop37 = pf.pogs.find(_.declName == "prop_37").getOrElse(fail("no prop_37"))
    prop37.nodes.length shouldBe 1     // single `sorry` node
    prop37.edges        shouldBe empty
  }
