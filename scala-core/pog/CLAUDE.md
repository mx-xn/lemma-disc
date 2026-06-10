# Phase 2: Proof Ordering Graph (POG) — Implementation Plan

## Context

Phase 2 takes Lean proof traces produced by phase 1 (digestion) and constructs
the **Proof Ordering Graph** `G_T = (V, E)` for each declaration, per paper §2.1.
The POG records the equivalence class of the input proof under reorderings that
preserve dependency constraints; phase 3 will decompose it into proof fragments.

### Inputs (already produced by phase 1)

One JSON file per Lean source file under `data/traces/<repo>/<source>.json`,
conforming to [`schemas/trace.schema.json`](../../schemas/trace.schema.json):

```
{ "source_file": "...",
  "declarations": [
    { "name": "...", "statement": "...", "root_tactic_id": int,
      "tactic_nodes": [ TacticNode, ... ] } ] }
```

Each `TacticNode` already carries:
- `input_obligation` (Γ, g)
- `output_obligations` ((Γ₁,g₁), …, (Γₘ,gₘ))
- `summary.directly_used` = U
- `summary.dependency_maps[i]` = πᵢ (name-level)
- `parent_id` / `child_ids` encoding the tree

No adaptation of phase 1 output is required.

### Outputs

One JSON file per Lean source file under `data/pogs/<repo>/<source>.json`,
conforming to a new schema `schemas/pog.schema.json`:

```
{ "source_file": "...",
  "pogs": [ ProofOrderingGraph, ... ] }
```

Each POG preserves the phase 1 node fields and adds:
- `footprint`: `(D, M_hyps, M_goal, ρ_coarsened)` per node
- `branch_path`: B(a) per node
- `edges`: list of `(from, to, kind)` where `kind ∈ {"modify", "use"}`

---

## Design Decisions

1. **Name-level coarsening.** Phase 1 only records name-level info; positions µ
   and position-level ρ are not available. We treat each modified proposition as
   a single "position". This is *sound* (every POG linearization remains a valid
   proof) but *over-approximates dependencies* — some genuinely independent
   tactic pairs may receive a spurious edge, so some valid reorderings will be
   missed by phase 3. See [`FUTURE.md`](FUTURE.md) for the planned phase 1
   extension to recover position info from the Lean AST.

2. **One file per source file.** Mirrors phase 1 sharding, enables parallel
   phase 3 execution, scales with corpus size.

3. **Preserve phase 1 fields in POG nodes.** Phase 3 (fragment reconstruction)
   needs the obligations; phase 4 (support calculus) needs the summaries. Keeping
   them inline avoids any re-join against the original trace files.

4. **Edge precision per Definition 2.** An edge `aᵢ → aⱼ` is added only when
   there is *no intermediate k* satisfying the same condition relative to `aⱼ`.
   This keeps the POG minimal; transitive dependencies are implied by graph
   reachability.

---

## Key Mathematical Facts (from paper §2.1)

### Tactic Footprint

`Φ(a, Γ, g) = (D, M, µ, ρ)`:
- `D ⊆ Γ`: hypotheses **used but not modified**
- `M ⊆ {g} ∪ Γ`: propositions **modified**
- `µ: M → P(Pos(s))`: positions within each modified proposition *(coarsened: every modified s has the single position "whole")*
- `ρ`: per-branch, maps `(s, p) → (q, p')` propagating positions forward through the tactic *(coarsened to a per-branch name map)*

### Forward propagation along a root-to-leaf path

For tactics `a₁, …, aₙ` on a single path, define
`ρ_{i→i}(s, p) = (s, p)` and
`ρ_{i→j+1}(s, p) = ρ_{j+1}(ρ_{i→j}(s, p))`.

Coarsened version: track just the *name* that `s` propagates to in each
successor obligation along the path.

### Dependency `aᵢ ≺ aⱼ` (Definition 2)

Holds when `aⱼ` is downstream of `aᵢ` on a root-to-leaf path and either:

