import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** Phase3→4 pipeline integration test (step 10 of the fragmentation build order).
 *
 *  Verifies that the `segments.schema.json` boundary holds end-to-end: fragmentation
 *  output is parseable by support and produces non-empty, well-formed lemmas.
 *
 *  Execution model:
 *    Phase 3 (fragmentation) — Serializer pipeline in-process, [[IntegrationTimeoutMs]]
 *      per POG.  The pipeline loop is replicated here (rather than delegating to
 *      Serializer.buildAll) so that [[EnumerationReport]] is captured for per-theorem
 *      logging.
 *    Phase 4 (support) — Serializer.main run as a subprocess.  The classpath is
 *      support's compiled class directory plus the library JARs already on the test
 *      JVM's classpath.  pog/fragmentation class directories are excluded: they are
 *      not needed by support and would shadow its default-package types.
 *
 *  The build.sbt task dependency `Test / test := (Test / test).dependsOn(support /
 *  Compile / compile).value` guarantees that support/target/classes exists before
 *  this test runs.
 *
 *  Correctness properties verified:
 *
 *  [PA] Full pipeline: runs without throwing; output JSON has "lemmas" as sole top-level key.
 *  [PB] Cardinality: one lemma per input fragment (no drops or duplicates).
 *  [PC] Provenance: fragment_id, source_file, decl_name pass through unchanged.
 *  [PD] Well-formedness: body/conclusion non-empty; premises formatted as "name : Type".
 *  [PE] Statement invariants: ends with conclusion; body="True" is dropped; premises appear
 *       as binders; body≠"True" means statement≠conclusion.
 *  [PF] Semantic coverage: both leaf (body="True") and hole (body≠"True") lemmas exist,
 *       and at least one lemma has non-empty premises (support calculus exercised).
 */
