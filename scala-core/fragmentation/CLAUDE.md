# Phase 3: Fragment Construction — Implementation Plan

## What phase 3 does

**Input:** a POG (phase 2, [`pog.schema.json`](../../schemas/pog.schema.json)).
**Output:** a list of obligation-annotated proof fragments
([`segments.schema.json`](../../schemas/segments.schema.json)), consumed by phase 4.

A *fragment* is a connected piece of a proof, rooted at an obligation `(Γ_F, g_F)`, with zero
or more **holes** marking where the selected piece stops and the original proof continues. Each
fragment becomes one candidate lemma downstream.

Two sub-phases (paper §2.2):

- **Phase A — Decomposition (§2.3):** choose which tactics form the fragment (`V_H`), which must
  run before it (`V_pre`), and which are left over (`V_post`).
- **Phase B — Reconstruction (§2.3.1):** compute the obligation at the fragment's root and at
  every node/hole inside it, by replaying tactic effects.

---

## The one idea to hold onto: two structures over the same nodes

The tactic nodes carry **two** structures:

| structure | what it is | what it gives us |
|-----------|------------|------------------|
| **proof tree `T`** | original parent/child shape (phase 1) | the *tree shape* of any set of nodes |
| **dependency graph `G_T`** (the POG) | edges `a ≺ b` = "`b` depends on `a`" | which decompositions are *legal* |

Phase A's admissibility is stated over `G_T`. Two facts relate the two structures:

1. **`G_T` is strictly sparser than `T`'s order.** Every edge connects a `T`-ancestor to a
   `T`-descendant (Def 2 only relates tactics on a common root-to-leaf path), i.e.
   `E ⊆ ancestor/descendant order` — but **not** conversely, and `E` is not transitively closed.
   Example: in a chain `A;B;C` where `C` depends on `A` but not on `B`, the edges are `(A,B)` and
   `(A,C)` — `(B,C)` is a tree-ancestor pair that is *not* an edge. So a tactic can be reordered
   past tree-intermediates it does not depend on.
2. **Original proof order, restricted to any `V_H`, is a valid linearization** of the induced
   subgraph (it respects every in-`V_H` edge, since the whole proof respects all of `E`). This is
   what lets us fix *one* canonical linearization per `V_H` — Theorem 1 makes the choice
   lemma-irrelevant.

Therefore **admissible `V_H` are convex + branch-closed vertex subsets of `G_T`, enumerated on the
graph** — *not* contiguous subtrees of `T`. The sets that are convex in `G_T` but not contiguous in
`T` are exactly the **reordered fragments** (e.g. `{A,C}` above, skipping the independent `B`):
`C` is re-parented under `A` and its obligation is reconstructed because `B` never ran. Capturing
these is the entire reason to build a POG rather than just chop up the proof tree — a
tree-subtree-only enumeration would be sound but would miss precisely them.

---

## What each vertex set is for

- **`V_H`** — the fragment's tactics: a **convex + branch-closed vertex subset of `G_T`**.
- **`V_pre`** — the tactics that must run *before* the fragment for it to replay. A node is
  included either because **H directly depends on it** (§2.3 cond. 3 — it produces something H
  uses/modifies) **or** because **another `V_pre` node depends on it** (§2.3 cond. 4 — so the
  pre-set can itself replay; such a node need not produce anything H consumes). So `V_pre` is the
  dependency-*ancestor* closure of H within `V\H`. 
- **`V_post`** — everything else (`V \ (V_H ∪ V_pre)`): nodes H does *not* depend on.

**Why this is more than the stub.** Obligations follow *dependencies, not tree position*, so the
fragment's reconstructed obligations differ from the recorded run in ways the stub (which copies
recorded obligations) cannot reproduce:
1. **Reordered fragments** — `V_H` may skip tree-intermediates it doesn't depend on (the `{A,C}`
   case), re-parenting the fragment tree relative to `T`.