1. **Modification dependence**: `∃ s ∈ Mᵢ` such that the propagation
   `ρ_{i→j}(s, _)` lands on some `q ∈ Mⱼ` (coarsened: both modify the same
   propagated name), and **no intermediate k** with `i < k < j` does so first.
2. **Use dependence**: `∃ s ∈ Mᵢ` such that `ρ_{i→j}(s, _)` lands on some
   `q ∈ Dⱼ`, with the same "no intermediate k" condition.

### Branch path `B(a)`

The sequence of branch indices chosen at branching ancestors of `a`, with `*`
suffix if `a` is itself branching (i.e., produces more than one residual
obligation).

---

## Recovering the Footprint from Phase 1 Data

Per `TacticNode` with input `(Γ, g)`, outputs `((Γ₁,g₁), …, (Γₘ,gₘ))`,
`directly_used = U`, `dependency_maps[i] = πᵢ`:

| Footprint field | Recovery rule |
|----------------|---------------|
| `M_hyps`       | `{h ∈ Γ \| ∃i. h ∉ names(Γᵢ) ∨ prop_Γ(h) ≠ prop_Γᵢ(h)}` |
| `M_goal`       | `∃i. g ≠ gᵢ` (boolean) |
| `D`            | `U \ M_hyps` |
| `ρᵢ` (names)   | `πᵢ` plus an implicit goal entry `g ↦ gᵢ` if `M_goal` |

In the schema, the `Hypothesis.type` field holds the Lean expression string of
the hypothesis's *proposition* (in Lean, a hypothesis `h : p` has "type" `p`).
So `prop_Γ(h)` above is just `hyp.type` read out of phase 1's JSON; a
"proposition change" is the string inequality of this field.

Cases to handle carefully:
- **Leaf** (`outputs = []`): `M = ∅`, `D = U`, no `ρ`.
- **Identity-rename pattern**: if `h` appears in both Γ and Γᵢ with the same
  type but a different name in Γᵢ, the existing πᵢ map captures it as the
  parent dependency; we treat the renamed name as ∈ M *if* its name doesn't
  appear in Γ. (Phase 1 doesn't currently distinguish renames from new
  introductions — fall back to: any name in Γᵢ that's not in Γ is "introduced",
  hence modifies the context.)

---

## Files to Create / Fill

| File | Role |
|------|------|
| `schemas/pog.schema.json` | Inter-phase schema: phase 2 → phase 3 |
| `scala-core/pog/src/main/scala/Types.scala` | ADTs for trace input + POG output |
| `scala-core/pog/src/main/scala/Parser.scala` | trace.schema.json JSON → ADT (upickle) |
| `scala-core/pog/src/main/scala/Footprint.scala` | Compute `(D, M_hyps, M_goal, ρ)` per node |
| `scala-core/pog/src/main/scala/BranchPath.scala` | Compute `B(a)` per node |
| `scala-core/pog/src/main/scala/Dependency.scala` | Pairwise `≺` with forward propagation + "no intermediate k" |
| `scala-core/pog/src/main/scala/Builder.scala` | Assemble per-declaration POG |
| `scala-core/pog/src/main/scala/Serializer.scala` | POG → JSON + `main` entry point |
| `scala-core/pog/src/test/scala/FootprintTest.scala` | Hand-built `TacticNode` → footprint |
| `scala-core/pog/src/test/scala/BranchPathTest.scala` | Hand-built tree → branch path |
| `scala-core/pog/src/test/scala/DependencyTest.scala` | Hand-built footprint sequence → edges |
| `scala-core/pog/src/test/scala/BuilderTest.scala` | Small end-to-end POG construction |
| `scala-core/build.sbt` (edit) | Add scalatest dependency to `pog` subproject |

---

## Step 1 — `schemas/pog.schema.json`

Top-level: `{ source_file, pogs[] }`.

`ProofOrderingGraph`:
```
{ "decl_name": "...",
  "statement": "...",
  "root_tactic_id": int,
  "root_obligation": Obligation,
  "nodes": [ PogNode, ... ],
  "edges": [ PogEdge, ... ] }
```

