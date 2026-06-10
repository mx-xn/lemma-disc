# exp/eval — Iterative Lemma-Augmented Evaluation Loop

Read the `lemma-discovery` skill before working here. Read `exp/expB/` to
understand the reused infrastructure.

## What this is

An iterative eval pipeline: prove a fixed theorem benchmark with an LLM, extract
reusable lemmas from (partial) proofs, augment the context, re-prove. Runs for
a fixed budget of `K` rounds or until all theorems succeed.

**Baselines:**
- `baseline` — vanilla LLM, no lemmas (empty hint pool).
- `llm-baseline` — same iterative loop as `loop`, including the same corpus
  construction step. But instead of running phases 1-5 on the corpus, feeds
  the corpus `.lean` files directly to an LLM and asks it to generate useful
  lemma statements. Skips phases 1-5, the registry, and all scoring. Tests
  whether our algorithmic extraction and learning add value over an LLM reading
  the same raw proof material.

---

## Prerequisites (must exist before implementing eval/)

1. **`exp/lib/`** — shared library promoted from `exp/expB/lib/`.  
   Files: `llm.py`, `lean_check.py`, `corpus.py`, `prover.py`  
   Add `exp/lib/__init__.py`.  
   Update `exp/expB/` imports: `from ..lib.X` → `from exp.lib.X`.

2. **`prover.py` API change** — `exp/expB/lib/prover.py` currently loads prompt
   templates from a hardcoded relative path (`parents[1]/prompts/`). After
   promotion to `exp/lib/prover.py`, make `prove()` accept template strings
   directly as parameters so each experiment can supply its own prompts:

   ```python
   def prove(thm, llm, *, lake_project, imports, max_attempts,
             baseline_template: str, fix_template: str) -> ProverResult
   ```

   Update `exp/expB/stages/` to load its own prompts and pass them in.

---

## Directory layout

```
exp/eval/
  CLAUDE.md             ← this file
  run.py                ← CLI: baseline | loop | round
  input/
    theorems.json       ← same schema as expB input (lake_project, imports, theorems[])
  output/
    round_00/           ← baseline results (01_baseline.json, 01_hard_set.json)
    round_01/           ← after first extraction
    ...
    lemma_registry.json ← persisted LemmaRegistry (grows across rounds)
  prompts/
    system.md           ← copy from expB/prompts/system.md
    solo.md             ← copy from expB/prompts/solo.md
    solo_fix.md         ← copy from expB/prompts/solo_fix.md
    fix_lemma.md        ← NEW (spec below)
    generalize.md       ← NEW (spec below)
    llm_rank.md         ← NEW (spec below)
  lib/
    __init__.py
    lemma_registry.py   ← LemmaRegistry dataclass + JSON I/O
    selector.py         ← selection algorithm
    lemma_fixer.py      ← batch LLM fixer for malformed lemma statements
    generalizer.py      ← optional LLM generalizer
    extractor.py        ← subprocess bridge to pipeline phases 1-5
  stages/
    __init__.py
    baseline.py         ← thin wrapper over exp/lib/prover (identical to expB baseline)
    prove.py            ← one round's prove step (pick-style: all lemmas in pool)
    extract.py          ← corpus construction + invoke extractor.py
    loop.py             ← outer iteration
    llm_baseline.py     ← same loop structure as loop.py; LLM generates lemmas
                           instead of phases 1-5 + registry
```

---

## Outer loop (pseudocode)

