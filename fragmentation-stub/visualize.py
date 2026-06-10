#!/usr/bin/env python3
"""Print fragment trees from a segments.schema.json file.

Usage:
  visualize.py <fragments.json>            # show all fragments
  visualize.py <fragments.json> --id N     # show only fragment_id=N
"""

import argparse
import json
import sys
from pathlib import Path


def _trunc(s: str, n: int = 55) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def _print_node(node_id: int, node_map: dict, indent: int = 0) -> None:
    node = node_map[node_id]
    kind = node["kind"]
    goal = _trunc(node["obligation"]["goal"])
    if kind == "hole":
        label = f"hole({node['hole_id']})"
    else:
        # leaf or node
        label = f"{kind}  {node['tactic_text']!r}"
    print("  " * indent + f"[{node['id']}] {label:<42}  ⊢ {goal}")
    for child_id in node.get("child_ids", []):
        _print_node(child_id, node_map, indent + 1)


def _visualize(fragment: dict) -> None:
    node_map = {n["id"]: n for n in fragment["nodes"]}
    print(f"# fragment {fragment['fragment_id']}  ({fragment['decl_name']})")
    print(f"# root ⊢ {fragment['root_obligation']['goal']}")
    _print_node(fragment["root_node_id"], node_map)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("fragments", help="fragments JSON (segments.schema.json)")
    ap.add_argument("--id", type=int, default=None, metavar="N",
                    help="show only fragment with fragment_id=N")
    args = ap.parse_args()

    frags = json.loads(Path(args.fragments).read_text())["fragments"]

    if args.id is not None:
        frags = [f for f in frags if f["fragment_id"] == args.id]
        if not frags:
            sys.exit(f"No fragment with fragment_id={args.id}")

    for i, f in enumerate(frags):
        if i > 0:
            print()
        _visualize(f)


if __name__ == "__main__":
    main()
