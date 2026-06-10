# Experiment B — Design

## Goal

Show that **lemmas with fewer hypotheses are easier for an LLM to apply**.
Operationalized on the existing corpus via two sub-studies:

- **(a)** Given a hard theorem and a menu of candidate lemmas, which one does
  the LLM pick? Correlate the pick with `num_hyps`.
- **(b)** Given a hard theorem and *one* candidate lemma as a hint, can the
  LLM close the proof? Correlate success rate with `num_hyps`.

"Hard" = the LLM fails to close the proof in ≤3 fix loops with no hint.

## Pipeline

Four stages, run in order. Each stage writes its artifact to `expB/output/`
and is independently re-runnable from the previous artifact.

```
                   ┌─────────────────────┐
   theorem corpus ─► 1. baseline prover  ├── 01_baseline.json   (hard set)
                   └──────────┬──────────┘
                              │
                  hard set ◄──┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
  ┌──────────────────────┐         ┌──────────────────────┐
  │ 2. pick (study a)    │         │ 3. solo (study b)    │
  │  T + [L1..Ln] → pick │         │  T + Li → ok/fail    │
  └──────────┬───────────┘         └──────────┬───────────┘
             │                                │
             ▼                                ▼
       02_picks.json                    03_solo.json
             │                                │
             └──────────────┬─────────────────┘
                            ▼
                ┌─────────────────────┐
                │ 4. aggregate + plot │
                └─────────────────────┘
                            │
                            ▼
                   04_plots/  (figures + tsv)
```

### Stage 1 — baseline prover

For each theorem `T` in the corpus, run the **fix-loop prover** (LLM + Lean
check, ≤3 fix loops) with **no hint**. Record `{T → ok?, attempts}`.
Theorems that fail → **hard set** `H`. These are what the sub-studies run on.

### Stage 2 — pick (study a)

For each `T ∈ H` with candidate lemmas `[L1..Ln]` (de-duped by statement):
build a prompt that shows `T` plus the menu of lemma statements (no proofs,
identifiers anonymized), and ask the LLM to attempt closing `T`, and use any provided lemmas if it finds any helpful. Record which provided lemmas was used. We also record if each theorem succeeded as extra data. The main goal of this stage is to gauge LLM's preference signal vs `num_hyps`.

### Stage 3 — solo (study b)

For each `(T, Li)` pair with `T ∈ H`: run the fix-loop prover with `Li`
injected as a named auxiliary lemma (statement only — proof left as `admit`).
Record `{T, Li → ok?}`. This measures, per lemma, the marginal lift it
gives to the prover.

### Stage 4 — aggregate + plot

Compute `num_hyps` (and `proof_effort`) for every candidate via the existing
`exp/count_hyps.py`. Produce:

- (a) histogram + scatter: pick frequency vs `num_hyps`.
- (b) success rate vs `num_hyps` (binned), with N per bin.

## Directory layout

All Experiment B code, inputs, and outputs live under `exp/expB/`. The only
shared file outside that tree is `exp/count_hyps.py` (used by other
experiments too).

```
exp/
├── count_hyps.py             # shared metric (already present)
├── design_B.md               # this doc
└── expB/
    ├── run.py                # CLI orchestrator: `python -m expB.run <stage>`
    ├── stages/               # one module per pipeline stage
    │   ├── baseline.py       # stage 1
    │   ├── pick.py           # stage 2
    │   ├── solo.py           # stage 3
    │   └── aggregate.py      # stage 4
    ├── lib/                  # cross-stage utilities
    │   ├── corpus.py         # load theorems + candidate lemmas
    │   ├── lean_check.py     # synthesize .lean → `lake env lean` → (ok, err)
    │   ├── llm.py            # OpenAI client (gpt-5.2), retries, response cache
    │   └── prover.py         # fix-loop driver: prompt → check → retry ≤3
    ├── prompts/              # prompt templates as plain .txt / .md
    │   ├── baseline.md
    │   ├── pick.md
    │   └── solo.md
    ├── input/                # experiment-scoped inputs
    │   ├── theorems.json     # {theorem_id, lean_path, statement, ...}
    │   └── candidates.json   # {theorem_id → [lemma statements]}
    └── output/               # all stage artifacts land here
        ├── 01_baseline.json
        ├── 02_picks.json
        ├── 03_solo.json
        ├── 04_plots/
        │   ├── pick_vs_hyps.png
        │   ├── success_vs_hyps.png
        │   └── summary.tsv
        └── cache/            # llm.py response cache (gitignored)
```