```python
def run_loop(theorems, rounds, model, generalize, max_hyps, max_pool,
             lake_project, imports):

    registry = LemmaRegistry.load_or_empty(output_dir / "lemma_registry.json")
    unsolved = list(theorems)   # all theorems start unsolved
    all_results = {}            # theorem_id -> latest ProverResult

    for r in range(rounds):
        round_dir = output_dir / f"round_{r+1:02d}"

        # ── Step 1: prove ────────────────────────────────────────────────────
        lemma_pool = registry.select(max_n=max_pool, max_hyps=max_hyps, llm=llm,
                                     lake_project=lake_project, imports=imports)
        round_results = prove_round(unsolved, lemma_pool, llm, lake_project, imports)
        all_results.update(round_results)

        # record usage signal: which lemmas were cited in successful proofs
        registry.record_usage(round_results)
        registry.save(output_dir / "lemma_registry.json")

        newly_solved = [t for t in unsolved if round_results[t.theorem_id].ok]
        unsolved = [t for t in unsolved if not round_results[t.theorem_id].ok]

        save_round(round_dir, round_results)

        if not unsolved:
            break  # all done

        # ── Step 2: build extraction corpus ─────────────────────────────────
        # solved: use real proof body; unsolved: replace failing subgoals with admit
        corpus_files = build_corpus(all_results, theorems, lake_project, imports, round_dir)

        # ── Step 3: extract lemmas (phases 1-5) ─────────────────────────────
        raw_lemmas = extract_lemmas(corpus_files, round_dir)   # list of statement strings

        # ── Step 4: fix malformed lemmas ─────────────────────────────────────
        fixed_lemmas = fix_lemmas(raw_lemmas, llm, lake_project, imports)

        # ── Step 5: (optional) generalize ────────────────────────────────────
        if generalize:
            fixed_lemmas = generalize_lemmas(fixed_lemmas, llm, lake_project, imports)

        # ── Step 6: register new lemmas ──────────────────────────────────────
        registry.add_extracted(fixed_lemmas)
        registry.save(output_dir / "lemma_registry.json")
```

No early break on zero newly-solved: partial proofs (with admits) still yield
useful lemma candidates. Loop runs until `unsolved` is empty or budget is
exhausted.

---

## Corpus construction (`stages/extract.py: build_corpus`)

For each theorem T:
- **Solved** (round_results[T].ok): write `<proof_body>` as the actual proof.
- **Unsolved**: take the last attempted proof body; replace each failing tactic
  (identified by Lean error line numbers in `final_error`) with `admit`.
  The phase 1-5 pipeline already ignores `admit` nodes during lemma extraction
  (this contract is assumed — the digestion/support modules handle it).

Output: a temp lake project directory populated with `.lean` files, one per
theorem, ready for phase 1 (digestion).

---

## LemmaRegistry (`lib/lemma_registry.py`)

```python
@dataclass
class LemmaEntry:
    statement: str
    extraction_freq: int = 0      # # corpus fragments it was extracted from
    success_cited: int = 0        # # rounds where cited in a verified-ok proof
    attempted_cited: int = 0      # # rounds where cited in a failed proof attempt

    def score(self) -> float:
        return (self.success_cited * 1.0
                + self.attempted_cited * 0.2
                + math.log1p(self.extraction_freq) * 0.5)
```

Key: `statement` string (deduplicated by exact string after stripping whitespace).

`record_usage(round_results)`: for each theorem, parse `<used_lemmas>` indices
from each attempt's raw LLM response. Increment `success_cited` if `result.ok`,
else `attempted_cited`. Only count one increment per lemma per round (not per
attempt).

Persisted as `output/lemma_registry.json`.

---

## Selection algorithm (`lib/selector.py: select`)

```python
def select(registry, max_n, max_hyps, llm, lake_project, imports) -> list[str]:
    candidates = [e for e in registry.entries() if num_hyps(e.statement) <= max_hyps]
    candidates.sort(key=lambda e: e.score(), reverse=True)
    top = [e.statement for e in candidates[:max_n]]

    # If slots remain and there are unscored lemmas (score == 0), ask LLM to rank them
    tail = [e for e in candidates[max_n:] if e.score() == 0.0]
    if len(top) < max_n and tail:
        ranked_tail = llm_rank(tail, llm)       # calls LLM with llm_rank.md
        # verify none were mutated
        ranked_tail = [s for s in ranked_tail if s in {e.statement for e in tail}]
        top += ranked_tail[:max_n - len(top)]

    return top
```

`num_hyps` comes from the existing `exp/count_hyps.py` module (already in the
codebase).

---

## fix_lemmas (`lib/lemma_fixer.py`)

Runs up to `max_fix_rounds` (default 2) iterations. Each iteration only retries
the statements that are still broken — already-fixed ones are not re-sent.

