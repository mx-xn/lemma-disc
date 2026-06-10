# Phase 2 — Deferred Work

## Position-level footprint via Lean AST extension to phase 1

**Current**: The POG is built with a **name-level coarsening** of the paper's
tactic footprint Φ(a, Γ, g) = (D, M, µ, ρ). Phase 1 only records hypothesis
names and a name-level dependency map; positions µ and position-level ρ are
unavailable. As a result:

- Every modified proposition is treated as having the single "whole-expression"
  position.
- Two tactics that touch disjoint sub-positions of the same proposition will
  receive a spurious dependency edge.
- Some valid reorderings will be missed by phase 3 (sound, not complete).

**Future plan**: Extend phase 1 (`digestion/src/extractor.py`) to compute
position information directly from the Lean AST:

1. For each `TacticNode`, walk the input expression AST(s) and the output
   AST(s) and identify which sub-positions were rewritten.
2. Augment `TacticSummary` (or add a new `Footprint` field on `TacticNode`)
   with:
   - `modifies: list[{prop: name | "⊢", positions: list[Pos]}]`
   - `rho: list[list[{src: (prop, pos), dst: (prop, pos)}]]` — per output
     branch, the position-level forward map.
3. Update `schemas/trace.schema.json` to add these fields (optional at first,
   so the schema stays backward-compatible while migration happens).
4. Replace `pog/Footprint.scala`'s diff-based recovery with a direct read of
   the position info.
5. Replace `pog/Dependency.scala`'s name-set intersection check with a true
   position-set intersection check at each step.

This will tighten the POG (fewer spurious edges → more reorderings → more
fragment candidates → richer lemma corpus).

**Tracking**: do this as a separate phase 1.5 milestone after the first
end-to-end pipeline run, so we can measure how much completeness is lost to
coarsening before investing in the AST work.