class Pipeline34Test extends AnyFlatSpec with Matchers:

  private val IntegrationTimeoutMs: Long = 5_000L

  private lazy val pogFixture: os.Path =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(6)
      .map(_ / "data" / "pogs" / "Examples.json")
      .find(os.exists)
      .getOrElse(throw RuntimeException("data/pogs/Examples.json not found"))

  // ── Subprocess infrastructure for phase 4 ──────────────────────────────────

  // Resolve java from the running JVM's JAVA_HOME — avoids hard-coding the conda path.
  private val javaExe: String =
    java.nio.file.Paths.get(System.getProperty("java.home"), "bin", "java").toString

  // support/target/classes — must exist (build.sbt enforces support/compile first).
  //
  // Walk up from os.pwd (sbt sets this to scala-core/ or scala-core/fragmentation/)
  // and look for the support/target sub-path.  take(4) keeps traversal within the
  // project tree; if support is not compiled the getOrElse throws a clear message.
  private lazy val supportClassesDir: String =
    Iterator.iterate(os.pwd)(_ / os.up)
      .take(4)
      .map(_ / "support" / "target" / "scala-3.3.4" / "classes")
      .find(os.exists)
      .getOrElse(throw RuntimeException(
        "support/target classes not found within 4 levels of os.pwd; run 'sbt support/compile' first"))
      .toString

  // Library JARs from the current test classloader hierarchy (upickle, scala-library, …).
  // sbt passes the test classpath through a URLClassLoader, NOT through java.class.path, so
  // we walk the classloader chain to collect JAR URLs.  Class directories are excluded —
  // support does not need pog/fragmentation classes and they would shadow support's types.
  private val libJars: String =
    def collectJars(cl: ClassLoader): Vector[String] = cl match
      case ucl: java.net.URLClassLoader =>
        ucl.getURLs.map(_.getPath).filter(_.endsWith(".jar")).toVector ++
          Option(ucl.getParent).map(collectJars).getOrElse(Vector.empty)
      case null  => Vector.empty
      case other => Option(other.getParent).map(collectJars).getOrElse(Vector.empty)
    collectJars(Thread.currentThread.getContextClassLoader)
      .distinct
      .mkString(java.io.File.pathSeparator)

  private lazy val supportClassPath: String =
    supportClassesDir + java.io.File.pathSeparator + libJars

  // ── Shared pipeline result (evaluated once on first test access) ───────────
  //
  // Phase 3: replicates Serializer.buildAll per-POG to capture EnumerationReport
  //   for per-theorem logging via info().
  // Phase 4: support Serializer subprocess on the written segments file.
  //
  // info() calls inside a lazy val body are captured under the test that first
  // triggers evaluation ([PA1]).

  private lazy val pipeline: (FragmentList, ujson.Value) =
    val pf     = PogParser.parseFile(pogFixture)
    val tmpDir = os.temp.dir()
    val segs   = tmpDir / "segments.json"
    val lems   = tmpDir / "lemmas.json"

    val fragments = pf.pogs.flatMap { pog =>
      val (decomps, report) = Decomposer.enumerate(pog, Decomposer.defaultHeuristic, IntegrationTimeoutMs)
      val built = decomps.flatMap { d =>
        try Some(FragmentBuilder.build(d, pog, pf.sourceFile, 0))
        catch case _: IllegalArgumentException => None
      }
      val renumbered = built.zipWithIndex.map { case (f, idx) => f.copy(fragmentId = idx) }
      val timedOutTag = if report.timedOut then " [timed out]" else ""
      info(s"  ${pog.declName}: ${renumbered.size} lemmas extracted${timedOutTag}")
      renumbered
    }
    val fl = FragmentList(fragments)

    Serializer.writeFile(fl, segs)
    os.proc(javaExe, "-cp", supportClassPath, "Serializer", segs.toString, lems.toString)
      .call(cwd = os.pwd)
    (fl, ujson.read(os.read(lems)))

  private def fragmentList: FragmentList  = pipeline._1
  private def lemmasRoot: ujson.Value     = pipeline._2
  private def lemmas: Vector[ujson.Value] = lemmasRoot("lemmas").arr.toVector

  // Index lemmas by (declName, fragmentId) for O(1) provenance lookups.
  private lazy val lemmaIndex: Map[(String, Int), ujson.Value] =
    lemmas.map(l => (l("decl_name").str, l("fragment_id").num.toInt) -> l).toMap


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP A — Full pipeline execution  [PA]
  // ═══════════════════════════════════════════════════════════════════════════

  "Phase3→4 pipeline" should
    "[PA1] run fragmentation + support on Examples.json without throwing" in {
    noException should be thrownBy { val _ = pipeline }
  }

  it should "[PA2] produce a JSON file with 'lemmas' as the only top-level key" in {
    lemmasRoot.obj.keys.toSet shouldBe Set("lemmas")
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP B — Fragment↔lemma cardinality  [PB]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[PB1] produce exactly one lemma per input fragment (no drops or duplicates)" in {
    lemmas.size shouldBe fragmentList.fragments.size
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP C — Provenance pass-through  [PC]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[PC1] preserve fragment_id for every lemma" in {
    for frag <- fragmentList.fragments do
      withClue(s"decl='${frag.declName}' fragment ${frag.fragmentId}: ") {
        lemmaIndex((frag.declName, frag.fragmentId))("fragment_id").num.toInt shouldBe frag.fragmentId
      }
  }

  it should "[PC2] preserve source_file for every lemma" in {
    for frag <- fragmentList.fragments do
      withClue(s"decl='${frag.declName}' fragment ${frag.fragmentId}: ") {
        lemmaIndex((frag.declName, frag.fragmentId))("source_file").str shouldBe frag.sourceFile
      }
  }

  it should "[PC3] preserve decl_name for every lemma" in {
    for frag <- fragmentList.fragments do
      withClue(s"decl='${frag.declName}' fragment ${frag.fragmentId}: ") {
        lemmaIndex((frag.declName, frag.fragmentId))("decl_name").str shouldBe frag.declName
      }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP D — Field well-formedness per lemmas.schema.json  [PD]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[PD1] have a non-empty body for every lemma" in {
    lemmas.foreach { l =>
      withClue(s"decl='${l("decl_name").str}' fragment ${l("fragment_id").num.toInt}: ") {
        l("body").str should not be empty
      }
    }
  }

  it should "[PD2] have a non-empty conclusion for every lemma" in {
    lemmas.foreach { l =>
      withClue(s"decl='${l("decl_name").str}' fragment ${l("fragment_id").num.toInt}: ") {
        l("conclusion").str should not be empty
      }
    }
  }

  it should "[PD3] format every premise as 'name : Type' (must contain ' : ')" in {
    lemmas.foreach { l =>
      l("premises").arr.foreach { p =>
        withClue(s"premise '${p.str}' in decl='${l("decl_name").str}' fragment ${l("fragment_id").num.toInt}: ") {
          p.str should include(" : ")
        }
      }
    }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP E — Statement structural invariants  [PE]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[PE1] end every statement with its conclusion" in {
    // StatementFormatter always places conclusion last: either as the whole string
    // (no binders) or after ' : ' (with binders). endsWith covers both cases.
    lemmas.foreach { l =>
      val stmt = l("statement").str
      val conc = l("conclusion").str
      withClue(s"statement='$stmt', conclusion='$conc': ") {
        stmt should endWith(conc)
      }
    }
  }

  it should "[PE2] set statement=conclusion when body='True', premises are empty, and scope_vars are empty" in {
    // With no binders from scope_vars, premises, or body (⊤), the statement degenerates
    // to just the conclusion with no leading binder block.
    lemmas
      .filter(l => l("body").str == "True" && l("premises").arr.isEmpty && l("scope_vars").arr.isEmpty)
      .foreach { l =>
        withClue(s"decl='${l("decl_name").str}' fragment ${l("fragment_id").num.toInt}: ") {
          l("statement").str shouldBe l("conclusion").str
        }
      }
  }

  it should "[PE3] include each premise as '(name : Type)' verbatim in the statement" in {
    // StatementFormatter wraps every premise p as "(p)" in the binder block.
    lemmas.foreach { l =>
      val stmt = l("statement").str
      l("premises").arr.foreach { p =>
        withClue(s"expected '(${p.str})' in statement='$stmt': ") {
          stmt should include(s"(${p.str})")
        }
      }
    }
  }

  it should "[PE4] produce statement≠conclusion when body is not 'True'" in {
    // A non-⊤ body is always lifted into at least one binder, making the statement
    // longer than the bare conclusion.
    lemmas.filter(_("body").str != "True").foreach { l =>
      withClue(s"decl='${l("decl_name").str}' fragment ${l("fragment_id").num.toInt}: ") {
        l("statement").str should not equal l("conclusion").str
      }
    }
  }


  // ═══════════════════════════════════════════════════════════════════════════
  // GROUP F — Semantic coverage over real Examples.json data  [PF]
  // ═══════════════════════════════════════════════════════════════════════════

  it should "[PF1] include at least one lemma with body='True' (leaf fragment, Supp-Leaf exercised)" in {
    lemmas.exists(_("body").str == "True") shouldBe true
  }

  it should "[PF2] include at least one lemma with body≠'True' (Lem(·) returns non-⊤)" in {
    lemmas.exists(_("body").str != "True") shouldBe true
  }

  it should "[PF3] include at least one lemma with non-empty premises (support calculus pulls hypotheses)" in {
    lemmas.exists(_("premises").arr.nonEmpty) shouldBe true
  }
