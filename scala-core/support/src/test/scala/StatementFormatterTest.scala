import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class StatementFormatterTest extends AnyFlatSpec with Matchers:

  // ── degenerate / pass-through cases ────────────────────────────────────────

  "format" should "return just the conclusion when there are no premises and body=True" in {
    StatementFormatter.format(Nil, "True", "P") shouldBe "P"
  }

  it should "emit only premise binders when body=True" in {
    StatementFormatter.format(List("h1 : Nat", "h2 : Bool"), "True", "P") shouldBe
      "(h1 : Nat) (h2 : Bool) : P"
  }

  it should "render a single named premise with the binder colon, not an arrow" in {
    StatementFormatter.format(List("h1 : Nat"), "True", "P") shouldBe "(h1 : Nat) : P"
  }

  // ── body lifted into binders ───────────────────────────────────────────────

  it should "lift a leading `(name : type)` antecedent from body into a binder" in {
    StatementFormatter.format(Nil, "(ih : Nat → Nat) → goal", "concl") shouldBe
      "(ih : Nat → Nat) (h1 : goal) : concl"
  }

  it should "lift all named antecedents from a multi-arrow body" in {
    StatementFormatter.format(
      Nil,
      "(h2 : A) → (h3 : B) → tail",
      "concl"
    ) shouldBe "(h2 : A) (h3 : B) (h1 : tail) : concl"
  }

  it should "generate a fresh name for an unnamed body antecedent" in {
    StatementFormatter.format(Nil, "a = b", "a + b = c") shouldBe
      "(h1 : a = b) : a + b = c"
  }

  it should "generate a fresh name for an unnamed antecedent and reuse it across the chain" in {
    StatementFormatter.format(Nil, "a = b → c < d → True", "concl") shouldBe
      "(h1 : a = b) (h2 : c < d) (h3 : True) : concl"
  }

  // ── parenthesis-depth correctness (the bug the user flagged) ────────────────

  it should "not split arrows inside a parenthesised subterm" in {
    // Top-level: ant → tail, where ant contains `(P → Q)` — must stay intact.
    StatementFormatter.format(Nil, "(P → Q) → tail", "concl") shouldBe
      "(h1 : P → Q) (h2 : tail) : concl"
  }

  it should "not split arrows inside a binder type" in {
    // Single arrow at depth 0 separates `(ih : ∀ x, P x → Q x)` from `tail`.
    StatementFormatter.format(
      Nil,
      "(ih : ∀ x, P x → Q x) → tail",
      "concl"
    ) shouldBe "(ih : ∀ x, P x → Q x) (h1 : tail) : concl"
  }

  it should "not split inside [] or {} groupings (implicit / instance binders)" in {
    StatementFormatter.format(
      Nil,
      "[Inhabited α] → {n : Nat} → tail",
      "concl"
    ) shouldBe "(h1 : [Inhabited α]) (h2 : {n : Nat}) (h3 : tail) : concl"
  }

  it should "treat a top-level `∀` as binding rightward and stop splitting there" in {
    // A body of `∀ x, P → Q` is `∀ x, (P → Q)` in Lean — the → is NOT top-level.
    StatementFormatter.format(Nil, "∀ x, P → Q", "concl") shouldBe
      "(h1 : ∀ x, P → Q) : concl"
  }

  // ── fresh-name collision avoidance ─────────────────────────────────────────

  it should "skip a candidate name that is already used as a premise binder" in {
    StatementFormatter.format(List("h1 : Nat"), "a = b", "concl") shouldBe
      "(h1 : Nat) (h2 : a = b) : concl"
  }

  it should "skip a candidate name appearing as a whole word in body or conclusion" in {
    // `h1` and `h2` both appear as variables inside the body and conclusion,
    // so the fresh name must skip to `h3` to avoid shadowing.
    StatementFormatter.format(Nil, "h1 + h2 = h2 + h1", "h1 + h2 = h2 + h1") shouldBe
      "(h3 : h1 + h2 = h2 + h1) : h1 + h2 = h2 + h1"
  }

  it should "not be confused by an identifier that merely contains the candidate as a substring" in {
    // `h1abc` should NOT make `h1` look taken — only whole-word matches block.
    StatementFormatter.format(Nil, "h1abc = 0", "P") shouldBe
      "(h1 : h1abc = 0) : P"
  }

  // ── (name : type) recognition edge cases ───────────────────────────────────

  it should "treat `(P)` (no colon) as an unnamed antecedent, not a binder" in {
    StatementFormatter.format(Nil, "(P) → Q", "concl") shouldBe
      "(h1 : P) (h2 : Q) : concl"
  }

  it should "not be tripped up by `:=` inside the binder type" in {
    // First top-level `:` precedes `:=`; we should still recognise the binder.
    StatementFormatter.format(Nil, "(h : a := b) → tail", "concl") shouldBe
      "(h : a := b) (h1 : tail) : concl"
  }

  it should "leave alone an antecedent whose first top-level `:` is `::`" in {
    // `x :: xs` has no real `:`-binder colon — must be lifted with a fresh name.
    StatementFormatter.format(Nil, "x :: xs = ys", "concl") shouldBe
      "(h1 : x :: xs = ys) : concl"
  }

  it should "preserve the binder name when the type itself contains arrows" in {
    StatementFormatter.format(Nil, "(f : α → β → γ) → goal", "concl") shouldBe
      "(f : α → β → γ) (h1 : goal) : concl"
  }
