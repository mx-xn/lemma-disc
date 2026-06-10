# Digestion Module

## Purpose

Extract obligation-annotated proof trees from Lean 4 repositories and emit one
JSON file per source file, conforming to `../schemas/trace.schema.json`.

Each JSON file contains a `LeanProofTrace`: a list of `Declaration`s, each
holding a flat list of `TacticNode`s whose tree structure is encoded via
`parent_id` / `child_ids`, with `input_obligation`, `output_obligations`, and a
`TacticSummary` (U and πᵢ) at every node.

---

## I/O

**Input**: a Lean 4 repository — either a GitHub repo `(url, commit)` or a path
to a local git repository. Passed as CLI arguments or config to `extractor.py`.

**Output**: one `LeanProofTrace` JSON file per Lean source file, written to
`data/traces/<repo_name>/`. Files are validated against
`../schemas/trace.schema.json` before writing.

---

## File Responsibilities

| File | Role |
|------|------|
| `src/tracer.py` | Thin wrapper around the LeanDojo v2 tracing API. Given a GitHub `(url, commit)` or a local repo path, returns a `TracedRepo` ready for extraction. |
| `src/extractor.py` | Core logic: iterates `TracedRepo` theorems, reconstructs proof trees, computes obligations and tactic summaries, emits JSON. |
| `src/models.py` | Dataclasses mirroring the schema (`Hypothesis`, `Obligation`, `TacticSummary`, `TacticNode`, `Declaration`, `LeanProofTrace`). No raw dicts past the parse boundary. |

> Note: the scaffold named this `lsp_client.py` but there is no LSP server involved.
> Rename to `tracer.py`.

---

## Key Dependency: LeanDojo v2

**Package**: `lean-dojo-v2` (installed in the `lemma` conda env).  
**Source** (for reading specific class definitions): `lean_dojo_v2/lean_dojo/data_extraction/`

Relevant modules to read when you need implementation details:
- `traced_data.py` — `TracedRepo`, `TracedFile`, `TracedTheorem`, `TracedTactic`
- `ast.py` — `IdentNode`, `TacticTacticseq1IndentedNode`, `TacticTacticseqbracketedNode`, `Node.traverse_preorder`
- `trace.py` — `trace()`, `get_traced_repo_path()`

**Do not** invoke `lake env lean --run ExtractData.lean` directly. That is an internal detail of `trace.py`. Use the public API below.

---

## Canonical Entry Pattern

```python
from lean_dojo_v2.lean_dojo import LeanGitRepo
from lean_dojo_v2.lean_dojo.data_extraction.trace import trace
from lean_dojo_v2.lean_dojo.data_extraction.ast import IdentNode

# GitHub repo:
repo = LeanGitRepo(url, commit)

# Local git repo (directory must have a .git folder):
repo = LeanGitRepo.from_path("/path/to/local/lean/repo")

# trace() calls ExtractData.lean internally via lake, caches as *.trace.xml.
# Expensive first time; reads from cache on subsequent runs.
traced_repo = trace(repo, build_deps=False)

for thm in traced_repo.get_traced_theorems():
    if not thm.has_tactic_proof():
        continue
    tactics = list(thm.get_traced_tactics(atomic_only=False))
    # tactics: List[TracedTactic], DFS pre-order over the proof AST
    # Use atomic_only=False — we need the full hierarchy, not just leaf tactics.
```

Each `TracedTactic` (`tt`) exposes:
- `tt.ast.state_before: str` — proof state before the tactic
- `tt.ast.state_after: str` — proof state after the tactic
- `tt.tactic: str` — raw tactic source text
- `tt.ast` — traversable AST node; call `.traverse_preorder(fn, node_cls=None)`

**Format note**: `ExtractData.lean` produces `*.ast.json` (raw output).
`trace()` serializes these into `*.trace.xml` for caching and returns a
`TracedRepo` loaded from that cache. Both formats live in the same codebase;
`trace()` handles the conversion transparently.

---

## Parsing Proof States into Obligations

`state_before` / `state_after` are pretty-printed Lean proof states. Format:

```
h₁ : T₁
h₂ : T₂
⊢ G
```

For multi-goal states (branching tactics), goals are separated by blank lines,
each block having its own `name : type` context lines and a `⊢ G` line.

**Parsing algorithm:**
1. If state is `""` or `"no goals"` → empty obligation list.
2. Split on blank lines to get per-goal blocks.
3. Within each block: lines containing ` : ` and not starting with `⊢` are
   hypotheses; the `⊢ ...` line is the goal.
4. Build `Obligation(hypotheses=[...], goal=goal_str)` for each block.

`state_before` → single `Obligation` (input).  
`state_after` → list of `Obligation`s (outputs), one per remaining goal.

---

## Computing U (directly_used hypotheses)

U ⊆ Γ is the set of hypothesis names in `state_before` that the tactic
**directly references**.

**Key invariant in `IdentNode`** (see `ast.py`): `full_name` is `None` iff the
identifier refers to a local variable (hypothesis). Global constants always have
a non-None `full_name`. Therefore: traverse `tt.ast` with `traverse_preorder`,
collect `IdentNode`s where `full_name is None` and `val ∈ hyp_names(state_before)`.

**Fallback**: AST traversal can miss some references (e.g. names used in dot
notation like `hab.subset`). After the AST pass, do a regex word-boundary scan
over the raw tactic string for any hypothesis names not yet collected.

**Special cases**: `simp_all`, `simp [*]`, `assumption` and similar implicitly
consume all hypotheses. Detect these by pattern and set U = list(Γ).

---

## Computing πᵢ (dependency_maps)

πᵢ: Γᵢ → P(Γ) maps each hypothesis in the i-th output context to the subset
of input hypotheses it depends on. **πᵢ must be total over Γᵢ.**

Strategy:
1. **Pass-throughs**: h ∈ Γᵢ and h ∈ Γ with matching type → πᵢ(h) = [h].
2. **New hypotheses introduced** (h ∈ Γᵢ \ Γ): scan the type string of h in
   `state_after` for names that appear in Γ; those are its parents. If none
   found, use U as a conservative approximation.
3. Every h ∈ Γᵢ must appear in the map; there must be no missing keys.

---

## Tree Reconstruction

`get_traced_tactics(atomic_only=False)` returns tactics in DFS pre-order from
the AST. The nesting structure comes from `TacticTacticseq1IndentedNode` and
`TacticTacticseqbracketedNode` parents in each tactic's AST ancestry.

Assign integer IDs in the order tactics are yielded (already DFS pre-order).
Reconstruct parent/child relationships by comparing the `pos`/`endPos` spans:
a tactic is a child of the nearest enclosing tactic whose span contains it.

---

## Schema Invariants (must not be violated)

1. **Co-indexing**: `output_obligations[i]`, `child_ids[i]`, and
   `dependency_maps[i]` all refer to the same output branch.
2. **Totality**: every key in `Γᵢ` must appear in `dependency_maps[i]`.
   Pass-throughs map to `[h]`. No missing keys, no extra keys.
3. **DFS pre-order IDs**: `id` values are non-negative integers assigned in
   DFS pre-order; root has the smallest id in its subtree.
4. **Leaf nodes**: `output_obligations = []`, `child_ids = []`,
   `dependency_maps = []` (empty arrays, not null).
5. **Root node**: `parent_id = null`.

---

## Output

One `LeanProofTrace` JSON per Lean source file, validated against
`../schemas/trace.schema.json` before writing. Emit to `data/traces/<repo_name>/`.
