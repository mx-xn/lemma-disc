import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers
import upickle.default.{read, write}

/** Round-trip tests for `PogParser.parseFile` against the real phase-2 fixture
 *  `data/pogs/Examples.json` (the phase-2 → phase-3 boundary).
 *
 *  The fixture exercises every POG shape phase 3 must consume: branching and
 *  leaf nodes, null parent_ids, both edge kinds, footprints and branch paths.
 *
 *  Stats (verified via jq against the fixture on 2026-06-02):
 *    pogs (declarations)  25
 *    tactic nodes        222
 *    edges               201  (kinds: modify, use)
 *    pogs[0]             prop_14: 7 nodes, 5 edges
 */
class PogParserTest extends AnyFlatSpec with Matchers:

  // Walk up from CWD so the test works whether sbt runs from `scala-core/` or
  // `scala-core/fragmentation/`.
  private lazy val fixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException(s"Examples.json fixture not found above ${os.pwd}"))

  private lazy val parsed: PogFile = PogParser.parseFile(fixture)

  "PogParser.parseFile" should "parse Examples.json without throwing" in {
    noException should be thrownBy PogParser.parseFile(fixture)
  }

  it should "recover the file header and declaration count" in {
    parsed.sourceFile shouldBe "LeanSrc/Examples.lean"
    parsed.pogs should have length 25
  }

  it should "recover every node and edge" in {
    parsed.pogs.map(_.nodes.size).sum shouldBe 222
    parsed.pogs.map(_.edges.size).sum shouldBe 201
    parsed.pogs.flatMap(_.edges.map(_.kind)).toSet shouldBe Set(ModifyEdge, UseEdge)
  }

  it should "preserve the POG-specific fields (footprint, branch_path) on nodes" in {
    val first = parsed.pogs.head
    first.declName  shouldBe "prop_14"
    first.nodes     should have length 7
    first.edges     should have length 5
    // every node carries the phase-2 extensions, not just the phase-1 fields
    first.nodes.foreach { n =>
      n.footprint  should not be null
      n.branchPath should not be null
    }
  }

  it should "round-trip losslessly through write → read" in {
    read[PogFile](write(parsed)) shouldBe parsed
  }
