# Phase 4: Support Minimization — Implementation Plan

## Context

Phase 4 takes proof segments (obligation-annotated partial proof trees + tactic summaries)
produced by phase 3 and emits lemma objects for phase 5 (Lean emission). It implements
two mathematical components from the paper:

1. **Support calculus** (§3.1, Figure 1) — backward analysis that computes the
   inclusion-minimal set of hypotheses A ⊆ ΓF needed to replay a proof fragment.
2. **Lem(·) construction** (§1) — recursive formula that turns a partial proof tree
   into a Lean proposition.

The final lemma for a fragment is: `(∧A) ∧ Lem(Υ) → gF`.

All support Scala files are currently empty stubs. No inter-phase schema exists yet
for the phase3→4 boundary (`segments.schema.json`). The `lemmas.schema.json` is also empty.

---

## Key Mathematical Facts (from paper)

### Support Calculus — Figure 1

```
Γ; g ⊢ •ℓ[(Γℓ,gℓ)] : ∅                                         (Supp-Hole)

Σ(a,Γ,g) = (U),  JaK(Γ,g) = ∅
──────────────────────────────────                               (Supp-Leaf)
        Γ; g ⊢ a : U

Σ(a,Γ,g) = (U, π₁,...,πₘ),  JaK(Γ,g) = {(Γ₁,g₁),...,(Γₘ,gₘ)}
∀i.  Γᵢ; gᵢ ⊢ P̂ᵢ : Aᵢ
──────────────────────────────────────────────────────────────── (Supp-Comp)
   Γ; g ⊢ a⟨P̂₁,...,P̂ₘ⟩ : U ∪ ⋃ᵢ ⋃_{h∈Aᵢ} πᵢ(h)
```

`Σ(a,Γ,g) = (U, π₁,...,πₘ)` is already stored in each tactic node's `summary`
field from phase 1: `directly_used = U`, `dependency_maps[i] = πᵢ`.

### Lem(·) Recursion — §1

```
Lem(•ℓ[(Γℓ,gℓ)])            = gℓ
Lem(a[(Γ,g)])               = ⊤          (leaf with no children)
Lem(a[(Γ,g)]⟨Υ₁,...,Υₘ⟩)  = ∧_{i: Lem(Υᵢ)≠⊤} ((∧(Γᵢ\Γ)) → Lem(Υᵢ))
                              ⊤ if all children yield ⊤
```

When `Γᵢ \ Γ = ∅`, the implication simplifies to `Lem(Υᵢ)`.

---

## Files to Create / Fill

| File | Role |
|------|------|
| `schemas/segments.schema.json` | Inter-phase schema: phase3 → phase4 |
| `schemas/lemmas.schema.json` | Inter-phase schema: phase4 → phase5 |
| `scala-core/build.sbt` | Scala build: three subprojects (`pog`, `fragmentation`, `support`) |
| `scala-core/support/src/main/scala/Types.scala` | ADTs for all concepts |
| `scala-core/support/src/main/scala/SupportCalc.scala` | Support calculus (Figure 1) |
| `scala-core/support/src/main/scala/LemmaConstructor.scala` | Lem(·) + lemma assembly |
| `scala-core/support/src/main/scala/Serializer.scala` | JSON↔ADT + `main` entry point |
| `scala-core/support/src/test/scala/SupportCalcTest.scala` | Unit tests |
| `scala-core/support/src/test/scala/LemmaConstructorTest.scala` | Unit tests |

---

## Step 1 — `schemas/segments.schema.json`

Inter-phase format produced by phase 3, consumed by phase 4. A flat list of fragment
candidates with provenance metadata. Each fragment stores its proof tree as a flat node
list (same pattern as `trace.schema.json`) to avoid deep nesting.

Top-level object: `{ "fragments": [...] }`  
Fragment: `{ fragment_id, source_file, decl_name, root_node_id, root_obligation, nodes[] }`  
Tree nodes (flat list, discriminated by `"kind"`, each with `id`, `parent_id`, `child_ids`):

