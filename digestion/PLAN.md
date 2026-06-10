# Digestion Module — Implementation Plan

## Overview

Three files to fill in (`models.py`, `tracer.py`, `extractor.py`), a test suite, and
small Lean fixture files. Everything is specified by `CLAUDE.md`, `trace.schema.json`,
and the LeanDojo v2 API. The work is pure Python.

---

## Step 1 — `models.py`

Define dataclasses that mirror `trace.schema.json` exactly, from innermost to outermost:

- `Hypothesis(name, type)`
- `Obligation(hypotheses, goal)`
- `TacticSummary(directly_used, dependency_maps)`
- `TacticNode(id, tactic_text, input_obligation, output_obligations, summary, parent_id, child_ids)`
- `Declaration(name, statement, root_tactic_id, tactic_nodes)`
- `LeanProofTrace(source_file, declarations)`

Each class gets explicit `to_dict()` / `from_dict()` for JSON round-tripping. No logic here
— pure data.

---

## Step 2 — `tracer.py`

A thin wrapper that takes either `(url, commit)` or a local path, calls LeanDojo's
`trace()`, and returns a `TracedRepo`. Two public functions:

- `trace_github_repo(url: str, commit: str) -> TracedRepo`
- `trace_local_repo(path: str) -> TracedRepo`

Nothing else. All expensive LeanDojo machinery stays behind this boundary.

---

## Step 3 — `extractor.py`

Core logic. Four private helpers called by the public
`extract(traced_repo) -> list[LeanProofTrace]`:

**3a. Proof state parsing** `_parse_obligations(state: str) -> list[Obligation]`
- Empty / `"no goals"` → `[]`
- Split on blank lines → one block per goal
- Lines with ` : ` and no leading `⊢` → hypotheses; `⊢ …` line → goal

**3b. U computation** `_compute_U(tt: TracedTactic, hyp_names: set[str]) -> list[str]`
- Traverse `tt.ast` with `traverse_preorder`, collect `IdentNode` where
  `full_name is None` and name ∈ hyp_names
- Fallback regex scan over raw tactic text for names not yet collected
- Special-case `simp_all`, `simp [*]`, `assumption` → U = all hyp names

**3c. π computation** `_compute_pi(input_hyps, output_hyps, U) -> dict[str, list[str]]`
- Pass-throughs (same name + type) → map to `[h]`
- New hyps → scan type string for names in input context; fallback to U
- Must cover every key in output context (totality invariant)

**3d. Tree reconstruction** `_build_tree(tactics: list[TracedTactic]) -> list[TacticNode]`
- Assign integer IDs in the DFS pre-order LeanDojo already yields
- Reconstruct parent/child links by span containment (`pos`/`endPos`)
- Wire `child_ids[i]` ↔ `output_obligations[i]` ↔ `dependency_maps[i]`
  (co-indexing invariant from schema)

The top-level loop iterates `traced_repo.get_traced_theorems()`, skips non-tactic proofs,
calls the helpers, builds `Declaration` objects, groups by source file into
`LeanProofTrace` objects, validates each against `trace.schema.json` with `jsonschema`,
then writes to `data/traces/<repo_name>/`.

---

## Step 4 — Tests

### Lean fixture files to add (`tests/lean/`)

| File | Content | Tests |
|------|---------|-------|
| `simple.lean` | One theorem proved with `exact` or `rfl` (no branching) | Linear tree, trivial U and π |
| `branching.lean` | One theorem proved with `constructor` or `cases` (two subgoals) | Branching tree, co-indexing of `output_obligations` / `child_ids` |
| `hyp_use.lean` | Proof that explicitly references a named hypothesis | U computation via `IdentNode` traversal |
| `intro_hyp.lean` | Proof that introduces hypotheses via `intro` / `obtain` | π for newly introduced hypotheses |

5–10 lines each; minimal imports.

### Test files (`tests/`)

- `test_models.py` — round-trip `to_dict` / `from_dict` on hand-built instances;
  schema validation of serialized output
- `test_parse.py` — unit tests for `_parse_obligations` on hand-written state strings
  (no Lean needed)
- `test_pi.py` — unit tests for `_compute_pi` on synthetic `Hypothesis` lists
- `test_integration.py` — calls `trace_local_repo` on `tests/lean/`, checks schema
  validity, tree invariants, and co-indexing on each fixture

---

## Logical Build Order

1. `models.py` — no dependencies, unblocks everything
2. `tracer.py` — thin, quick
3. Parser helpers in `extractor.py` + `test_parse.py` / `test_pi.py` (no Lean needed)
4. Tree reconstruction in `extractor.py` + Lean fixtures + `test_integration.py`
5. Top-level `extract()` loop with schema validation + `test_models.py`