```python
def fix_lemmas(statements, llm, lake_project, imports, max_fix_rounds=2) -> list[str]:
    current = list(statements)
    valid_mask = [False] * len(current)  # tracks which are confirmed valid

    for _ in range(max_fix_rounds):
        # Validate only those not yet confirmed valid
        to_check = {i: current[i] for i in range(len(current)) if not valid_mask[i]}
        broken = batch_validate(to_check, lake_project, imports)  # {idx: error_msg}

        # Mark newly passing as valid
        for i in to_check:
            if i not in broken:
                valid_mask[i] = True

        if not broken:
            break  # all remaining passed

        # LLM fix only the still-broken ones
        for idx, err in broken.items():
            fixed_stmt = llm_fix_one(current[idx], err, llm)
            if fixed_stmt:
                current[idx] = fixed_stmt

    # Final validation pass to confirm last round's fixes
    to_check = {i: current[i] for i in range(len(current)) if not valid_mask[i]}
    broken = batch_validate(to_check, lake_project, imports)
    for i in to_check:
        if i not in broken:
            valid_mask[i] = True

    return [current[i] for i in range(len(current)) if valid_mask[i]]
```

`batch_validate`: writes one `.lean` file with `lemma validate_N : <stmt> := by sorry`
for each statement, runs one `lean_check` call, parses errors by `validate_N`
name using existing `_parse_errors` in `lean_check.py`. Uses the same
`lake_project` and `imports` as the theorem benchmark. The sorry warning is
already filtered by `lean_check.py`.

---

## generalizer (`lib/generalizer.py`)

```python
def generalize_one(stmt, llm, lake_project, imports) -> str:
    generalized = llm_generalize(stmt, llm)   # prompt: generalize.md
    if lean_check_stmt(generalized, lake_project, imports):
        return generalized
    return stmt  # fall back to original
```

Called only when `--generalize` flag is set.

---

## extractor (`lib/extractor.py`)

Thin subprocess wrapper that invokes the full phase 1-5 pipeline on a directory
of `.lean` files and returns a list of lemma statement strings parsed from
the final `lemmas.json` (schema: `schemas/lemmas.schema.json`, field `statement`).

**This module is a stub for now.** Fill in the subprocess call details once the
pipeline is runnable end-to-end. Interface:

```python
def extract_lemmas(lean_files_dir: Path, work_dir: Path) -> list[str]:
    """Run phases 1-5 on lean_files_dir; return list of statement strings."""
    ...
```

---

## Prompts to write

### `prompts/fix_lemma.md`
Input placeholders: `<<statement>>`, `<<error>>`, `<<imports>>`  
Task: "The following Lean 4 lemma statement failed to type-check. Fix it so it
is a valid Lean 4 binder-syntax statement `(p : T) ... : conclusion`. Return
ONLY the corrected statement string — no `lemma`/`theorem` keyword, no `:= by`,
no fences."

### `prompts/generalize.md`
Input placeholders: `<<statement>>`, `<<imports>>`  
Task: "The following Lean 4 lemma is specialized. Produce a strictly more
general version by replacing concrete types/values with universally quantified
variables. Return ONLY the statement string in binder syntax."

### `prompts/llm_generate.md`
Input placeholders: `<<imports>>`, `<<corpus>>` (concatenated content of the
corpus `.lean` files, same material phases 1-5 would receive)  
Task: "The following Lean 4 files contain theorem proofs (some with `admit`s).
Extract or invent reusable lemma statements that would be broadly useful as
proof hints. Return one statement per line in binder syntax — no
`lemma`/`theorem` keyword, no `:= by`, no fences."

### `prompts/llm_rank.md`
Input placeholders: `<<imports>>`, `<<candidates>>` (newline-separated, indexed L0..Ln)  
Task: "Rank the following Lean 4 lemma statements by how broadly useful they
are likely to be as proof hints. Return a newline-separated list of indices
(0-based integers), most useful first, no other text."

---

## CLI (`run.py`)