```json
// Hole
{ "id": 0, "kind": "hole", "hole_id": "ℓ1",
  "parent_id": null, "child_ids": [],
  "obligation": { "hypotheses": [...], "goal": "..." } }

// Leaf (tactic proved its goal immediately)
{ "id": 1, "kind": "leaf", "tactic_text": "...",
  "parent_id": 0, "child_ids": [],
  "obligation": { "hypotheses": [...], "goal": "..." },
  "summary": { "directly_used": ["h1"], "dependency_maps": [] } }

// Composite tactic
{ "id": 2, "kind": "node", "tactic_text": "...",
  "parent_id": null, "child_ids": [3, 4],
  "obligation": { "hypotheses": [...], "goal": "..." },
  "output_obligations": [{ "hypotheses": [...], "goal": "..." }, ...],
  "summary": { "directly_used": [...], "dependency_maps": [{...}, ...] } }
```

`output_obligations[i]`, `summary.dependency_maps[i]`, `child_ids[i]` are co-indexed.
Node IDs are unique within a fragment (not globally).

---

## Step 2 — `schemas/lemmas.schema.json`

Output of phase 4, input to phase 5. A flat list of lemma objects with provenance,
one per input fragment.

```json
{
  "lemmas": [
    {
      "fragment_id": 0,
      "source_file": "...",
      "decl_name": "...",
      "premises": ["h1 : T1", "h2 : T2"],
      "body": "<Lem(Υ) as Lean prop string, or 'True' when ⊤>",
      "conclusion": "<gF>",
      "statement": "<full lemma statement string>"
    }
  ]
}
```

`premises` = the hypotheses in A (minimal support), formatted as `"name : Type"`.  
`statement` = `"(h1 : T1) → (h2 : T2) → body → conclusion"` (flat implication chain, each premise wrapped in parens).  
When `body = "True"`, emit `"(h1 : T1) → ... → conclusion"` (drop the True conjunct).

---

## Step 3 — `build.sbt`

Three subprojects sharing upickle for JSON:

```scala
val upickleVersion = "3.3.1"

lazy val pog = project.in(file("pog"))
  .settings(libraryDependencies += "com.lihaoyi" %% "upickle" % upickleVersion)

lazy val fragmentation = project.in(file("fragmentation"))
  .settings(libraryDependencies += "com.lihaoyi" %% "upickle" % upickleVersion)
  .dependsOn(pog)

lazy val support = project.in(file("support"))
  .settings(
    libraryDependencies ++= Seq(
      "com.lihaoyi" %% "upickle" % upickleVersion,
      "org.scalatest" %% "scalatest" % "3.2.18" % Test
    )
  )
```

---

## Step 4 — `Types.scala`

One case class / sealed trait per concept:

```scala
case class Hypothesis(name: String, typ: String)
case class Obligation(hypotheses: List[Hypothesis], goal: String)
case class TacticSummary(directlyUsed: Set[String], dependencyMaps: List[Map[String, Set[String]]])

sealed trait PartialTree
case class Hole(holeId: String, obligation: Obligation)                                      extends PartialTree
case class Leaf(tacticText: String, obligation: Obligation, summary: TacticSummary)          extends PartialTree
case class Node(tacticText: String, obligation: Obligation, outputObligations: List[Obligation],
                summary: TacticSummary, children: List[PartialTree])                         extends PartialTree

case class Fragment(fragmentId: Int, sourceFile: String, declName: String,
                    rootObligation: Obligation, tree: PartialTree)

case class LemmaObj(fragmentId: Int, sourceFile: String, declName: String,
                    premises: List[String], body: String, conclusion: String, statement: String)
```

Note: `PartialTree` is the in-memory recursive representation used for computation.
The flat `nodes` list in the JSON is reconstructed into a `PartialTree` by the Serializer.

---

## Step 5 — `SupportCalc.scala`

Direct encoding of Figure 1:

```scala
object SupportCalc {
  def computeSupport(tree: PartialTree): Set[String] = tree match {
    case Hole(_, _)          => Set.empty                             // Supp-Hole
    case Leaf(_, _, summary) => summary.directlyUsed                  // Supp-Leaf
    case Node(_, _, _, summary, children) =>                          // Supp-Comp
      val pulled = children.zipWithIndex.flatMap { case (child, i) =>
        val ai = computeSupport(child)
        val pi = summary.dependencyMaps(i)
        ai.flatMap(h => pi.getOrElse(h, Set.empty))
      }.toSet
      summary.directlyUsed ++ pulled
  }
}
```

---

## Step 6 — `LemmaConstructor.scala`

