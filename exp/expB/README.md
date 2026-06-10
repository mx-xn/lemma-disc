# Experiment B — Baseline Prover

Finds **hard theorems**: theorems an LLM cannot prove in 1 attempt + 2 fix-loops.

## Setup

1. **Create `input/theorems.json`** — one entry per theorem:

```json
{
  "lake_project": "path/to/your/lake/project",
  "imports": ["Mathlib"],
  "theorems": [
    {
      "theorem_id": "my_theorem",
      "lean_path": "LeanSrc/MyFile.lean",
      "statement_text": "(n m : Nat) : n + m = m + n",
      "local_ctx": "-- optional: local definitions preceding the theorem in the same file"
    }
  ]
}
```

- `lake_project` — path to the Lake project root (contains `lakefile.lean`)
- `imports` — Lean imports available to the prover
- `statement_text` — everything between the theorem name and `:=` in the source
- `local_ctx` — *(optional)* local definitions from the same file that precede the theorem; omit or leave blank if not needed

2. **Set `OPENAI_API_KEY`** in `/.env` or your environment.

## Run

```bash
cd /nas/lemma-disc
python -m exp.expB.run baseline
```

**Options:**

| Flag | Effect |
|------|--------|
| `--limit N` | Stop once N hard theorems are found |
| `--force` | Re-run even if output already exists |
| `--model M` | LLM model (default: `gpt-5.2`) |
| `--max-attempts K` | Attempts per theorem (default: 3 = 1 sample + 2 fixes) |
| `--lake-project P` | Override `lake_project` from the JSON |
| `--imports X,Y` | Override `imports` from the JSON |

## Output

| File | Contents |
|------|----------|
| `output/01_baseline.json` | Full record for every theorem attempted |
| `output/01_hard_set.json` | Failing theorems only — feeds stages 2 & 3 |
| `output/cache/` | LLM response cache (re-runs are free) |

---

## Stage 2 — Pick study (study a)

**Input files:**

- `output/01_hard_set.json` — produced by stage 1 (or your custom hard set)
- `input/candidates.json` — candidate lemma statements per theorem:

```json
{
  "theorem_id": ["stmt0", "stmt1", "stmt2"]
}
```

**Command:**

```bash
cd /nas/lemma-disc
python -m exp.expB.run pick
```

**Output:** `output/02_picks.json`

---

## Stage 3 — Solo study (study b)

**Input files:** same as stage 2 (`01_hard_set.json` + `input/candidates.json`)

**Command:**

```bash
cd /nas/lemma-disc
python -m exp.expB.run solo
```

**Options:**

| Flag | Effect |
|------|--------|
| `--num-hyps N` | Only test lemmas with exactly N hypotheses |
| `--num-lemmas N` | Sample up to N lemmas per theorem |
| `--seed N` | Random seed for sampling (default: 0) |

**Output:** `output/03_solo.json`

## Stage 4 - Aggregate:

```bash
cd /nas/lemma-disc
python -m exp.expB.run aggregate
```
