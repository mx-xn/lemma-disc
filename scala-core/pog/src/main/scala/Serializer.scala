import upickle.default.write

/** POG → JSON output + the phase-2 command-line entry point.
 *
 *  Serialization itself lives in `Types.scala` (the `ReadWriter[PogFile]` and
 *  the wire-format overrides it transitively pulls in); this module is the thin
 *  I/O + CLI shell around it. `writeFile` pretty-prints and creates any missing
 *  parent directories (the `data/pogs/` tree does not exist until phase 2 runs).
 *
 *  No JSON-schema validation is performed: there is no validator on the
 *  classpath, and structural conformance to `pog.schema.json` is already
 *  guaranteed by the ADTs + their ReadWriters (see `TypesTest`). The schema is
 *  the human contract; the ADTs are the machine-enforced one.
 *
 *  CLI (both forms take exactly two paths):
 *
 *    pog <input-trace.json> <output-pog.json>   — single file
 *    pog <input-dir>        <output-dir>        — batch
 *
 *  Batch mode walks the input dir RECURSIVELY for `*.json` and mirrors each
 *  file's relative subpath into the output dir, so the phase-1 sharding
 *    data/traces/<repo>/<src>.json  →  data/pogs/<repo>/<src>.json
 *  is preserved. The two forms are distinguished by whether the input path is a
 *  directory.
 */
object Serializer:

  private val Usage =
    """Usage: pog <input-trace.json> <output-pog.json>   (single file)
      |       pog <input-dir>        <output-dir>        (batch, mirrors subdirs)""".stripMargin

  /** Write a POG file as pretty-printed JSON, creating parent directories and
   *  overwriting any existing file. */
  def writeFile(pf: PogFile, path: os.Path): Unit =
    os.write.over(path, write(pf, indent = 2), createFolders = true)

  /** Parse one trace file, build its POGs, write the result. */
  def convertFile(input: os.Path, output: os.Path): Unit =
    writeFile(Builder.buildFile(Parser.parseFile(input)), output)

  /** Convert every `*.json` under `inputDir` (recursively), mirroring relative
   *  subpaths into `outputDir`. */
  def convertDir(inputDir: os.Path, outputDir: os.Path): Unit =
    os.walk(inputDir)
      .filter(p => os.isFile(p) && p.ext == "json")
      .foreach(in => convertFile(in, outputDir / in.relativeTo(inputDir)))

  /** Argument dispatch, factored out of `main` so it is unit-testable without
   *  spawning a process. Throws `IllegalArgumentException` (with usage) on a
   *  bad argument count. */
  def run(args: Array[String]): Unit = args match
    case Array(in, out) =>
      val inPath  = os.Path(in, os.pwd)
      val outPath = os.Path(out, os.pwd)
      if os.isDir(inPath) then convertDir(inPath, outPath)
      else convertFile(inPath, outPath)
    case _ =>
      throw new IllegalArgumentException(s"expected 2 arguments, got ${args.length}\n$Usage")

  def main(args: Array[String]): Unit = run(args)