Rationale:
- `stages/` vs `lib/` separates *what each stage does* from *machinery the
  stages share*. Adding a new stage means one file in `stages/`; refactoring
  the LLM client doesn't touch any stage code.
- `prompts/` keeps long prompt text out of Python source — easier to iterate
  on wording without diff noise in the orchestrator.
- `input/` and `output/` are sibling top-level dirs under `expB/`, so the
  whole experiment is one self-contained, copyable tree.
- Stage outputs are numbered (`01_…`, `02_…`) so the order matches the
  pipeline and `ls` sorts correctly.

## Component responsibilities

| Module | Role |
|--------|------|
| `lib/corpus.py` | Read `input/theorems.json` and `input/candidates.json`; expose typed records (`Theorem`, `Candidate`) consumed by all stages. |
| `lib/lean_check.py` | Drop a synthesized `.lean` file into the corpus Lake project, run `lake env lean`, return `(ok, error_text)`. Single entry point — the only thing that touches the filesystem outside `expB/`. |
| `lib/llm.py` | Thin OpenAI wrapper (model: gpt-5.2). Handles retries, deterministic seeding where supported, and on-disk response caching keyed by `(prompt hash, model, params)` so reruns are free. |
| `lib/prover.py` | The fix-loop prover used by stages 1 and 3: prompt LLM → `lean_check` → if fail, append error to history and retry up to 3 times. Returns the full attempt trace. |
| `stages/baseline.py` | Iterate theorems, call `prover.prove(T)`, write `01_baseline.json`. Records the hard set inline. |
| `stages/pick.py` | For each hard theorem, build menu prompt from `prompts/pick.md`, single LLM call, write `02_picks.json`. |
| `stages/solo.py` | For each `(T, L)` with `T ∈ H`, call `prover.prove(T, hint=L)`, write `03_solo.json`. |
| `stages/aggregate.py` | Join stage 2 + 3 outputs with `count_hyps` metrics; emit `04_plots/`. |
| `run.py` | CLI: `python -m expB.run {baseline,pick,solo,aggregate,all}`. Each subcommand skips work if its artifact already exists (override with `--force`). |

## Inputs / outputs

**Inputs** (`expB/input/`):

- `theorems.json` — list of `{theorem_id, lean_path, statement_text}`.
- `candidates.json` — map `theorem_id → [lemma statement strings]`.

How these get populated is **out of scope** for this doc — they're the
contract the pipeline reads from. They can be hand-curated, re-extracted via
the main pipeline, or pulled from `data/prop_*_lemmas.json`.

**Outputs** (`expB/output/`):

| File | Produced by | Shape |
|------|-------------|-------|
| `01_baseline.json` | stage 1 | `{theorem_id: {ok, attempts, final_error}}` |
| `02_picks.json`    | stage 2 | `{theorem_id: {pick_index, pick_statement, all_candidates}}` |
| `03_solo.json`     | stage 3 | `{theorem_id: {lemma_index: {ok, attempts}}}` |
| `04_plots/`        | stage 4 | PNGs + `summary.tsv` |

## Open decisions (left for the implementation step)

- **Theorem corpus size.** Start with the props already in `data/`
  (prop_56/57/85, etc.); scale up once the loop works end-to-end.
- **How "hint" is injected in stage 3.** Likely: prepend
  `theorem Li : <stmt> := sorry` above the target and let the LLM use it;
  revisit if the LLM refuses to trust a `sorry`-backed lemma.
- **LLM params.** Temperature, max tokens, seed — pick during stage 1
  shake-out, then freeze for stages 2 and 3.
