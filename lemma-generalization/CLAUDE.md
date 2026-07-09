# Phase 6: Lemma Generalization

## Environment

Runs inside the **`lemma` conda environment**, same as phases 1 and 5. This phase
shells out to Lean twice per round (term elaboration, coverage check), so treat Lean
startup as the expensive resource: batch, and cache aggressively.

---

## Implementation workflow — required for every step in this phase

This phase is explicitly held to a higher standard than the rest of a codebase that
is otherwise already messy. This section applies to every stage listed below, and to
any agent (including a future session with no memory of this conversation) picking up
implementation work here. Don't skip it, don't re-derive a looser process from first
principles — follow it as written.

**Code quality, non-negotiable:**
- Clean, modular, principled code. Each module/function has exactly one
  responsibility (see "Coding conventions" below for this phase's concrete module
  boundaries).
- Minimal comments: only when the *why* is genuinely non-obvious (a hidden
  invariant, a workaround, a subtle correctness argument — e.g. the memoization
  behavior in `antiunify.py`, or the promotion-filter soundness argument). Never
  comment what the code already says through naming.
- No speculative abstraction, no unused flexibility, no code paths for cases outside
  this phase's stated scope.

**Process, per step (i.e. per stage/module in "Sub-stages" below), strictly in this
order — do not collapse or reorder these:**
1. **Analyze expected behavior first**, in writing, before any code — including edge
   cases. Don't do this silently and jump straight to code.
2. **Propose an exhaustive test suite, then stop.** Enumerate the cases that would
   pin down correct behavior for this step, informed by step 1. Do not write
   implementation code yet.
3. **Get explicit approval on the tests** before moving on; iterate on the list as
   needed.
4. **Propose an implementation plan** for the step, informed by the approved tests.
   Get it finalized before writing code.
5. **Write a code skeleton first**: every function's signature (with type hints) plus
   a short note on its expected behavior and how the functions chain together to
   satisfy the step's goal — no bodies yet. Stop for approval before implementing
   anything. This is where a bad decomposition or data-flow mistake gets caught,
   while it's still cheap to change.
   The behavior notes at this stage are a review aid, not final code — once a
   function is actually implemented (next step), its comments collapse back down to
   the normal rule (only when the *why* is non-obvious), not left as leftover
   planning prose.
6. **Implement one function at a time**, showing the result after each function is
   completed — not batched, not one large diff at the end. The goal is for each piece
   to be understood as it lands, not just reviewed after the fact.

This sequence applies independently to each stage/module — don't batch several
stages through it at once.

---

## What phase 6 does

Phases 1–5 extract lemmas from concrete proof traces, so a single general truth often
surfaces as several *overly specific* lemmas — one per case that a proof happened to
branch on. Example: an inlined `(l : List T) : Permut l l` surfaces as three separate
lemmas, one per constructor shape Lean's induction split into:

```
Permut [] []
(e : T) : Permut [e] [e]
(e x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs)
```

Phase 6 detects clusters of lemmas that are all instances of one generalization
differing only in how one variable's value was pattern-matched, checks that the
observed patterns **exhaustively cover** that variable's type, and — only when that
check passes — replaces the cluster with the single general lemma.

**Soundness rule this phase must never violate:** a generalized lemma is only emitted
when the instantiated patterns are a genuine exhaustive case split over the
generalized variable's type. Coverage is checked by asking Lean itself (see
`coverage.py` below) — Lean's own match-exhaustiveness check is sound (never accepts a
non-exhaustive split), so we inherit that soundness rather than re-implementing it. It
is *not* complete (some true generalizations get missed, e.g. `[]` / `xs ++ [x]`
splits), which is an accepted, intentional trade-off, not a bug.

**Explicitly out of scope for v1:**
- **Proof reconstruction.** Generalized lemmas are emitted with `proof: null` and a
  `sorry`-stubbed `declaration` (see I/O below). The member lemmas' proofs are *not*
  stitched into a case-split proof for the generalized statement in this phase —
  deferred, see Future work.
