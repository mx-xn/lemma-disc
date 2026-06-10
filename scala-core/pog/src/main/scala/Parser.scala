import upickle.default.read

/** Parse a phase-1 trace JSON file into a `LeanProofTrace`.
 *
 *  The wire format is defined by `schemas/trace.schema.json` and mirrored by
 *  the ADTs in `Types.scala`; all custom encoding rules (null → None,
 *  reserved-word keys, snake_case) live there.
 */
object Parser:
  def parseFile(path: os.Path): LeanProofTrace =
    read[LeanProofTrace](path.toIO)
