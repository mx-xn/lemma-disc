#!/usr/bin/env python3
"""Auto-enumerate proof-trace → fragment candidates (replaces phases 2+3, batch mode).

Randomly samples (root, cutoffs) pairs from a proof trace and emits up to
--limit fragments in segments.schema.json format.

To add a new strategy, implement a generator with signature
    fn(node_map: dict, rng: random.Random) -> Generator[(root_id, frozenset[cutoffs])]
and register it in STRATEGIES.
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import FrozenSet, Generator

sys.path.insert(0, str(Path(__file__).parent))
from fragment import _descendants, build_fragment, load_trace


# ---------------------------------------------------------------------------
# Validity
# ---------------------------------------------------------------------------

def _effective_cutoffs(
    root_id: int, cutoffs: FrozenSet[int], node_map: dict
) -> FrozenSet[int]:
    """The subset of cutoffs reachable from root without passing through another
    cutoff. Two raw cutoff sets that differ only in unreachable entries denote
    the same fragment (since `_convert` stops at the first cutoff on each path),
    so dedup keys must use this canonical form.
    """
    effective: set[int] = set()

    def walk(node_id: int) -> None:
        if node_id in cutoffs:
            effective.add(node_id)
            return
        for child_id in node_map[node_id].child_ids:
            walk(child_id)

    walk(root_id)
    return frozenset(effective)


def _vh_nodes(root_id: int, cutoffs: FrozenSet[int], node_map: dict) -> list[int]:
    """Non-hole tactic nodes reachable from root without passing through a cutoff."""
    if root_id in cutoffs:
        return []
    result = [root_id]
    for child in node_map[root_id].child_ids:
        result.extend(_vh_nodes(child, cutoffs, node_map))
    return result


def _is_valid(root_id: int, cutoffs: FrozenSet[int], node_map: dict) -> bool:
    return (
        bool(node_map[root_id].child_ids)           # root must be composite
        and len(_vh_nodes(root_id, cutoffs, node_map)) >= 2
    )


def _default_heuristic(root_id: int, cutoffs: FrozenSet[int], node_map: dict) -> bool:
    """Accept unless the fragment both branches and has a hole (mirrors Decomposer.defaultHeuristic)."""
    vh = _vh_nodes(root_id, cutoffs, node_map)
    subgoal_counts = [len(node_map[n].output_obligations) for n in vh]
    hole_count = sum(subgoal_counts) - (len(vh) - 1)
    branches = any(m >= 2 for m in subgoal_counts)
    return not branches or hole_count == 0


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def random_strategy(
    node_map: dict, rng: random.Random
) -> Generator[tuple[int, FrozenSet[int]], None, None]:
    """Random composite root; each descendant independently included in cutoffs with p=0.5."""
    composite = [nid for nid, n in node_map.items() if n.child_ids]
    if not composite:
        return
    while True:
        root_id = rng.choice(composite)
        descendants = _descendants(root_id, node_map) - {root_id}
        cutoffs = frozenset(d for d in descendants if rng.random() < 0.5)
        yield root_id, cutoffs


STRATEGIES: dict[str, callable] = {
    "random": random_strategy,
}


# ---------------------------------------------------------------------------
# Enumeration loop
# ---------------------------------------------------------------------------

def enumerate_fragments(
    node_map: dict,
    source_file: str,
    decl_name: str,
    strategy: Generator,
    limit: int,
    max_attempts: int,
) -> list[dict]:
    seen: set[tuple] = set()
    fragments: list[dict] = []
    attempts = 0
    for root_id, cutoffs in strategy:
        if len(fragments) >= limit or attempts >= max_attempts:
            break
        attempts += 1
        cutoffs = _effective_cutoffs(root_id, cutoffs, node_map)
        key = (root_id, cutoffs)
        if key in seen:
            continue
        seen.add(key)
        if not _is_valid(root_id, cutoffs, node_map):
            continue
        if not _default_heuristic(root_id, cutoffs, node_map):
            continue
        frag = build_fragment(root_id, cutoffs, source_file, decl_name, node_map)
        frag["fragment_id"] = len(fragments)
        fragments.append(frag)
    return fragments


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("trace", help="Proof trace JSON (snapshot or trace.schema.json)")
    ap.add_argument("--decl", default=None, metavar="NAME",
                    help="Declaration name (for multi-declaration traces)")
    ap.add_argument("--limit", type=int, default=20, metavar="N",
                    help="Max fragments to emit (default: 20)")
    ap.add_argument("--strategy", choices=list(STRATEGIES), default="random",
                    help="Sampling strategy (default: random)")
    ap.add_argument("--seed", type=int, default=None, metavar="N",
                    help="RNG seed for reproducibility")
    ap.add_argument("--max-attempts", type=int, default=10_000, metavar="N",
                    help="Abort after this many sampling attempts (default: 10000)")
    ap.add_argument("--output", default=None, metavar="FILE",
                    help="Write to FILE instead of stdout")
    args = ap.parse_args()

    source_file, decl_name, _root_tactic_id, node_map = load_trace(args.trace, args.decl)

    rng = random.Random(args.seed)
    strategy = STRATEGIES[args.strategy](node_map, rng)

    fragments = enumerate_fragments(
        node_map, source_file, decl_name, strategy, args.limit, args.max_attempts
    )

    if not fragments:
        print("Warning: no valid fragments found.", file=sys.stderr)

    output = json.dumps({"fragments": fragments}, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote {len(fragments)} fragment(s) to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
