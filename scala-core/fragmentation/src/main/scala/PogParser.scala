import upickle.default.read

/** Parse a phase-2 POG JSON file into a `PogFile`.
 *
 *  `PogFile` and all of its constituent ADTs / wire-format `ReadWriter`s are
 *  reused verbatim from the `pog` module (a compile dependency), so this is a
 *  thin wrapper at the phase-2 → phase-3 boundary. The wire contract is
 *  `schemas/pog.schema.json`.
 */
object PogParser:
  def parseFile(path: os.Path): PogFile =
    read[PogFile](path.toIO)