2. **Reordered pre-set** — `V_pre` is a *dependency closure*, not an ancestor prefix. It drops
   tree-ancestors H doesn't need, **and** may pull in nodes elsewhere on the path — even tree-
   *descendants* of the fragment root — that H does need, reordered to run before it. (Path
   `root→r→p→h` with `r,h ∈ H`, `h` depending on `p` but not `r`: then `p ∈ V_pre` runs before the
   fragment root `r`, though it sits below `r` in the tree.) So `(Γ_F, g_F)` is in general neither
   the recorded obligation at the root nor a truncation of it.

Either way the recorded obligations are invalid for the fragment, which is why Phase B
reconstructs them.

---

## Phase B: obligation reconstruction

**Purpose:** label every node of the fragment with the obligation its tactic runs at. We cannot
read these off the recorded run — dropping incidental ancestors changes the obligations — so we
*recompute* them by replaying tactic effects along the original order.

Two computations:

1. Replay **`H_pre`** from the proof's root obligation → the fragment's **input** obligation
   `(Γ_F, g_F)` (the obligation entering the fragment root).
2. Replay **`H`** from `(Γ_F, g_F)` → the obligation at **every internal node** *and* at **every
   hole** (the open goals leaving the fragment).

So both ends are produced: H_pre's output is the goal *entering* the fragment; H's outputs are the
goals *leaving* it at the holes — plus every obligation in between, which phase 4 consumes.

**Tactic effects — how much care is needed now.** A node's *effect* on a branch is the diff
between its recorded input and output obligation: hyps removed (`Clear`), hyps added (`Introduce`),
goal or hyp-type changed (`Modify`). `Apply` replays a diff onto an obligation. Under phase-2's
name-level coarsening this is *literal* replacement — no template/position machinery (the paper's
`µ, ρ, σ` collapse).

### `Action` ADT (coarsened Def 4/6)

```
Clear(name)             — remove hypothesis `name` from Γ
Introduce(hyp)          — append hypothesis `hyp` to Γ
Modify(prop, old, snew) — change proposition identified by `prop` from `old` to `snew`:
                            prop = "⊢"        → replace goal  (verify old == current goal)
                            prop = hyp name   → replace that hypothesis's type in-place
                                               (verify old == current type)
```

`prop = "⊢"` follows the same convention as the POG module's `ρ` maps. `old` serves as a
fail-fast pre-condition: if the current value does not equal `old`, `Apply` throws.

**Derivation order** (within `Effects.derive`): `Clear`s (input order) → `Modify`s for type
changes (input order) → `Introduce`s (output order) → `Modify` for goal (if changed). This
ordering ensures each `Modify`'s `old` value is unambiguous at the time of application —
e.g., a cleared hypothesis's type cannot be accidentally matched by a later type-change Modify.

**Future work:** the paper's `Modify(p, Sold, Snew)` uses *templates* (`□i` holes + substitution
σ) so effects compose correctly when applied to structurally similar but textually distinct
obligations (e.g. across proof reorderings). The coarsened literal model is sound here because
dependency closure guarantees the same propositions are always present, but a template-based
`Sold`/`Snew` would recover completeness. See `pog/FUTURE.md` for the analogous position-level
coarsening note.

- **Pin down now:** the `Action` ADT and `Apply`'s semantics — they are load-bearing for Phase B.
  The intended invariant: literal replay is sound because **dependency closure guarantees every
  proposition a kept node references is still present** (a skipped node is, by admissibility, never
  referenced by a kept node).
- **Defer / tune against `Examples.json`:** derivation edge cases (rename vs. fresh intro,
  multi-branch splits). Any residual coarsening imprecision is caught downstream by phase 5's Lean
  validation, so it cannot produce a silently-wrong lemma.

---

## Enumeration heuristic

**Purpose:** only extract fragment *shapes* that make clean, reusable lemmas. A fragment with holes
encodes "goal A reduces to goals B₁…Bₖ". If it *also* branches, `Lem(Υ)` becomes nested
conjunctions of implications with dangling holes — low reuse value. So:

1. **Chain** (a single root-to-leaf/hole path): allowed, with or without holes.
2. **Branching tree** (some tactic splits into ≥2 subgoals): allowed only if fully closed to original
   leaves (**no holes**).

