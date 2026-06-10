#!/usr/bin/env python3
"""Proof-trace → fragment stub (replaces phases 2+3).

Converts a digestion proof trace into a single segments.schema.json fragment
by manually choosing a root node and optional cut-off points.

Omit --root to print the proof tree and exit (helps choose node IDs).
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Hypothesis:
    name: str
    type: str


@dataclass
class Obligation:
    hypotheses: list[Hypothesis]
    goal: str


@dataclass
class TacticSummary:
    directly_used: list[str]
    dependency_maps: list[dict[str, list[str]]]


@dataclass
class TacticNode:
    id: int
    tactic_text: str
    input_obligation: Obligation
    output_obligations: list[Obligation]
    summary: TacticSummary
    parent_id: Optional[int]
    child_ids: list[int]


# --- Parsing ------------------------------------------------------------------

def _parse_obligation(d: dict) -> Obligation:
    return Obligation(
        hypotheses=[Hypothesis(name=h["name"], type=h["type"]) for h in d["hypotheses"]],
        goal=d["goal"],
    )


def _parse_node(d: dict) -> TacticNode:
    return TacticNode(
        id=d["id"],
        tactic_text=d["tactic_text"],
        input_obligation=_parse_obligation(d["input_obligation"]),
        output_obligations=[_parse_obligation(o) for o in d["output_obligations"]],
        summary=TacticSummary(
            directly_used=d["summary"]["directly_used"],
            dependency_maps=d["summary"]["dependency_maps"],
        ),
        parent_id=d["parent_id"],
        child_ids=d["child_ids"],
    )


def load_trace(
    path: str, decl_name: Optional[str]
) -> tuple[str, str, int, dict[int, TacticNode]]:
    """Return (source_file, decl_name, root_tactic_id, node_map)."""
    raw = json.loads(Path(path).read_text())

    if "declarations" in raw:
        # Full trace.schema.json: {source_file, declarations: [...]}
        source_file = raw["source_file"]
        decls = raw["declarations"]
        if decl_name is not None:
            matches = [d for d in decls if d["name"] == decl_name]
            if not matches:
                sys.exit(f"Error: declaration '{decl_name}' not found. "
                         f"Available: {[d['name'] for d in decls]}")
            decl = matches[0]
        elif len(decls) == 1:
            decl = decls[0]
        else:
            sys.exit(f"Error: trace has multiple declarations; use --decl. "
                     f"Available: {[d['name'] for d in decls]}")
    else:
        # Single-declaration snapshot: {name, statement, root_tactic_id, tactic_nodes}
        source_file = path
        decl = raw

    node_map = {n["id"]: _parse_node(n) for n in decl["tactic_nodes"]}
    return source_file, decl["name"], decl["root_tactic_id"], node_map


# --- Tree display -------------------------------------------------------------

def print_tree(node_id: int, node_map: dict[int, TacticNode], indent: int = 0) -> None:
    node = node_map[node_id]
    goal = node.input_obligation.goal
    truncated = goal if len(goal) <= 55 else goal[:52] + "..."
    print("  " * indent + f"[{node.id}]  {node.tactic_text!r:<28}  ⊢ {truncated}")
    for child_id in node.child_ids:
        print_tree(child_id, node_map, indent + 1)


# --- Fragment construction ----------------------------------------------------

def _descendants(node_id: int, node_map: dict[int, TacticNode]) -> set[int]:
    result: set[int] = {node_id}
    for child_id in node_map[node_id].child_ids:
        result |= _descendants(child_id, node_map)
    return result


def _obl_json(obl: Obligation) -> dict:
    return {
        "hypotheses": [{"name": h.name, "type": h.type} for h in obl.hypotheses],
        "goal": obl.goal,
    }


def _convert(
    node_id: int,
    node_map: dict[int, TacticNode],
    cutoffs: set[int],
    parent_id: Optional[int],
    out: list,
    hole_counter: list[int],
) -> None:
    node = node_map[node_id]
    obl = _obl_json(node.input_obligation)

    if node_id in cutoffs:
        out.append({
            "id": node_id,
            "kind": "hole",
            "hole_id": f"ℓ{hole_counter[0]}",
            "parent_id": parent_id,
            "child_ids": [],
            "obligation": obl,
        })
        hole_counter[0] += 1
        return

    summary = {
        "directly_used": node.summary.directly_used,
        "dependency_maps": node.summary.dependency_maps,
    }

    if not node.child_ids:
        out.append({
            "id": node_id,
            "kind": "leaf",
            "tactic_text": node.tactic_text,
            "parent_id": parent_id,
            "child_ids": [],
            "obligation": obl,
            "summary": summary,
        })
    else:
        out.append({
            "id": node_id,
            "kind": "node",
            "tactic_text": node.tactic_text,
            "parent_id": parent_id,
            "child_ids": node.child_ids,
            "obligation": obl,
            "output_obligations": [_obl_json(o) for o in node.output_obligations],
            "summary": summary,
        })
        for child_id in node.child_ids:
            _convert(child_id, node_map, cutoffs, node_id, out, hole_counter)


def build_fragment(
    root_id: int,
    cutoffs: set[int],
    source_file: str,
    decl_name: str,
    node_map: dict[int, TacticNode],
) -> dict:
    nodes: list[dict] = []
    _convert(root_id, node_map, cutoffs, None, nodes, [0])
    return {
        "fragment_id": 0,
        "source_file": source_file,
        "decl_name": decl_name,
        "root_node_id": root_id,
        "root_obligation": _obl_json(node_map[root_id].input_obligation),
        "nodes": nodes,
    }


# --- Entry point -------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("trace", help="Proof trace JSON (snapshot or trace.schema.json)")
    ap.add_argument("--root", type=int, default=None, metavar="ID",
                    help="Root node ID for the fragment (omit to print tree and exit)")
    ap.add_argument("--cutoffs", type=int, nargs="*", default=[], metavar="ID",
                    help="Node IDs to replace with holes")
    ap.add_argument("--decl", default=None, metavar="NAME",
                    help="Declaration name (only needed for multi-declaration traces)")
    ap.add_argument("--output", default=None, metavar="FILE",
                    help="Write fragment JSON to FILE instead of stdout")
    ap.add_argument("--print-tree", action="store_true",
                    help="Print the proof tree (implied when --root is omitted); "
                         "if --root is also given, print tree then emit JSON")
    args = ap.parse_args()

    source_file, decl_name, root_tactic_id, node_map = load_trace(args.trace, args.decl)

    if args.root is None or args.print_tree:
        print(f"# {decl_name}  (root_tactic_id={root_tactic_id})\n")
        print_tree(root_tactic_id, node_map)
        if args.root is None:
            return
        print()  # blank line before JSON when both tree and output are requested

    root_id = args.root
    cutoffs = set(args.cutoffs)

    all_ids = _descendants(root_tactic_id, node_map)
    if root_id not in all_ids:
        sys.exit(f"Error: node {root_id} is not in the proof tree of '{decl_name}'")

    subtree = _descendants(root_id, node_map)
    bad = [c for c in cutoffs if c not in subtree or c == root_id]
    if bad:
        sys.exit(f"Error: node(s) {bad} are not proper descendants of root {root_id}")

    fragment = build_fragment(root_id, cutoffs, source_file, decl_name, node_map)
    output = json.dumps({"fragments": [fragment]}, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