```
python -m exp.eval.run baseline     [--theorems P] [--output-dir P] [--model M]
                                    [--max-attempts K] [--workers N] [--force]
python -m exp.eval.run llm-baseline [--theorems P] [--output-dir P] [--model M]
                                    [--rounds K] [--max-attempts K]
                                    [--max-fix-rounds K (default 2)]
                                    [--workers N] [--force]
python -m exp.eval.run loop         [--theorems P] [--output-dir P] [--model M]
                                    [--rounds K] [--max-attempts K]
                                    [--max-hyps K (default 5)] [--max-pool N]
                                    [--max-fix-rounds K (default 2)]
                                    [--generalize] [--workers N] [--force]
```

---

## TODO — in implementation order

1. **Promote `exp/expB/lib/` → `exp/lib/`**  
   Move 4 files, add `exp/lib/__init__.py`, update expB imports.  
   Change `prove()` signature to accept `baseline_template` and `fix_template`
   as string params; update expB stages to load and pass their own prompts.

2. **Copy reused prompts**  
   Copy `system.md`, `solo.md`, `solo_fix.md` from `exp/expB/prompts/` into
   `exp/eval/prompts/`.

3. **Write the three new prompts**  
   `fix_lemma.md`, `generalize.md`, `llm_rank.md` in `exp/eval/prompts/`.

4. **`exp/eval/lib/lemma_registry.py`**  
   `LemmaEntry` dataclass, `LemmaRegistry` with `load_or_empty`, `save`,
   `add_extracted`, `record_usage`, `entries`. JSON I/O to
   `output/lemma_registry.json`.

5. **`exp/eval/lib/selector.py`**  
   `select(registry, max_n, max_hyps, llm, ...) -> list[str]` as specced above.
   Import `num_hyps` from `exp.count_hyps`.

6. **`exp/eval/lib/lemma_fixer.py`**  
   `batch_validate` + `fix_lemmas` as specced above.

7. **`exp/eval/lib/generalizer.py`**  
   `generalize_one` and `generalize_lemmas(stmts, llm, ...) -> list[str]`.

8. **`exp/eval/lib/extractor.py`**  
   Stub with the correct interface. Fill in subprocess logic when pipeline is
   ready.

9. **`exp/eval/stages/baseline.py`**  
   Thin wrapper: same logic as `exp/expB/stages/baseline.py` but imports from
   `exp.lib`. No lemmas are provided — the prover runs with an empty hint pool,
   the same `max_attempts` budget as loop rounds.  
   Outputs `round_00/01_baseline.json` and `round_00/01_hard_set.json`.

9b. **`exp/eval/stages/llm_baseline.py`** and **`prompts/llm_generate.md`**  
    Same outer loop structure as `loop.py` including the corpus construction
    step (`build_corpus` is reused unchanged). After the corpus is built,
    instead of calling `extractor.extract_lemmas`, concatenate the corpus
    `.lean` files and send them to the LLM via `llm_generate.md`. The LLM's
    output (a list of candidate statements) is then validated and fixed with
    the same `fix_lemmas` step (no generalization). The resulting pool is used
    directly for the next round's `prove_round` call — no registry, no scoring,
    pool rebuilt from scratch each round.  
    Outputs `llm_baseline/round_NN/prove_results.json` (same schema as loop).

10. **`exp/eval/stages/prove.py`**  
    One round's prove step. Identical to `exp/expB/stages/solo.py` with two
    differences: (a) candidates come from `registry.select(...)` not a static
    file, (b) raw LLM responses are stored so `registry.record_usage` can parse
    `<used_lemmas>` afterwards.  
    **Schema note:** `prove_results.json` must store `raw_response: str` on each
    attempt alongside the existing `proof_body`, `ok`, `error_text` fields.
    expB's `Attempt` dataclass only has the latter three — add `raw_response`
    when defining the `Attempt` equivalent in `exp/eval/`.  
    Outputs `round_NN/prove_results.json`.

11. **`exp/eval/stages/extract.py`**  
    `build_corpus` (writes .lean files for solved + admit-patched unsolved) +
    calls `extractor.extract_lemmas`. Outputs extracted statement strings.

12. **`exp/eval/stages/loop.py`**  
    Implements `run_loop` as specced above. Orchestrates stages 9-11 +
    fixer + generalizer + registry updates.

13. **`exp/eval/run.py`**  
    CLI entrypoint. `baseline` and `loop` subcommands.
