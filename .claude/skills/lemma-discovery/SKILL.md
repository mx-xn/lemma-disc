---
name: lemma-discovery
description: Lemma discovery pipeline implementation. Multi-phase system (Python + Scala) that extracts reusable lemmas from Lean 4 proof corpora via proof ordering graph decomposition and support minimization. Read this before start working on any phase.
---

## Phases of Lemma Discovery Procedure
phase1: Digestion             [Python: extract proof traces from Lean scripts via LSP]
phase2: POG construction      [Scala: build proof ordering graph from traces]
phase3: Fragment construction [Scala: POG decomposition + obligation reconstruction]
phase4: Support minimization  [Scala: support calculus + Lem(·) construction]
phase5: Lemma Emission        [Python: emit Lean lemma code + validate via Lean server]


## Module → Paper Section Map

Before implementing any module, read `./docs/formalization.pdf` for the relevant sections, then read the module's own `CLAUDE.md`.

| Module | Paper Sections | Input | Output |
|--------|---------------|-------|--------|
| phase1 | §1 (obligations, proof trees) | Lean source files | Lean trace (JSON) |
| phase2 | §2.1 (footprint, dependency, POG) | Lean trace | POG (JSON) |
| phase3 | §2.3, §2.3.1 (decomposition, tactic effects, obligation reconstruction) | POG | Proof segments (JSON) |
| phase4 | §3.1 (tactic summary, support calculus), §1 Lem(·) | Proof segments | Lemma objects (JSON) |
| phase5 | — | Lemma objects | Lean source code |

## Coding Principles

### Scala (phases 2–4)
- Algebraic data types for all tree/graph grammars — never raw maps or untyped JSON internally
- Parse JSON into typed ADTs at module boundary between phase1 and phase2; serialize back to JSON at output between phase4 and phase5
- One source file per major definition or data type
- Tests on small hand-built examples before any integration

### Python (phases 1, 5)
- Type hints on all function signatures
- Dataclasses for structured data; no raw dicts past the JSON parsing layer
- Keep Lean LSP interaction isolated behind a clean interface

## Inter-Phase Data Flow

Phases communicate via JSON files. Schemas live in `schemas/`. Scala parses JSON → ADTs at entry, serializes ADTs → JSON at exit. Python does the same with dataclasses.

When adding a new inter-phase schema, define it in `schemas/` first, then implement parsers on both sides.