`PogNode` (extends the phase 1 `TacticNode` shape):
```
{ "id": int,
  "tactic_text": "...",
  "input_obligation": Obligation,
  "output_obligations": [Obligation, ...],
  "summary": { "directly_used": [...], "dependency_maps": [...] },
  "parent_id": int | null,
  "child_ids": [int, ...],
  "footprint": {
    "uses": [string, ...],             // D
    "modifies_hyps": [string, ...],    // M_hyps (names)
    "modifies_goal": bool,             // M_goal
    "rho": [                           // one entry per output branch
      { "<parent name or '⊢'>": ["<child name or '⊢'>", ...] }, ... ] },
  "branch_path": [string, ...]         // e.g. ["1", "0*"] or ["*"]
}
```

`PogEdge`:
```
{ "from": int, "to": int, "kind": "modify" | "use" }
```

Reuse `Obligation`, `Hypothesis`, `TacticSummary` definitions verbatim from
`trace.schema.json` (copy them in; do not `$ref` across files — schema lives
standalone).

---

## Step 2 — `Types.scala`

```scala
// Phase 1 mirror (parse target)
case class Hypothesis(name: String, `type`: String)
case class Obligation(hypotheses: List[Hypothesis], goal: String)
case class TacticSummary(directlyUsed: List[String], dependencyMaps: List[Map[String, List[String]]])
case class TacticNode(id: Int, tacticText: String, inputObligation: Obligation,
                      outputObligations: List[Obligation], summary: TacticSummary,
                      parentId: Option[Int], childIds: List[Int])
case class Declaration(name: String, statement: String, rootTacticId: Int,
                       tacticNodes: List[TacticNode])
case class LeanProofTrace(sourceFile: String, declarations: List[Declaration])

// POG-specific
case class Footprint(uses: Set[String], modifiesHyps: Set[String], modifiesGoal: Boolean,
                     rho: List[Map[String, Set[String]]])  // co-indexed with output branches
//   key/value in rho can be a hypothesis name; the literal "⊢" denotes the goal slot
case class BranchPath(segments: List[String])               // e.g. List("1", "0*")
sealed trait EdgeKind
case object ModifyEdge extends EdgeKind
case object UseEdge extends EdgeKind
case class PogEdge(from: Int, to: Int, kind: EdgeKind)
case class PogNode(node: TacticNode, footprint: Footprint, branchPath: BranchPath)
case class ProofOrderingGraph(declName: String, statement: String, rootTacticId: Int,
                              rootObligation: Obligation, nodes: List[PogNode],
                              edges: List[PogEdge])
case class PogFile(sourceFile: String, pogs: List[ProofOrderingGraph])
```

Use `@upickle.implicits.key("type")` for the Scala-reserved field name on
`Hypothesis`. Define `ReadWriter` instances at the bottom of the file.

---

## Step 3 — `Parser.scala`

```scala
object Parser {
  def parseFile(path: os.Path): LeanProofTrace = upickle.default.read[LeanProofTrace](path.toIO)
}
```

Two-line module; round-trip-tested by reading `Examples.json` and checking
declaration count + a few representative node fields.

---

## Step 4 — `Footprint.scala`

```scala
object Footprint {
  def compute(node: TacticNode): Footprint = {
    val Γ        = node.inputObligation.hypotheses
    val g        = node.inputObligation.goal
    val ΓNames   = Γ.map(_.name).toSet
    val ΓTypeMap = Γ.iterator.map(h => h.name -> h.`type`).toMap

    val (modifiesHyps, modifiesGoal) =
      node.outputObligations.foldLeft((Set.empty[String], false)) {
        case ((mh, mg), Obligation(hyps, gi)) =>
          val outMap = hyps.iterator.map(h => h.name -> h.`type`).toMap
          val modHere = ΓNames.filter { n =>
            !outMap.contains(n) || outMap(n) != ΓTypeMap(n)
          }
          (mh ++ modHere, mg || gi != g)
      }

    val U    = node.summary.directlyUsed.toSet
    val D    = U -- modifiesHyps
    val rho  = node.summary.dependencyMaps.map { πᵢ =>
      val withGoal = if (modifiesGoal) πᵢ.updated("⊢", List("⊢")) else πᵢ
      withGoal.view.mapValues(_.toSet).toMap
    }

    Footprint(uses = D, modifiesHyps = modifiesHyps, modifiesGoal = modifiesGoal, rho = rho)
  }
}
```