i.e. **any fragment with a hole must be a chain.**

The rule is one predicate on the candidate `V_H`, computable structurally with **no obligations and
no POG edges** — only `mₙ`, the number of output obligations (subgoals) tactic `n` produces,
recorded in the trace.

> **`mₙ` is the subgoal count, not the POG out-degree.** A linear `intro h` produces one subgoal
> (`mₙ = 1`) yet may have many dependency edges (every later tactic that uses `h`). "Branching" is a
> proof-tree fact (`mₙ ≥ 2`, e.g. `induction`/`cases`); POG edges are used only for admissibility,
> never here.

In the fragment tree, node `n` has exactly `mₙ` children — each subgoal is one slot, filled by a
sub-proof in `V_H` or left as a hole. Admissible `V_H` has a single fragment root, so its non-root
nodes fill exactly `|V_H| − 1` slots; every remaining slot is a hole:

```
mₙ            = #output obligations of n        (subgoal count from the trace, NOT POG out-degree)

branches(V_H) = ∃ n ∈ V_H.  mₙ ≥ 2              -- some tactic splits the goal into ≥2 subgoals
holeCount     = (Σ_{n∈V_H} mₙ) − (|V_H| − 1)    -- subgoal slots minus the |V_H|−1 filled by H-nodes
hasHole(V_H)  = holeCount > 0
accept(V_H)   = !branches(V_H) || !hasHole(V_H)
```

`!branches(V_H)` *is* "the fragment is a chain". The only rejected shape is branching-with-a-hole:

| shape | node `mₙ`s | `Σmₙ` | holes | branches | accept |
|-------|-----------|-------|-------|----------|--------|
| chain → leaf            | 1, 1, 0 | 2 | 0 | no  | ✅ |
| chain → hole            | 1, 1, 1 | 3 | 1 | no  | ✅ |
| branch, closed to leaves| 2, 0, 0 | 2 | 0 | yes | ✅ |
| branch + dangling hole  | 2, 0    | 2 | 1 | yes | ❌ |

**Modularity + timeout.** `accept` is one value of type `Candidate => Boolean`: pass `_ => true` to
disable it, or swap in another rule. It is applied **during** enumeration, as a filter on the lazy
candidate stream, *before* Phase B runs — so the wall-clock `timeoutMs` budget reconstructs only
accepted candidates. The predicate is purely structural (needs no obligations), so filtering early
is free. Enumeration returns the accepted decompositions plus an `EnumerationReport`
(`examined` / `accepted` / `skipped` / `timedOut`), logged so a capped run is never mistaken for a
complete one.

---

## Phase 3 → Phase 4 contract (already live)

Phase 4 ([`scala-core/support/`](../support/CLAUDE.md)) is **already implemented** and reads
`segments.schema.json` directly: its `Serializer` parses `fragments[]`, rebuilds a `PartialTree`
from the flat node list (dispatch on `kind`), then runs the support calculus + `Lem(·)`. Phase 3
must emit exactly this shape. The build order ends with a **phase3→4 pipeline test** that feeds
phase 3 output straight into phase 4 and asserts lemmas come out.

---

## Files to create / fill (`fragmentation/src/main/scala/`)

The subproject exists in [`build.sbt`](../build.sbt) with `.dependsOn(pog)`; the three existing
files are empty stubs. **POG input ADTs are reused from the `pog` module** (default package, on the
classpath) — we do not redefine `ProofOrderingGraph` / `PogNode` / `Footprint` / `Obligation`.

