import upickle.default.write

/** Phase-3 → segments JSON output + the fragmentation command-line entry point.
 *
 *  `buildAll` drives the full phase-A+B pipeline (Decomposer → FragmentBuilder)
 *  for every POG in a `PogFile` and assigns per-decl fragment IDs (0-indexed,
 *  contiguous within each declaration). `writeFile` pretty-prints to disk.
 *  The I/O shells `convertFile`/`convertDir` mirror the pog Serializer.
 *
 *  The default timeout uses `Long.MaxValue / 2` rather than `Long.MaxValue` to
 *  avoid overflowing the deadline arithmetic in `Decomposer.enumerate` while
 *  remaining effectively unbounded (~146 million years).
 *
 *  CLI (both forms take exactly two paths):
 *
 *    fragmentation <input-pog.json>  <output-segments.json>   (single file)
 *    fragmentation <input-dir>       <output-dir>             (batch, mirrors subdirs)
 */
object Serializer:

  private val NoTimeoutMs: Long = Long.MaxValue / 2

  private val Usage =
    """|Usage: fragmentation [--timeout <ms>] <input-pog.json>  <output-segments.json>   (single file)
       |       fragmentation [--timeout <ms>] <input-dir>       <output-dir>             (batch, mirrors subdirs)""".stripMargin

  /** Run the full phase-A+B pipeline on every POG in `pf` and collect results.
   *  Fragment IDs are 0-indexed and restart at 0 for each new declaration.
   *
   *  Decompositions whose reconstruction throws `IllegalArgumentException` are
   *  silently skipped: the name-level coarsening in phase 2 can leave a Modify
   *  action referencing a hypothesis absent from the reconstructed obligation when
   *  a V_post tactic cleared it without a recorded dependency edge. Phase 5 would
   *  reject the fragment anyway; skipping it here avoids a hard crash. Surviving
   *  fragments are renumbered to keep IDs contiguous from 0. */
  def buildAll(
    pf:        PogFile,
    heuristic: Candidate.Heuristic = Decomposer.defaultHeuristic,
    timeoutMs: Long                = NoTimeoutMs
  ): FragmentList =
    val fragments = pf.pogs.flatMap { pog =>
      val (decomps, _) = Decomposer.enumerate(pog, heuristic, timeoutMs)
      val built = decomps.flatMap { decomp =>
        try Some(FragmentBuilder.build(decomp, pog, pf.sourceFile, 0))
        catch case _: IllegalArgumentException => None
      }
      built.zipWithIndex.map { case (frag, fragId) => frag.copy(fragmentId = fragId) }
    }
    FragmentList(fragments)

  /** Write a `FragmentList` as pretty-printed JSON, creating parent directories
   *  and overwriting any existing file. */
  def writeFile(fl: FragmentList, path: os.Path): Unit =
    os.write.over(path, write(fl, indent = 2), createFolders = true)

  /** Parse one POG file, run the full pipeline, write the result. */
  def convertFile(input: os.Path, output: os.Path, timeoutMs: Long = NoTimeoutMs): Unit =
    writeFile(buildAll(PogParser.parseFile(input), timeoutMs = timeoutMs), output)

  /** Convert every `*.json` under `inputDir` (recursively), mirroring relative
   *  subpaths into `outputDir`. */
  def convertDir(inputDir: os.Path, outputDir: os.Path, timeoutMs: Long = NoTimeoutMs): Unit =
    os.walk(inputDir)
      .filter(p => os.isFile(p) && p.ext == "json")
      .foreach(in => convertFile(in, outputDir / in.relativeTo(inputDir), timeoutMs))

  /** Argument dispatch, factored out of `main` so it is unit-testable without
   *  spawning a process. Throws `IllegalArgumentException` on wrong arg count. */
  def run(args: Array[String]): Unit =
    val (timeoutMs, rest) = args.toList match
      case "--timeout" :: ms :: tail => (ms.toLong, tail)
      case other                     => (NoTimeoutMs, other)
    rest match
      case List(in, out) =>
        val inPath  = os.Path(in, os.pwd)
        val outPath = os.Path(out, os.pwd)
        if os.isDir(inPath) then convertDir(inPath, outPath, timeoutMs)
        else convertFile(inPath, outPath, timeoutMs)
      case _ =>
        throw IllegalArgumentException(s"expected 2 path arguments, got ${rest.length}\n$Usage")

  def main(args: Array[String]): Unit = run(args)
