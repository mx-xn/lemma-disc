# Sorts_Mathlib — Train/Test Lemma Eval

End-to-end walkthrough for learning lemmas from `Sorts_Mathlib.lean` and
evaluating proof automation on the test split.

All commands run from `/nas/lemma-disc` inside `conda activate lemma`.

---

## Split

**Train set** (13 theorems — source material for lemma extraction):
`Sorted.nlt`, `Sorted.sub`, `Permut.refl`, `Permut.trans`, `count_app`,
`Permut.app`, `insert_sorted`, `insert_permut`, `insertionsort_permut`,
`left_less`, `right_less`, `double_left_less`, `double_right_less`

**Test set** (8 theorems — proved using learned lemmas):
`Permut.symm`, `insertionsort_sorted`, `insertionsort_correct`,
`merge_sorted`, `mergesort_sorted`, `merge_permut`, `mergesort_permut`,
`mergesort_correct`

---

## Prerequisite: author `train.json` and `test.json`

The split is explicitly defined, so skip `run split`. Write both files
directly to `exp/eval/domain_eval/output/`. Format mirrors
`exp/eval/sanity/output/theorems_sanity.json`:

```json
{
  "lake_project": "/nas/lemma-disc/data/input/MiniCodePropsLeanSrc",
  "imports": ["LeanSrc.Sorts_Mathlib"],
  "theorems": [
    {
      "theorem_id": "Sorted.nlt",
      "lean_path": "LeanSrc/Sorts_Mathlib.lean",
      "statement_text": "[LT T] {a b : T} {l : List T} (s : Sorted (a :: b :: l)) : Not (b < a)",
      "local_ctx": ""
    }
  ]
}
```

- `theorem_id` — the Lean declaration name; must match the name in the
  digestion trace (suffix matching is applied, so bare names like `Sorted.nlt`
  work even if the trace uses a fully-qualified prefix)
- `statement_text` — everything after `lemma <name>` and before `:= by` in
  `data/input/MiniCodePropsLeanSrc/LeanSrc/Sorts_Mathlib.lean`
- `local_ctx` — `""` for all theorems; all definitions live in the imported module

---

## Step 1 — Generate trace (Phase 1: Digestion)

```bash
python -m digestion.src.extractor \
    --local /nas/lemma-disc/data/input/MiniCodePropsLeanSrc \
    --files LeanSrc/Sorts_Mathlib.lean
```

Output: `data/traces/MiniCodePropsLeanSrc/Sorts_Mathlib.json`

Slow on first run (LeanDojo builds the Lean project). Cached on subsequent runs.

---

## Step 2 — Learn lemmas from training set (Phases 2–4)

```bash
python -m exp.eval.domain_eval.run learn \
    --method pipeline \
    --train exp/eval/domain_eval/input/sorts_mathlib/train.json \
    --trace data/traces/MiniCodePropsLeanSrc/Sorts_Mathlib.json \
    --output-dir exp/eval/domain_eval/output \
    --skip-fix \
    --pipeline-timeout 60000
```

Outputs in `exp/eval/domain_eval/output/`:

| File | Description |
|------|-------------|
| `train_trace.json` | Trace filtered to the 13 training declarations |
| `raw_lemmas.json` | Lemma objects from phases 2–4 (`statement`, `fragment_id`, `decl_name`) |
| `raw_lemmas.fragments.json` | Tactic fragment trees — required for lemma emission |
| `learned_lemmas.json` | LLM-fixed/validated statements |

Add `--skip-fix` to skip the LLM fixer if no API key is available.

---

## Step 3 — Lemma Emission (Phase 5): verify + synthesise proofs

```bash
python -m lemma_emission \
    --lemmas   exp/eval/domain_eval/output/raw_lemmas.json \
    --segments exp/eval/domain_eval/output/raw_lemmas.fragments.json \
    --output   exp/eval/domain_eval/output/verified_lemmas.json \
    --lake-project /nas/lemma-disc/data/input/MiniCodePropsLeanSrc \
    --imports  LeanSrc.Sorts_Mathlib
```

Pass `raw_lemmas.json` (phases 2–4 output), not `learned_lemmas.json`.
Emission does its own two-pass Lean validation (statement check via `sorry`,
then proof check with synthesised tactic body).

Output: `verified_lemmas.json` — each entry has `statement`, `proof`,
and `declaration`, all Lean-verified.

---

## Step 4 — Proof automation on test set

```bash
python -m exp.eval.domain_eval.run eval \
    --theorems exp/eval/domain_eval/output/test.json \
    --lemmas   exp/eval/domain_eval/output/verified_lemmas.json \
    --output-dir exp/eval/domain_eval/output/eval
```

Output: `exp/eval/domain_eval/output/eval/prove_results.json`

---

## File flow

```
Sorts_Mathlib.lean
        │  Step 1: digestion
        ▼
data/traces/.../Sorts_Mathlib.json
        │  Step 2: learn (phases 2–4 via run_full.sh)
        ▼
raw_lemmas.json + raw_lemmas.fragments.json
        │  Step 3: lemma_emission (phase 5)
        ▼
verified_lemmas.json
        │  Step 4: eval
        ▼
eval/prove_results.json
```