| File | Role | Paper |
|------|------|-------|
| `build.sbt` (edit) | add scalatest to `fragmentation` | — |
| `Types.scala` | `Decomposition(vH, vPre, vPost)`; `Candidate`; `EnumerationReport`; effect ADTs (`Action = Modify \| Introduce \| Clear`, `Effect`); output ADTs (`Fragment`, `TreeNode = HoleNode \| LeafNode \| CompositeNode`, `FragmentList`) + segments ReadWriters | §2.3, §2.3.1, §1 |
| `PogParser.scala` | `read[PogFile]` wrapper (reuses `pog` ReadWriters) | — |
| `Decomposer.scala` (Phase A) | enumerate convex + branch-closed `V_H` over `G_T` (lazy iterator); `vPre` (dependency closure) + `vPost`; admissibility predicates; `EnumerationHeuristic` + validity predicate; `enumerate(pog, heuristic, timeoutMs)` | §2.3 |
| `Effects.scala` | derive `Effect` from a node's recorded diff; `Apply(action, Γ, g)` (Def 6); `deriveAll(node)` is the primary API (returns `List[Effect]`, one per output branch; empty for leaves) | §2.3.1, Def 4–6 |
| `Linearizer.scala` | original proof order restricted to a vertex set | §2.3.1 |
| `Reconstructor.scala` (Phase B) | replay `H_pre` → `(Γ_F,g_F)`; replay `H` → per-node + per-hole obligations; derive fragment tree structure (parent/child + hole placement) from the linearization | §2.3.1 |
| `FragmentBuilder.scala` | annotated tree → output `Fragment` ADTs + IDs. Tree comes from the linearization (re-parented relative to `T`), holes at residuals not continued in `V_H`, leaves at H-nodes with no residuals | — |
| `Serializer.scala` | `FragmentList` → segments.schema.json JSON; `main` (single-file + batch-dir, mirroring `pog`) | — |

Tests mirror the `pog` module (hand-built first, integration last): `DecomposerTest`,
`EffectsTest`, `LinearizerTest`, `ReconstructorTest`, `FragmentBuilderTest`, `SerializerTest`.

---

## Build order

1. **`build.sbt`** — add scalatest to `fragmentation`.
2. **`Types.scala`** — ADTs + segments ReadWriters. Unblocks everything.
3. **`PogParser.scala`** + round-trip test on [`data/pogs/Examples.json`](../../data/pogs/Examples.json).
4. **`Decomposer.scala` + `DecomposerTest`** (Phase A core — *no obligations yet*). Test:
   admissibility predicates on hand-built POGs (incl. a reordered `{A,C}`-style set that is convex
   in `G_T` but not a `T`-subtree); the heuristic on chain / branch / chain-with-hole /
   branch-with-hole shapes; `vPre` closure; timeout + report on `Examples.json`.
5. **`Effects.scala` + `EffectsTest`** — derive + `Apply` on hand-built nodes (intro / rewrite /
   induction-split / leaf).
6. **`Linearizer.scala` + `LinearizerTest`** — original-order restriction on small graphs.
7. **`Reconstructor.scala` + `ReconstructorTest`** (Phase B; needs 5+6). Key cases: dropping an
   incidental post-ancestor changes `(Γ_F,g_F)`; goal threading through `V_pre` is preserved; hole
   obligations equal recorded residuals when no reordering occurred.
8. **`FragmentBuilder.scala` + `FragmentBuilderTest`** — end-to-end on one small POG; assert exact
   hole/leaf/composite structure and obligations.
9. **`Serializer.scala`** + integration on `Examples.json`; validate output against
   [`segments.schema.json`](../../schemas/segments.schema.json).
10. **Phase3→4 pipeline test** — run `fragmentation/run` then `support/run` on the result; assert
    a non-empty, well-formed lemmas JSON (the boundary actually holds end-to-end).

---

## Verification

```bash
cd /nas/lemma-disc/scala-core
sbt "fragmentation/test"
sbt "fragmentation/run ../data/pogs/Examples.json ../data/segments/Examples.json"
sbt "support/run ../data/segments/Examples.json ../data/lemmas/Examples.json"   # phase3→4
jq '.fragments | length' ../data/segments/Examples.json
# no branching fragment may contain a hole:
jq '[.fragments[] | select([.nodes[]|select(.kind=="hole")]|length > 0)
     | ([.nodes[]|select(.kind=="node" and (.child_ids|length>1))]|length)] | add // 0' \
   ../data/segments/Examples.json   # must be 0
```

---

## Out of scope (later)

- Phase 5 (Lean emission + validation).
- Non-minimal `V_pre`; multiple linearizations per decomposition; non-coarsened
  (position/template-level) effects.
