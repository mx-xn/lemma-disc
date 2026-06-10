# Fragmentation Stub — Plan

## Purpose

Temporary replacement for phases 2+3 (POG construction + fragment construction).
Instead of building a POG and decomposing it, the user manually picks a root node
and zero or more cut-off points on the subtree. The resulting proof fragment is
written in `segments.schema.json` format, ready for phase 4 (`Serializer.scala`).

Will be discarded once phases 2+3 are implemented.

---

## Data format gap being bridged

| Field in trace (`TacticNode`) | Field in segments (`TreeNode`) |
|-------------------------------|-------------------------------|
| `input_obligation`            | `obligation`                  |
| `output_obligations`          | `output_obligations` (node only) |
| `summary`                     | `summary` (leaf/node only)    |
| `child_ids == []`             | `kind: "leaf"` (if not cut off) |
| `child_ids != []`             | `kind: "node"` (if not cut off) |
| any cut-off node              | `kind: "hole"`, `child_ids: []`, `hole_id: "ℓN"` |

`source_file` in the segments format is the Lean `.lean` source path (provenance only,
not used in computation). When the input is a snapshot (no `source_file` field), we
use the trace JSON path as a placeholder.

---

## File

Single script: `fragmentation-stub/fragment.py`. No dependencies beyond stdlib.

---

## CLI

```
# Inspect the tree, pick nodes
python fragment.py <trace.json>
python fragment.py <trace.json> --print-tree          # same

# Extract a fragment
python fragment.py <trace.json> --root <id> [--cutoffs <id>...]
python fragment.py <trace.json> --root <id> --cutoffs 3 7 --output frag.json

# When the trace has multiple declarations
python fragment.py <trace.json> --decl <name> --root <id>
```

Omitting `--root` (or passing `--print-tree`) prints the tree and exits.
`--print-tree` alongside `--root` prints the tree *then* emits the JSON.

---

## Batching

One invocation produces one fragment. To produce many from the same trace, loop in
bash and merge with `jq`:

```bash
for root in 0 2 7; do
  python fragment.py trace.json --root $root --output frag_${root}.json
done
jq -s '{fragments: [.[].fragments[]]}' frag_*.json > all_fragments.json
```

---

## Conversion algorithm

DFS from `root_id`. At each node:
- If in `cutoffs` → emit `hole` node (`child_ids: []`, `hole_id: "ℓN"`)
- Else if `child_ids == []` in trace → emit `leaf` node
- Else → emit `node` (composite), then recurse into each child

Original node IDs are preserved (Serializer builds a map by ID, so they need not
be 0-based, only consistent within the fragment).

---

## Input formats accepted

- **Snapshot** (e.g. `digestion/tests/snapshots/*.json`): top-level keys are
  `name`, `statement`, `root_tactic_id`, `tactic_nodes`.
- **Full trace** (`trace.schema.json`): top-level keys are `source_file`,
  `declarations`. The `--decl` arg selects which declaration to use when there
  are multiple.