```scala
object LemmaConstructor {
  // None = ⊤
  def computeLem(tree: PartialTree): Option[String] =
    tree match {
      case Hole(_, obl)     => Some(obl.goal)
      case Leaf(_, _, _)    => None
      case Node(_, obl, outputObls, _, children) =>
        val parentNames = obl.hypotheses.map(_.name).toSet
        val parts = children.zipWithIndex.flatMap { case (child, i) =>
          computeLem(child).map { lemStr =>
            val newHyps = outputObls(i).hypotheses.filterNot(h => parentNames(h.name))
            if (newHyps.isEmpty) lemStr
            else s"(${newHyps.map(h => s"${h.name} : ${h.typ}").mkString(" ∧ ")}) → $lemStr"
          }
        }
        if (parts.isEmpty) None else Some(parts.mkString(" ∧ "))
    }

  def constructLemma(fragment: Fragment): LemmaObj = {
    val support  = SupportCalc.computeSupport(fragment.tree)
    val premises = fragment.rootObligation.hypotheses
                     .filter(h => support(h.name))
                     .map(h => s"${h.name} : ${h.typ}")
    val body       = computeLem(fragment.tree).getOrElse("True")
    val conclusion = fragment.rootObligation.goal
    val antecedents = premises.map(p => s"($p)") ++ (if (body == "True") Nil else List(body))
    val stmt = if (antecedents.isEmpty) conclusion
               else antecedents.mkString(" → ") + " → " + conclusion
    LemmaObj(fragment.fragmentId, fragment.sourceFile, fragment.declName,
             premises, body, conclusion, stmt)
  }
}
```

---

## Step 7 — `Serializer.scala`

- Parse `segments.schema.json`-conforming JSON → `List[Fragment]` using upickle
- Serialize `List[LemmaObj]` → JSON conforming to `lemmas.schema.json`
- `main`: read segments JSON from stdin (or file arg), run construction, write lemmas JSON to stdout (or file arg)

Key upickle note: use `@upickle.implicits.key("kind")` on the `PartialTree` discriminator,
`@upickle.implicits.key("hole")` / `"leaf"` / `"node"` on case classes.

Flat-to-tree reconstruction: the JSON `nodes` array is a flat list; the Serializer must
rebuild the recursive `PartialTree` before passing a `Fragment` to `LemmaConstructor`:
1. Parse all nodes into a `Map[Int, RawNode]`
2. Recursively build `PartialTree` starting from `root_node_id`, looking up each
   `child_id` in the map to build children

`RawNode` is a serialization-only type (wire format) defined inside `Serializer.scala`;
it should not leak into `Types.scala`.

---

## Step 8 — Tests

Build two test files on hand-crafted `PartialTree` values — no file I/O needed.

### `SupportCalcTest.scala`

| Scenario | Expected A |
|----------|-----------|
| Single hole | `∅` |
| Single leaf with `directly_used = {h1}` | `{h1}` |
| Node with two holes, `U={h1}`, `π₁={h2→{h1,h2}}`, `π₂={}`, `A₁=A₂=∅` | `{h1}` |
| Node with one leaf child (`A_child = {h2}`), `π₁={h2→{h1}}`, `U={}` | `{h1}` |

### `LemmaConstructorTest.scala`

| Scenario | Expected Lem |
|----------|-------------|
| Single hole at `(Γℓ, "P ∧ Q")` | `"P ∧ Q"` |
| Single leaf (no children) | `None` (⊤) |
| Node → [hole1, hole2], no new hyps | conjunction of hole goals |
| Node → [leaf, hole], leaf gives ⊤ (filtered), hole gives goal | just hole goal |
| Node → [hole] with new hyp `h3 : T` | `"(h3 : T) → goalℓ"` |

---

## Logical Build Order

1. `schemas/segments.schema.json` + `schemas/lemmas.schema.json` — define contracts first
2. `build.sbt` — unblocks compilation
3. `Types.scala` — no dependencies, unblocks steps 4–7
4. `SupportCalcTest.scala` (hand-built trees) + `SupportCalc.scala`
5. `LemmaConstructorTest.scala` + `LemmaConstructor.scala`
6. `Serializer.scala` + integration smoke-test against sample segments JSON

---

## Verification

```bash
cd /nas/lemma-disc/scala-core
sbt "support/test"                          # unit tests pass
echo '<sample segments JSON>' | sbt "support/run"   # produces valid lemmas JSON
```
