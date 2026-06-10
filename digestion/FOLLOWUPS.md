# Digestion follow-ups

Open issues whose root cause is in this module's parsing of Lean's pretty-printed
proof states. Fix them here before downstream phases consume the trace.

---

## Inaccessible-name (`✝` dagger) rename

### Symptom

Lemma statements emitted by phase 4 contain identifiers with the `✝` suffix:

```
(h1 : … ∧ ((h✝ : [].length = ys.length) → (head✝ : β) → (tail✝ : List β) → …))
```

These names cannot be referenced by tactics in emitted Lean code, so any
downstream proof script (phase 5) using them will not type-check.

### Why it happens

Lean tags any binding the elaborator introduces *without a user-supplied name*
with a trailing `✝`, e.g. from `cases`, `induction`, `intro` (no arg), pattern-
matched arguments. Multiple inaccessible bindings sharing a root are
disambiguated with unicode superscripts: `x✝`, `x✝¹`, `x✝²`, …

The names appear in two places in the pretty-printed proof state:
1. As hypothesis names (`head✝ : β`).
2. As references inside other hypothesis types and the goal
   (`[].length = (head✝ :: tail✝).length`).

[`_parse_obligations`](src/extractor.py) captures both verbatim. Daggers then
propagate through phases 2–4 into `LemmaObj.statement`.

### Fix design

A per-**declaration** rename pass (not per-obligation — see scope note below).

1. After building all `Obligation`s for one `Declaration`, walk every
   `Hypothesis.name`, `Hypothesis.type`, and `Obligation.goal` in the
   declaration.
2. Find every dagger occurrence, key it by `(root, superscript_count)` so
   `x✝` and `x✝¹` are different keys.
3. Generate one fresh name per key. Naming scheme: `x✝` → `x_1`,
   `x✝¹` → `x_2`, etc.; bump the numeric suffix to dodge any collision with
   a non-dagger identifier already used anywhere in the declaration.
4. Apply the rename with whole-word substitution (identifier-boundary aware,
   not raw `str.replace`) to every name / type / goal in the declaration.

#### Scope note

Per-obligation rename is *wrong*: the same `ys✝` can appear in multiple
obligations of a single proof tree (the input obligation of one tactic vs. the
output obligation of another), and phase 4's `Lem(·)` construction splices
strings from sibling obligations together. Mismatched per-obligation rename
maps would produce syntactically inconsistent output. Per-declaration is the
smallest scope that keeps every co-occurring reference aligned.

### Where to put it

- New helper at the top of [`src/extractor.py`](src/extractor.py),
  e.g. `_dedagger_declaration(decl: Declaration) -> Declaration`.
- Call site: right after the declaration is fully assembled, before it is
  serialized. The existing parse path is unchanged — the rename pass runs once
  per declaration as a post-processing step.

### Estimated size

~40–60 lines plus a unit test. The test fixture should include:
- Daggers as hypothesis names.
- Dagger references *inside* another hyp's type and inside the goal.
- The `x✝` / `x✝¹` superscript-disambiguated case.
- A non-dagger identifier whose name happens to be the candidate (e.g. `x_1`
  already taken) — the generator must skip past it.

### Snapshot impact

`tests/snapshots/{zip_append_of_length_eq,prop_85,entangled_reasoning}.json`
all contain daggers today; once the rename pass lands they will need to be
regenerated with `pytest tests/test_integration.py -m integration --snapshot-update`
(see the docstring in `test_integration.py`). The downstream demo data under
`/data/*.fragments.json` and `/data/*_lemmas.json` should be regenerated in the
same pass.

### Related fix already shipped

The `:= <value>` strip for let-bound hypotheses is in
[`_parse_obligations`](src/extractor.py) — same parsing layer, different
artifact. See `test_let_bound_hypothesis_strips_value` for the contract.
