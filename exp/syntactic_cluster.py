#!/usr/bin/env python3
"""Cluster Lean 4 lemma statements by exact syntactic equivalence.

Two statements share a cluster iff their ``canonical_key`` (type-binder
stripped + alpha-renamed) matches exactly. No LLM, no cache, deterministic.

The output JSON shape matches ``anti_unify.py`` so ``plot_freq_vs_hyps.py``
works unchanged.

Usage
-----
    python exp/syntactic_cluster.py data/prop_56_lemmas.json \\
        --out data/output/syntactic_prop_56.json
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lemma_record import (  # noqa: E402
    Cluster, LemmaRecord, emit_clusters, group_records, load_lemmas,
)
from lemma_normalize import canonical_key, strip_type_binders  # noqa: E402


def cluster_syntactically(records: Sequence[LemmaRecord]) -> list[Cluster]:
    """One cluster per distinct canonical key.

    Canonical display = first member's statement, type-binders stripped.
    Members preserve the original (unstripped) statement.
    """
    buckets = group_records(records, canonical_key)
    clusters = [
        Cluster(canonical=strip_type_binders(bucket[0].statement), members=list(bucket))
        for bucket in buckets
    ]
    clusters.sort(key=lambda c: -c.frequency)
    return clusters


def _expand_inputs(args: list[str]) -> list[Path]:
    out: list[Path] = []
    for a in args:
        matches = sorted(glob.glob(a))
        if matches:
            out.extend(Path(m) for m in matches)
        else:
            out.append(Path(a))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+",
                        help="lemma JSON file(s); globs accepted")
    parser.add_argument("--out", type=Path, required=True,
                        help="output JSON path")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N input lemmas")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    input_paths = _expand_inputs(args.inputs)
    records = load_lemmas(input_paths)
    if args.limit is not None:
        records = records[:args.limit]
    if not records:
        print("[syntactic_cluster] no lemmas loaded", file=sys.stderr)
        return 1

    clusters = cluster_syntactically(records)
    emit_clusters(
        clusters,
        args.out,
        meta={
            "method": "syntactic",
            "normalization": "strip Type/Sort binders + alpha-rename",
            "input_files": [str(p) for p in input_paths],
        },
    )
    if args.verbose:
        print(f"[syntactic_cluster] {len(records)} lemmas → "
              f"{len(clusters)} clusters", file=sys.stderr)
        print(f"[syntactic_cluster] wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
