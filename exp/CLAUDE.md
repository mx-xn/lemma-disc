# exp/ — lemma discovery heuristic validation

Prototype experiments that empirically test heuristics used by the main lemma
discovery pipeline (see `../` for the pipeline itself; consult the
`lemma-discovery` skill for pipeline-level context when relevant).

## Heuristic under test

When a proof tree has branches, cutting a hole inside a branched subtree
produces a lemma with many hypotheses, which makes it harder to reuse.
**Conclusion:** only cut holes inside chain (non-branching) subtrees.

## Experiments

### A — Branching holes inflate hypothesis count and deflate reuse frequency

Show that lemmas with holes in branches have more hypotheses than chain
lemmas, and that hypothesis count correlates with reduced reuse frequency.

- Corpus: `m` proofs. For each proof, extract `n` candidate lemmas (varying
  the location: branch vs. chain).
- Anti-unify lemmas across the corpus using an LLM: collapse syntactic
  variants into unique lemmas; then count their appearance frequency.
- Plot: lemma appearance frequency vs. number of hypotheses.

### B — Lemmas with more hypotheses are harder to apply

Show the lemmas with less hyps can be more easily used to finish a theorem proof by LLMs.

Therefore, we have two sub-studies on the existing corpus:

**LLM use-test:** find theorems where an LLM fails to close the proof 
within 3 fix loops. Extract candidate lemmas from those theorems and:
- (a) feed all extracted lemmas to the LLM, record which it picks
  (cross-reference choice against #hyps);
- (b) feed each lemma individually, compare success rates.

## What's already here

- `count_hyps.py` — computes two complexity metrics for a Lean 4 lemma
  statement string: `num_hyps` (context-match difficulty) and
  `proof_effort` (total propositional sub-obligations). CLI accepts either
  `--stmt "<statement>"` or a lemmas JSON file. See the module docstring
  for the exact rules.
- `data/` — input lemma JSON files (`*_lemmas.json`,
  `*_lemmas.fragments.json`) and `input/` / `output/` / `lemmas/`
  subdirectories for experiment artifacts.

## Conventions

- Lemma JSON shape: either a top-level list of lemma objects, or
  `{"lemmas": [...]}`. Each object has at least `statement`, and
  optionally `fragment_id` and `decl_name`.
- Prefer adding new scripts alongside `count_hyps.py` rather than nesting
  deeply; keep each experiment self-contained and runnable from `exp/`.

## Known upstream issue: free identifiers not lifted into binders

Phase4 lemma extraction (or whichever component serializes `statement`)
sometimes preserves Lean's surface display form, in which section-bound
variables are omitted from the binder prefix even though they appear in
the statement body. The corresponding `premises` list is also missing
those names. Surveyed corpora: ~100% of lemmas in `prop_85`, `prop_56`,
`zip_append_of_length_eq`, and 25/30 in `prop_57` exhibit at least one
free lowercase identifier.

**Workaround:** `lemma_normalize.rename_free_variables` renames free
identifiers to `_f0, _f1, ...` so syntactic clustering treats
alpha-equivalent statements as equal. The workaround is isolated to a
clearly-marked block in `lemma_normalize.py`; removal instructions are
in the block header. Remove the workaround once upstream lifts all free
identifiers into top-level binders and reports them in `premises`.
