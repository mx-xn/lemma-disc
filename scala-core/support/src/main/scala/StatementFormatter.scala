// Renders a (premises, body, conclusion) triple as a Lean-conventional theorem
// statement: `(p1 : T1) ... (pN : TN) : conclusion`.
//
// All premises become binders; every top-level `→`-antecedent in `body` is lifted
// into an additional binder. `(name : type)`-shaped antecedents keep their name;
// unnamed ones receive a fresh `h{k}` that does not collide (as a whole word)
// with anything already present in the premises, body, or conclusion.
//
// Top-level here means "at paren/bracket depth 0 and not under a `∀`-quantifier";
// nested `→`s inside binder types, `∀ … ,` bodies, or parenthesised subterms are
// left intact.

object StatementFormatter:

  def format(premises: List[String], body: String, conclusion: String): String =
    val premiseBinders = premises.map(p => s"($p)")
    val bodyBinders    = liftBody(body, premises, conclusion)
    val binders        = premiseBinders ++ bodyBinders
    if binders.isEmpty then conclusion
    else binders.mkString(" ") + " : " + conclusion

  // Lifts every top-level antecedent of `body` into a binder string.
  // `body == "True"` yields no binders (the ⊤ conjunct is dropped, as before).
  private def liftBody(body: String, premises: List[String], conclusion: String): List[String] =
    val trimmed = body.trim
    if trimmed.isEmpty || trimmed == "True" then return Nil

    val chunks = splitTopLevelArrows(trimmed)         // n+1 chunks for n arrows
    val taken  = scala.collection.mutable.Set.from(premises.flatMap(binderName))
    val avoid  = premises.mkString(" ") + " " + body + " " + conclusion
    var counter = 0

    def fresh(): String =
      while
        counter += 1
        val cand = s"h$counter"
        taken.contains(cand) || isWholeWordPresent(cand, avoid)
      do ()
      val name = s"h$counter"
      taken += name
      name

    chunks.map { raw =>
      val c = raw.trim
      binderName(c) match
        case Some(n) => taken += n; c                 // already `(name : type)` — keep
        case None    => s"(${fresh()} : ${stripWrappingParens(c)})"
    }

  // ── paren/∀-aware scanning ────────────────────────────────────────────────

  // Splits `s` on every `→` at paren-depth 0 that is not in scope of a top-level `∀`.
  // Returns one more chunk than the number of split points (always ≥ 1).
  private[this] def splitTopLevelArrows(s: String): List[String] =
    val out   = List.newBuilder[String]
    var depth = 0
    var i     = 0
    var start = 0
    var stopped = false                                // hit a top-level `∀` — bind rightward, no more splits
    while i < s.length && !stopped do
      val c = s.charAt(i)
      if isOpen(c) then depth += 1
      else if isClose(c) then depth -= 1
      else if depth == 0 then
        if c == '∀' then stopped = true
        else if c == '→' then
          out += s.substring(start, i)
          start = i + 1
      i += 1
    out += s.substring(start)
    out.result()

  // Extracts the binder name from a `(name : type)` chunk, if it has that shape.
  // The chunk must be wrapped by a single matched paren pair, and contain a `:`
  // (not `:=` or `::`) at the wrapper's interior depth 0.
  private[this] def binderName(chunk: String): Option[String] =
    val t = chunk.trim
    if !isFullyWrapped(t) then return None
    val inner = t.substring(1, t.length - 1)
    val colon = findTopLevelColon(inner)
    colon.map(idx => inner.substring(0, idx).trim).filter(_.nonEmpty)

  // True iff the leading `(` and trailing `)` of `s` form a matched pair that
  // encloses the entire string. Brackets `[` `{` are tracked so depth stays accurate.
  private[this] def isFullyWrapped(s: String): Boolean =
    if s.length < 2 || s.charAt(0) != '(' || s.charAt(s.length - 1) != ')' then return false
    var depth = 0
    var i = 0
    while i < s.length do
      val c = s.charAt(i)
      if isOpen(c) then depth += 1
      else if isClose(c) then
        depth -= 1
        if depth == 0 && i != s.length - 1 then return false
      i += 1
    depth == 0

  // Strips one layer of wrapping parens, if they enclose the entire expression.
  private[this] def stripWrappingParens(s: String): String =
    val t = s.trim
    if isFullyWrapped(t) then t.substring(1, t.length - 1).trim else t

  // Finds the first `:` at depth 0 in `s` that is not part of `:=` or `::`.
  private[this] def findTopLevelColon(s: String): Option[Int] =
    var depth = 0
    var i = 0
    while i < s.length do
      val c = s.charAt(i)
      if isOpen(c) then depth += 1
      else if isClose(c) then depth -= 1
      else if c == ':' && depth == 0 then
        val next = if i + 1 < s.length then s.charAt(i + 1) else ' '
        if next != '=' && next != ':' then return Some(i)
      i += 1
    None

  private[this] def isOpen (c: Char): Boolean = c == '(' || c == '[' || c == '{'
  private[this] def isClose(c: Char): Boolean = c == ')' || c == ']' || c == '}'

  // Whole-word substring search: matches `needle` only when flanked by non-identifier
  // characters (or string boundaries). Used to avoid generating a fresh `h{k}` that
  // collides with an identifier already appearing in the lemma surface.
  private[this] def isWholeWordPresent(needle: String, haystack: String): Boolean =
    val n = needle.length
    var i = 0
    while i <= haystack.length - n do
      if haystack.regionMatches(i, needle, 0, n)
         && !isIdentChar(if i == 0 then ' ' else haystack.charAt(i - 1))
         && !isIdentChar(if i + n == haystack.length then ' ' else haystack.charAt(i + n))
      then return true
      i += 1
    false

  private[this] def isIdentChar(c: Char): Boolean =
    c.isLetterOrDigit || c == '_' || c == '\''
