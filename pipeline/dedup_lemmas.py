#!/usr/bin/env python3
"""Drop lemma/fragment pairs whose (lemma statement, root obligation) already appeared.

Phase 4 (support minimization) can map two enumerated fragments to the same
final lemma — different proof structures that collapse to identical statements
after support minimization. This pass dedupes at the post-phase-4 granularity:
for each matching (statement, root_obligation) key, keep the earliest
fragment_id and drop later ones from BOTH the lemmas and fragments arrays.

Surviving entries are renumbered 0..N-1 so fragment_id remains a contiguous
index — matching the invariant `enumerate.py` already maintains.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _root_obligation_key(root_obl: dict) -> str:
    hyps = " ".join(f"({h['name']} : {h['type']})" for h in root_obl["hypotheses"])
    return f"{hyps} ⊢ {root_obl['goal']}"


def dedup(
    lemmas: list[dict], fragments: list[dict]
) -> tuple[list[dict], list[dict]]:
    frag_by_id = {f["fragment_id"]: f for f in fragments}
    seen: set[tuple[str, str]] = set()
    kept_lemmas: list[dict] = []
    kept_fragments: list[dict] = []

    for lemma in sorted(lemmas, key=lambda l: l["fragment_id"]):
        frag = frag_by_id[lemma["fragment_id"]]
        key = (lemma["statement"], _root_obligation_key(frag["root_obligation"]))
        if key in seen:
            continue
        seen.add(key)
        new_id = len(kept_lemmas)
        kept_lemmas.append({**lemma, "fragment_id": new_id})
        kept_fragments.append({**frag, "fragment_id": new_id})
    return kept_lemmas, kept_fragments


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("lemmas", help="Lemmas JSON path (modified in place by default)")
    ap.add_argument("fragments", help="Fragments JSON path (modified in place by default)")
    ap.add_argument("--lemmas-out", default=None, metavar="FILE",
                    help="Write filtered lemmas here instead of overwriting")
    ap.add_argument("--fragments-out", default=None, metavar="FILE",
                    help="Write filtered fragments here instead of overwriting")
    args = ap.parse_args()

    lemmas = json.loads(Path(args.lemmas).read_text())["lemmas"]
    fragments = json.loads(Path(args.fragments).read_text())["fragments"]
    n_before = len(lemmas)

    lemmas, fragments = dedup(lemmas, fragments)

    Path(args.lemmas_out or args.lemmas).write_text(
        json.dumps({"lemmas": lemmas}, indent=2, ensure_ascii=False)
    )
    Path(args.fragments_out or args.fragments).write_text(
        json.dumps({"fragments": fragments}, indent=2, ensure_ascii=False)
    )

    dropped = n_before - len(lemmas)
    print(f"Deduplicated: {n_before} → {len(lemmas)} lemmas ({dropped} dropped)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
