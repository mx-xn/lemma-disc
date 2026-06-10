# Sanity Check

Compares LLM proof success **with** vs. **without** the pre-learned lemma library on the same theorem set, in a single run.

- **Condition A (without)** — `run_baseline`: LLM sees no hint section at all.
- **Condition B (with)** — `prove_round`: LLM sees all lemma statements from `Lemmas.lean` as admitted hints.

## Prerequisites

| What | Default path |
|------|-------------|
| Theorems | `exp/expB/input/theorems.json` |
| Learned lemmas | `data/input/MiniCodePropsLeanSrc/LeanSrc/Lemmas.lean` |

Theorems are automatically filtered to those covered in `Lemmas.lean` (the 9 `prop_N` IDs). The filtered set is written to `output/theorems_sanity.json` so you can inspect it.

## Run

```bash
# from /nas/lemma-disc
python -m exp.eval.sanity.run
```

Key options:

```
--theorems PATH           theorems.json  (default: exp/expB/input/theorems.json)
--lemmas   PATH           Lemmas.lean    (default: data/input/.../Lemmas.lean)
--output-dir DIR          where to write results  (default: exp/eval/sanity/output/)
--model MODEL             LLM model string  (default: gpt-5.2)
--max-attempts N          fix-loop budget per theorem  (default: 3)
--workers N               parallel workers  (default: 1)
--force                   overwrite existing results
--theorem-ids ID [ID...]  run only specific theorem IDs; default: all covered by Lemmas.lean
--retriever {none,byt5}   retriever for condition B  (default: none = pass all lemmas)
--top-k K                 retrieve top-K lemmas per theorem (required with --retriever byt5)
```

Examples:

```bash
# Run all covered theorems, no retriever
python -m exp.eval.sanity.run

# Run two specific theorems only
python -m exp.eval.sanity.run --theorem-ids prop_29 prop_36

# Run with ByT5 retriever, top-5 lemmas per theorem
python -m exp.eval.sanity.run --retriever byt5 --top-k 5

# Combine: two theorems, retriever, custom output dir
python -m exp.eval.sanity.run --theorem-ids prop_29 --retriever byt5 --top-k 5 --output-dir /tmp/test_run
```

## Outputs

```
output/
  theorems_sanity.json          filtered theorem set (9 props)
  without_lemmas/
    01_baseline.json            full per-theorem attempt records
    01_hard_set.json            failing subset
  with_lemmas/
    prove_results.json          full per-theorem attempt records
  comparison.json               side-by-side summary  ← main result
```

`comparison.json` shape:

```json
{
  "total_theorems": 9,
  "lemma_pool_size": 102,
  "without_lemmas": {"solved": 3, "failed": 6},
  "with_lemmas":    {"solved": 7, "failed": 2},
  "per_theorem": {
    "prop_29": {"without_lemmas": false, "with_lemmas": true},
    ...
  }
}
```

## Tests

```bash
python -m pytest exp/eval/sanity/ -v
```