- **Multi-variable generalization in one step.** A cluster is only promoted if
  anti-unifying its members introduces exactly one fresh variable. See "Why exactly
  one variable, not independent per-variable checks" below — this is a soundness
  requirement, not an implementation shortcut.
- **Indexed/dependent inductive types** (`Vector`, `Fin`-indexed families, etc.), where
  matching one field can constrain others. Restrict to plain (non-indexed) inductives;
  revisit once the non-indexed path is validated.

---

## Where everything lives

New top-level module, sibling to `lemma-emission/`:

```
lemma-generalization/
├── CLAUDE.md              # this doc
├── pyproject.toml         # packages = ["lemma_generalization"], mirrors lemma-emission/pyproject.toml
├── lean/
│   └── DumpTerm.lean      # elaborated-Expr → JSON exporter
├── src/
│   ├── __init__.py
│   ├── __main__.py        # CLI entry point
│   ├── models.py          # Term / Node / Var / Binder / Statement / LemmaObj
│   ├── elaborate.py       # Lean round-trip (statement string -> Statement tree) + cache
│   ├── antiunify.py       # pairwise AU, promotion filter, alpha-equivalence clustering
│   ├── coverage.py        # pattern serialization + Lean exhaustiveness check + promotion
│   └── fixpoint.py        # the round loop: repeat antiunify+coverage until no promotions
├── .cache/elaborate/      # gitignored already (repo .gitignore has a blanket `*/cache/` rule)
└── tests/                 # structure TBD per stage as it's implemented, see "Testing" note below
```