The literal `"⊢"` key is reserved for the goal slot inside `ρ`.

---

## Step 5 — `BranchPath.scala`

```scala
object BranchPath {
  def compute(nodes: List[TacticNode]): Map[Int, BranchPath] = {
    val byId = nodes.iterator.map(n => n.id -> n).toMap
    def isBranching(n: TacticNode) = n.outputObligations.size > 1

    def loop(id: Int, acc: List[String]): BranchPath = {
      val n = byId(id)
      val tail = if (isBranching(n)) List("*") else Nil
      BranchPath(acc.reverse ++ tail)
    }

    // Walk parent chain, recording the child index at each branching ancestor.
    nodes.map { n =>
      val prefix = collection.mutable.ListBuffer.empty[String]
      var cur    = n
      while (cur.parentId.isDefined) {
        val parent = byId(cur.parentId.get)
        if (isBranching(parent)) {
          val idx = parent.childIds.indexOf(cur.id)
          prefix.prepend(idx.toString)
        }
        cur = parent
      }
      val selfMark = if (isBranching(n)) List("*") else Nil
      n.id -> BranchPath(prefix.toList ++ selfMark)
    }.toMap
  }
}
```

`*` is appended only when the node itself is branching, even if zero ancestors
were branching. Linear chain nodes get an empty path `List()`.

---

## Step 6 — `Dependency.scala`

This is the most subtle component. Algorithm:

1. **Enumerate root-to-leaf paths** in the tree. Each path is a sequence
   `[a₁, …, aₙ]` of node IDs.
2. **For each path**, compute the cumulative forward-propagation map:
   `forward(i)` = a function that, given a name `s` in `Γ` ∪ {⊢}, returns the
   set of names it has propagated to by index `i`. Computed by composing the
   `ρ`'s of the chosen branch at each step.
3. **For each ordered pair `(i, j)` on the path with `i < j`**, check the two
   conditions:
   - *Modify-dep*: `∃ s ∈ Mᵢ. forward(i→j)(s) ∩ Mⱼ ≠ ∅`
   - *Use-dep*: `∃ s ∈ Mᵢ. forward(i→j)(s) ∩ Dⱼ ≠ ∅`
4. **"No intermediate k"**: for each `j`, scan `i` from `j-1` down to root. Once
   a witnessing `s` shows the condition at index `i`, record `(i,j)` and mark
   that witness as "claimed" so earlier `i'` cannot also claim it.
   - Concretely: maintain a set `claimedFor(j)` of names already explained;
     skip `s` if `forward(i→j)(s)` only intersects `Mⱼ`/`Dⱼ` via already-claimed
     names.
5. **Deduplicate across paths**: an edge `(i, j)` may be discovered along
   multiple paths through a common ancestor; keep distinct `(from, to, kind)`
   tuples.

Edge kind: if both conditions hold for the same `(i, j)`, emit two edges (one
per kind) — they are semantically distinct constraints.

This routine is O(P × N²) where P is the number of paths and N is the path
length. For our corpus sizes (proof trees of ≤ 50 nodes) this is fine.

---

## Step 7 — `Builder.scala`

```scala
object Builder {
  def build(decl: Declaration): ProofOrderingGraph = {
    val footprints  = decl.tacticNodes.iterator.map(n => n.id -> Footprint.compute(n)).toMap
    val branchPaths = BranchPath.compute(decl.tacticNodes)
    val edges       = Dependency.compute(decl.tacticNodes, footprints)
    val pogNodes    = decl.tacticNodes.map(n => PogNode(n, footprints(n.id), branchPaths(n.id)))
    val rootObl     = decl.tacticNodes.find(_.id == decl.rootTacticId).get.inputObligation
    ProofOrderingGraph(decl.name, decl.statement, decl.rootTacticId, rootObl, pogNodes, edges)
  }

  def buildFile(trace: LeanProofTrace): PogFile =
    PogFile(trace.sourceFile, trace.declarations.map(build))
}
```