New schema files: `schemas/term_tree.schema.json` (the `Term`/`Statement` JSON shape),
`schemas/generalized_lemmas.schema.json` (this phase's output shape).

**Data output.** Following the existing naming convention in `data/`
(`prop_77_lemmas.json` → `prop_77_verified_lemmas.json`), this phase's output for a
given prop should be written as `data/prop_77_generalized_lemmas.json` — i.e. same
stem, `generalized_` prefix on `lemmas.json`, sitting alongside the
`_verified_lemmas.json` it was derived from. The CLI's `--output` flag takes an
explicit path (matching `lemma-emission`'s convention — no implicit default path is
computed by the tool itself); the caller is responsible for following this naming
convention when invoking it by hand.

**Not touched by this phase, pending later work:** `pipeline/run_full.sh` (phase 6
isn't wired in — neither is phase 5 yet), `.claude/skills/lemma-discovery`'s phase
table (I'll add a `phase6` row once this design is implemented and working, not
before).

### Command

```
python -m lemma_generalization \
    --input   <verified_lemmas.json> \
    --output  <generalized_lemmas.json> \
    [--lake-project <path>] \
    [--imports Module1,Module2] \
    [--max-rounds N]          # default 10; safety valve, see fixpoint.py
    [--dump-au-pairs <path>]  # optional debug artifact, see antiunify.py
```

Lake project / imports auto-detection follows the same convention as
`lemma-emission`'s `__main__.py` (walk up from the source file for `lakefile.*`;
explicit flags override).

---

## I/O

### Input

`verified_lemmas.json` — phase 5's output (`lemma-emission/CLAUDE.md`), schema
`schemas/lemmas.schema.json` plus phase 5's `proof`/`declaration` fields. Only
`statement` and `fragment_id` are read by this phase; `proof`/`declaration` are
carried through untouched on lemmas that are *not* part of a promoted cluster, and
dropped (along with the cluster) on lemmas that are.

### Output

`generalized_lemmas.json` — schema `schemas/generalized_lemmas.schema.json` (new; a
superset of `lemmas.schema.json` so downstream tooling that only reads `statement`
keeps working unchanged). Structure:

```json
{
  "lemmas": [
    {
      "fragment_id": 12,
      "source_file": "...",
      "decl_name": "...",
      "scope_vars": [...],
      "premises": [...],
      "body": "...",
      "conclusion": "...",
      "statement": "(l : List T) : Permut l l",
      "proof": null,
      "declaration": "lemma generalized_42 (l : List T) : Permut l l := by sorry",
      "generalized_from": [3, 7, 9],
      "pattern_coverage": ["List.nil", "List.cons e List.nil", "List.cons e (List.cons x xs)"]
    }
  ]
}
```

`statement` vs. `declaration` — same meaning as in `lemma-emission`, not
interchangeable: `statement` is just the binder-syntax type signature
(`(l : List T) : Permut l l`), while `declaration` is the *complete* Lean source
(`lemma <name> <statement> := by <proof>`). Since v1 doesn't synthesize a real proof,
`declaration`'s proof body is `sorry` — Lean 4's actual placeholder tactic (there is
no `admit` tactic in Lean 4 core; don't reach for that word). This isn't just a
convenience stub: assembling `declaration` and running it through Lean with `sorry`
(the same statement-only check `lemma-emission/validator.py`'s Pass 1 does) is the one
point in this phase that validates the *entire* reconstructed statement — binders,
substitutions, everything — end to end. Nothing earlier does this: the coverage check
(`coverage.py`) only validates the `match` skeleton over the generalized variable
`v : T`, not the surrounding premises/binder assembly. If the `sorry`-stubbed
declaration fails to elaborate, that means this phase's own code assembled the
generalized statement incorrectly (bad substitution, a dangling pattern variable,
etc.) — treat it as a promotion failure (leave the cluster's members untouched) and
log it distinctly from an ordinary coverage-check failure, since it signals a bug in
our code, not a legitimate "not generalizable" outcome.

Promoted lemmas get a freshly allocated `fragment_id` (never reused from any member)
and `decl_name = f"generalized_{fragment_id}"`.

- Lemmas untouched by generalization pass through with `generalized_from: null`,
  `pattern_coverage: null`, and their original `proof`/`declaration` intact.
- Generalized lemmas get `proof: null`, a `sorry`-stubbed but Lean-validated
  `declaration` (see above), `generalized_from` = the `fragment_id`s of every member
  lemma the cluster replaced (across however many fixpoint rounds it took), and
  `pattern_coverage` = the surface syntax of each pattern the coverage check verified,
  in the order Lean matched them.

---

## Why lemma statements need a term tree, not strings

Every field on `LemmaObj` today (`premises`, `body`, `conclusion`, `statement`) is a
**string** — Lean's pretty-printed surface syntax. Nothing in the codebase parses
these. Anti-unification, pattern matching, and coverage are all defined over term
trees (see the notes: `p ::= x | C p₁ … pₖ`), so this phase needs a real parse step
that the rest of the pipeline has never needed.

**Decision: elaborate through Lean itself, don't hand-roll a Lean 4 parser.** Lean 4's
notation is extensible and ambiguous outside its own elaborator — `e :: x :: xs` could
resolve to `List.cons`, or to a different type's own `::` notation (e.g. a custom
inductive that also declares `::`), depending entirely on what's open/imported and
what type is expected. There is no way to know it means `List.cons` from the text
alone. Only Lean's elaborator, with the real import context, can resolve it — so we
submit each lemma's `statement` to Lean as a scratch declaration, let elaboration
resolve all notation and implicit arguments down to actual `Expr.const` names, and
walk the resulting `Expr` ourselves into a small pattern-tree ADT we control. This
mirrors the existing convention of treating Lean as the source of truth
(`lemma-emission/validator.py` does the same round-trip for proof checking).

---

## Sub-stages, in implementation order

### 1. `schemas/term_tree.schema.json` + `src/models.py` — the pattern-tree ADT

Not a general `Expr` mirror (no universes, no metavariables, no sorts beyond what's
needed) — just enough structure to anti-unify and to re-serialize patterns as Lean
surface syntax:

```python
@dataclass
class Var:
    index: int      # de Bruijn index, NOT a name
    display_name: str  # for re-serialization only; never compared on

@dataclass
class Node:
    head: str            # fully-qualified constant/constructor name, e.g. "List.cons"
    args: list["Term"]   # flattened application spine, explicit arguments only

Term = Var | Node

@dataclass
class Binder:
    display_name: str
    type: Term
    implicit: bool

@dataclass
class Statement:
    binders: list[Binder]   # in declaration order
    body: Term              # the conclusion, with bound vars as de Bruijn Vars
```

**De Bruijn indices, not names, for bound variable references.** This is what makes
alpha-equivalence checking (used when clustering, see `antiunify.py`) free: two
alpha-equivalent statements produce *identical* `Statement` trees (`display_name`
differs, `index` doesn't), so alpha-equivalence is just Python structural equality once
`display_name` is excluded from `__eq__`.

**Implicit/instance arguments are never represented at all** — not stripped-then-
reinserted, just never captured in the tree in the first place, on both sides:

- *When building the tree* (`DumpTerm.lean`, stage 2), implicit/instance arguments
  (e.g. `Type u` parameters, `DecidableEq` instances) are skipped when flattening
  `Node.args`. They're fully determined by the explicit arguments' types and would
  otherwise register as spurious AU mismatches (e.g. differing universe metavariables
  that mean nothing semantically).
- *When serializing a pattern back to Lean surface syntax* (`coverage.py`, e.g.
  `List.cons e (List.cons x xs)`), implicit arguments are likewise never written —
  exactly like normal hand-written Lean, where you don't write `@List.cons`
  positionally either. Lean's elaborator re-infers them from context when it
  elaborates the surface text we hand it. There is no explicit "put them back" step;
  omitting them is what makes them get inferred.
- This is only safe because we've restricted to *non-indexed* inductive types (see
  "out of scope" above): for those, every implicit argument is a type/instance
  parameter that's always reconstructible from the explicit context. For an indexed
  family, an implicit argument can carry information (e.g. a length index) that
  Lean can't always re-derive purely from the explicit arguments — which is exactly
  why indexed types are excluded rather than handled by this same mechanism.

### 2. `lean/DumpTerm.lean` — the elaborated-term exporter

New Lean-side code (no existing precedent walks `Expr` structurally into JSON —
`digestion/lean/legacy/ExtractData.lean` only pretty-prints via `Meta.ppExpr`). Given
a batch of scratch declarations `theorem __gen_i <statement> := sorry`, elaborate
each and recursively convert its type (the full `∀`-binder chain ending in the
conclusion) into the `Term`/`Statement` JSON shape above:

- `Expr.forallE` → peel into `Statement.binders`, recursing into the body.
- `Expr.app` spine → flatten into `Node(head, args)`; resolve the head to its
  fully-qualified name via `Expr.const`/`Expr.fvar` lookup; skip implicit/instance
  arguments per the note above.
- `Expr.bvar` → `Var(index, display_name)`, taken from the binder name at that depth.
- One JSON object per line (batch output), same shape as
  `lemma-emission/validator.py`'s batched-scratch-file convention, so parse errors can
  be attributed back to `fragment_id` by declaration name.

### 3. `src/elaborate.py` — Lean round-trip + cache

Batches lemmas into scratch files (reuse the batch-size/imports/lake-project
conventions from `lemma-emission/validator.py` rather than reinventing them), invokes
`lake env lean` on `DumpTerm.lean`-produced input, parses the JSON-lines output into
`dict[fragment_id, Statement]`.

**What gets cached, and why.** Elaborating a statement is a pure function of
`(statement text, imports, lake project)` — same input always produces the same
`Statement` tree. Lean's process startup dominates the cost of this round trip (not
the elaboration itself), and this phase will be re-run on the *same* corpus file
repeatedly while `antiunify.py`/`coverage.py`/`fixpoint.py` are being developed and
debugged — none of which need statements re-elaborated if their text hasn't changed.
So: cache the resulting `Statement` JSON on disk, keyed by a hash of
`(statement text, imports, lake_project path)`, at
`lemma-generalization/.cache/elaborate/<hash>.json`. Same rationale as
`exp/anti_unify.py`'s LLM response cache — a slow, pure, externally-invoked step gets
memoized across process runs, not just within one.

### 4. `src/antiunify.py` — pairwise anti-unification + clustering

```python
def antiunify(a: Statement, b: Statement) -> Generalization | None
def find_clusters(statements: dict[int, Statement]) -> list[Cluster]
```

**`antiunify`** — standard memoized Plotkin anti-unification over the whole
`Statement` (binders + body as one nested term, in order) — not binders and body
separately. This is deliberate: members of a real cluster have *different numbers* of
binders (0 in `Permut [] []`, 2 in the `cons` case), because the pattern instantiated
for the generalized variable introduces its own fresh binders. Treating the whole
statement as one nested term lets the single differing position (the pattern
occurrence) absorb all of that, rather than needing separate
binder-list-arity-mismatch handling.

Maintain a memo `dict[(TermA, TermB), Var]` during the walk: whenever the same pair
of mismatched subterms recurs at multiple positions (e.g. `Permut l l` — the argument
`l` appears twice), reuse the same fresh variable rather than allocating a new one per
position. This is what keeps the Permut example at one variable instead of two.

Discard trivial results (`is_singleton`): if the entire generalization collapses to a
single bare variable (nothing shared at all), there's no structure worth clustering
on.

**Promotion filter — exactly one fresh variable.** Count variables introduced by
*disagreement* (i.e. exclude variables that are literally the same de Bruijn index on
both sides — those aren't generalizations, they're just shared structure). Only keep
`AUPair`s where this count is exactly 1; see below for why this can't be relaxed to
"check each fresh variable's coverage independently."

**`find_clusters`** — groups the surviving (single-variable) `AUPair`s by their
alpha-normalized generalization. Since bound variables are already de Bruijn-indexed,
alpha-equivalence is exact structural equality (`display_name` excluded), so this is a plain
`dict[Generalization, set[fragment_id]]` accumulation — no separate normalization pass
needed. Each resulting `Cluster` carries the shared generalized variable's type `T`
and, per member, the concrete pattern it instantiated for that variable.

If `--dump-au-pairs` is given, also write every computed `AUPair` — including ones
dropped by the promotion filter, tagged with the drop reason — to the given path;
useful for debugging why an expected cluster didn't form.

#### Why exactly one variable, not independent per-variable checks

It's tempting to think: if AU produces `f (g z) m`, just check `Cov(P_z, type of z)`
and `Cov(P_m, type of m)` independently, and promote if both hold. **This is not
sound.** Concretely: let `g(z, m) := (z = m)` over `z, m : Bool`, and say the corpus
gives exactly two member lemmas — the only ones an actual proof produced —
`g(true, true)` and `g(false, false)`. Checking coverage independently: `{true,
false}` exhausts `Bool` for `z` (✓), and `{true, false}` exhausts `Bool` for `m` (✓).
Both pass. But `∀ z m : Bool, z = m` is false: `g(true, false)` doesn't hold, and
neither independent check ever examined that pair, because it was never an observed
member lemma.

In general, concluding `∀z:T1, ∀m:T2. g(z,m)` requires a proof of `g(p_z, p_m)` for
**every pair in the full cross product** `P_z × P_m`, not just the "diagonal" pairs
that happened to co-occur in an actual member. Two independent single-variable checks
only ever verify the diagonal. AU can't be forced to avoid producing two variables in
the first place, either — `f (g x) (h y)` vs. `f (g a) b` genuinely disagrees in two
unrelated places, and the memoization trick (above) only collapses repeats of the
*same* subterm pair, which doesn't apply here.

So: such multi-variable `AUPair`s are computed by `antiunify`, then simply **dropped**
by the promotion filter — not stored, not retried within the round. This is a sound,
intentional false negative, consistent with the coverage check's own
sound-but-incomplete philosophy (see "What phase 6 does" above). Doing this soundly
for real would mean proving `g` on the full cross product, which requires proof
obligations the corpus doesn't hand us for free — that's real additional work
(entangled with proof reconstruction), not a smarter version of the same check; see
Future work.

A multi-variable pair may still resolve in a later fixpoint round if some other
promoted generalization happens to pin one of the two positions to a single shared
value across what's left to compare — but this isn't guaranteed, and no mechanism
forces it.

One free consequence: because the whole statement (not an isolated subterm) is
anti-unified, the one-fresh-variable filter automatically requires every *other*
premise/binder to already match up to alpha-equivalence between the two members —
there's no separate rule needed to keep `scope_vars`/`premises` consistent across a
cluster.

### 5. `src/coverage.py` — coverage check + promotion

For each candidate cluster:

1. **Serialize patterns.** For each member, extract the concrete `Term` instantiated
   for the cluster's one generalized variable, and render it as Lean surface syntax
   using **fully-qualified constructor application** (`List.cons e (List.cons x xs)`),
   never notation (`e :: x :: xs`) — see "Why lemma statements need a term tree"
   above for why notation can't be reconstructed reliably. Implicit arguments are
   omitted, per stage 1.
2. **Coverage check.** Batch a scratch declaration per candidate:
   ```lean
   example (v : List T) : True := by
     match v with
     | List.nil => trivial
     | List.cons e List.nil => trivial
     | List.cons e (List.cons x xs) => trivial
   ```
   Run through `lake env lean`. A clean elaboration means the patterns are exhaustive
   (`Cov(P, T)` holds); a "missing cases" diagnostic means they aren't.
   **On a "missing cases" diagnostic, stop here**: this is an ordinary, expected
   coverage failure, not an error — leave every member of the cluster untouched in
   the working set and move on to the next candidate.
3. **Construct the generalized `LemmaObj`** (only reached once step 2 succeeds):
   - Binders = the (already alpha-matched) shared binders from the cluster's
     generalization tree, with the one generalized position now a plain
     `v : T` binder in place of whatever per-member binders only existed to name
     pieces of that member's pattern.
   - `statement`/`body`/`conclusion` = the generalization tree's body, re-rendered to
     Lean surface syntax with `v` in place of the generalized position.
   - `fragment_id` = freshly allocated (never reused), `decl_name = f"generalized_{fragment_id}"`.
   - `proof: null`; `declaration = f"lemma {decl_name} {statement} := by sorry"`.
   - `generalized_from` = the union of every original member's `fragment_id`,
     including transitively through earlier fixpoint rounds if any member was itself
     already a generalized lemma.
   - `pattern_coverage` = the serialized patterns from step 1, in the order Lean
     matched them.
4. **Validate the assembled `declaration`** through Lean (statement-only check with
   `sorry`, same pattern as `lemma-emission/validator.py`'s Pass 1). This is a
   *different* check from step 2 — step 2 only validates the match skeleton over
   `v : T`; this validates the entire reconstructed statement (all binders,
   substitutions, everything). If it fails to elaborate, that means this phase's own
   code assembled the statement incorrectly (bad substitution, dangling pattern
   variable, etc.) — this is a construction bug, not a coverage failure. Abort the
   promotion, leave the cluster's members untouched, and log it loudly and distinctly
   from an ordinary step-2 coverage failure, since it needs a code fix, not just "this
   cluster doesn't generalize."
5. **Only once both step 2 and step 4 succeed**, replace the cluster's member lemmas
   with the generalized `LemmaObj` in the working set.

### 6. `src/fixpoint.py` — the round loop

Repeat `antiunify.find_clusters` → `coverage.check_and_promote` over the working
lemma set, re-including newly-promoted generalized lemmas as ordinary candidates in
the next round — their body is a genuine bound variable at this point, not a pattern,
so later rounds treat them structurally like any other statement, no special-casing
needed.

Terminate when a full round promotes nothing. `--max-rounds` (default 10) is a safety
valve only — log a warning, don't fail, if it's hit without convergence, and emit
whatever the working set looks like at that point.

**Why loop at all, given one round already finds every pair:** pairwise AU +
clustering is complete in a single round for finding every member of a cluster that
varies in exactly one position — all pairs are compared, so if three lemmas
instantiate the same one-variable generalization, all three pairwise AUs already
normalize to the same key. The loop exists to **compose generalizations across
different variables**: round 1 might generalize over `l1` while `l2` is held fixed per
cluster, producing several new lemmas that differ only in which `l2`-pattern they
fixed; round 2 can then anti-unify *those* over `l2` if the corpus happens to sample
`l2`'s cases independently of `l1`'s. This only becomes visible if round 1's output
feeds round 2's input.

### 7. `src/__main__.py` — CLI entry point

Wires stages 1–6, writes `generalized_lemmas.json` validated against
`schemas/generalized_lemmas.schema.json`.

---

## Coding conventions

Same standard as the rest of the pipeline: type hints on every function signature,
dataclasses for all structured data, no raw dicts past the JSON parse boundary. Each
module has one job — `models.py` is data, `elaborate.py` is the Lean-elaboration round
trip, `antiunify.py` is symbolic AU + clustering, `coverage.py` is the
Lean-exhaustiveness round trip + promotion, `fixpoint.py` is the round loop.
Deliberately not named `pipeline.py` — that name is already taken by the top-level
`pipeline/` directory (shell orchestration across phases) and would be confusing
inside a single phase's own module. See "Implementation workflow" above for the full
code-quality bar and the required process for writing any of this.

---

## Testing

Not pre-specified here — see "Implementation workflow" above: tests are proposed and
approved per stage as it's implemented, not decided speculatively before the code
exists. The one convention worth fixing in advance, since it's already established
elsewhere in the repo: mark any test that shells out to Lean with
`pytest.mark.integration`, same as `lemma-emission`, so the suite can run without a
Lean toolchain when needed.

---

## Future work

- **Proof reconstruction.** The coverage check's match skeleton (`coverage.py`) is
  structurally identical to a valid proof shape:
  ```
  lemma general (v : T) ... : g(v) := by
    match v with
    | p1 => <member 1's proof, pattern variables renamed to match>
    | p2 => <member 2's proof>
    ...
  ```
  This mirrors `lemma-emission/emitter.py`'s existing `_*_` case-arm substitution
  almost exactly. Deferred because it requires phase 5's proofs to be re-validated
  under renamed pattern variables, and needs its own design pass (proof text isn't
  just copy-pasted — identifiers introduced by the match arm may not match the
  identifiers the original member's proof was written against).
- **Multi-variable coverage.** Lift the one-fresh-variable promotion filter once
  single-variable generalization is validated on a real corpus. Requires proving the
  generalized statement for the full cross product of patterns (see "Why exactly one
  variable" above) — not just checking each variable's coverage independently, which
  is unsound — and deciding how to serialize a multi-variable match skeleton for Lean
  to check.
- **Indexed/dependent inductive types.** `Vector`, `Fin`-indexed families, and any
  type where matching one field constrains another. Needs real dependent
  pattern-match support in `coverage.py`'s serialization, not just flat constructor
  application.
- **Wiring into `pipeline/run_full.sh`.** Natural once phase 5 itself is wired in.