---

## Step 8 — `Serializer.scala`

- `writeFile(pf: PogFile, path: os.Path): Unit` — upickle write + schema
  validation (best-effort; fall back to raw write if no schema validator).
- `main(args: Array[String])`:
  ```
  Usage: pog <input-trace.json> <output-pog.json>
       | pog <input-dir>          <output-dir>      // batch mode
  ```
  Batch mode iterates `*.json` in the input dir.

---

## Step 9 — Tests

### `FootprintTest.scala`

| Scenario | Expected |
|----------|----------|
| Leaf `exact h` with `U={h}`, no outputs | `D={h}, M_hyps=∅, M_goal=false, ρ=[]` |
| `intro h` (introduces `h` into output) | `M_hyps={...}`, goal unchanged → `M_goal=false` |
| `simp` rewriting the goal, no hyp change | `M_hyps=∅, M_goal=true` |
| `induction xs` with two branches, drops `xs`, adds new hyps | `M_hyps ⊇ {xs}` |

### `BranchPathTest.scala`

| Tree shape | Expected paths |
|------------|----------------|
| Single linear chain a→b→c | `a: [], b: [], c: []` |
| Branching root with two leaves a→{b, c} | `a: ["*"], b: ["0"], c: ["1"]` |
| Two-level branching a→{b→{d, e}, c}, b also branches | `a: ["*"], b: ["0*"], c: ["1"], d: ["0","0"], e: ["0","1"]` |

### `DependencyTest.scala`

Hand-build linear chains with known footprints; verify:
- Two non-overlapping tactics → no edge
- `a₁` modifies `h`, `a₂` uses `h` → use-edge `(1,2)`
- `a₁` modifies `h`, `a₂` modifies `h` again, `a₃` uses `h` → use-edge `(2,3)` only (the intermediate `a₂` cancels `(1,3)`)
- Goal threading: `a₁` modifies goal, `a₃` uses propagated goal via ρ → edge `(1,3)`

### `BuilderTest.scala`

Build one small POG end-to-end (e.g. a 3-node linear `intro h; rw h; rfl`),
assert the edge set exactly.

### Integration test

`Builder.buildFile(Parser.parseFile(path("data/traces/MiniCodePropsLeanSrc/Examples.json")))`
must succeed and produce a non-empty POG for each declaration.

---

## Logical Build Order

1. `schemas/pog.schema.json` — defines the wire contract first.
2. Edit `scala-core/build.sbt` — add scalatest to `pog` subproject.
3. `Types.scala` — unblocks everything else.
4. `Parser.scala` + round-trip read of `Examples.json`.
5. `Footprint.scala` + `FootprintTest.scala`.
6. `BranchPath.scala` + `BranchPathTest.scala`.
7. `Dependency.scala` + `DependencyTest.scala` (most tricky; build incrementally).
8. `Builder.scala` + `BuilderTest.scala`.
9. `Serializer.scala` + integration smoke test against `Examples.json`.

---

## Verification

```bash
cd /nas/lemma-disc/scala-core
sbt "pog/test"                                  # unit tests pass
sbt "pog/run data/traces/MiniCodePropsLeanSrc/Examples.json data/pogs/Examples.json"
jq '.pogs | length' data/pogs/Examples.json     # one POG per declaration
jq '.pogs[0].edges | length' data/pogs/Examples.json  # at least one edge for a non-trivial proof
```

---

## Out of Scope (Phase 3+ responsibilities)

- POG decomposition `(H_pre, H, H_post)` — phase 3.
- Linearization and obligation reconstruction — phase 3.
- Support calculus / Lem(·) — phase 4.
