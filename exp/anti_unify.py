#!/usr/bin/env python3
"""Cluster Lean 4 lemma statements by anti-unification using an LLM.

Pipeline:
  1. Load lemma JSON file(s) (see ``lemma_record.load_lemmas``).
  2. Syntactic prefilter via ``lemma_normalize.canonical_key`` — alpha-
     equivalent statements collapse into one bucket before any LLM call.
  3. Incremental LLM clustering — for each bucket representative, ask the
     model whether it matches an existing cluster (returning the strict
     anti-unifier as the new canonical) or starts a new one.
  4. Emit one JSON file via ``lemma_record.emit_clusters``.

LLM responses are cached at ``exp/.cache/anti_unify/<hash>.json`` keyed by
(model, system prompt, user prompt) so re-runs are free.

Usage
-----
    export OPENAI_API_KEY=...
    python exp/anti_unify.py data/prop_56_lemmas.json \\
        --out data/output/anti_unify_prop_56.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lemma_record import (  # noqa: E402
    Cluster, LemmaRecord, emit_clusters, group_records, load_lemmas,
)
from lemma_normalize import canonical_key, strip_type_binders  # noqa: E402


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You cluster Lean 4 lemma statements by strict anti-unification.

Two statements belong to the same cluster iff they share a non-trivial \
most-general common generalization (anti-unifier S): each statement is \
obtained from S purely by INSTANTIATING its top-level bound variables with \
specific terms. No hypotheses are added or removed during instantiation.

You will be shown a CANDIDATE statement and a list of EXISTING clusters, \
each with a canonical statement and one example member. Decide exactly one of:

  - Candidate matches cluster K. Return JSON:
      {"match": K, "new_canonical": "<anti-unifier of cluster K's members and the candidate, as a Lean 4 statement>", "reason": "<short>"}
    new_canonical must subsume BOTH the prior canonical AND the candidate; \
    generalize the prior canonical only if the candidate exposes that it was \
    too specific, otherwise keep it.
  - Candidate matches no cluster. Return JSON:
      {"match": null, "new_canonical": "", "reason": "<short>"}

Rules:
  1. Differing concrete subterms (e.g., (x+y) vs a, or 3 vs n) become fresh \
     top-level term-variable binders in the canonical.
  2. STRICT: do NOT drop or add hypotheses during merging. Two statements \
     with different numbers of propositional hypotheses, or with hypotheses \
     that cannot themselves be pairwise anti-unified, must NOT merge.
  3. Do NOT merge across different function symbols or different \
     propositional connectives. List.drop ≠ List.take. (a + b = c) ≠ \
     (a + b ≤ c). When in doubt, do NOT merge.
  4. Canonical variable names should be short and idiomatic \
     (x, y, z, n, m, xs, ys, h, h1, ...).
  5. Output JSON only, no surrounding prose.

Worked examples:

A) Merge — body generalization (no hypotheses)
   cluster 0 canonical: (a b : Nat) : a + b = b + a
   candidate:           (x y z : Nat) : (x + y) + z = z + (x + y)
   -> {"match": 0, "new_canonical": "(x y : Nat) : x + y = y + x", "reason": "candidate instantiates x:=x+y, y:=z"}

B) No merge — different function symbols
   cluster 0 canonical: (n : Nat) (xs : List α) : List.drop n xs = xs
   candidate:           (n : Nat) (xs : List α) : List.take n xs = xs
   -> {"match": null, "new_canonical": "", "reason": "drop and take are distinct"}

C) Merge — hypothesis types anti-unified pairwise
   cluster 0 canonical: (n : Nat) (h : n > 0) : n + n > 0
   candidate:           (m : Nat) (h : m > 1) : m + m > 1
   -> {"match": 0, "new_canonical": "(n k : Nat) (h : n > k) : n + n > k", "reason": "single hypothesis on each; constants 0 and 1 abstract to k"}

D) No merge — differing hypothesis count
   cluster 0 canonical: (xs : List α) : List.length (List.reverse xs) = List.length xs
   candidate:           (xs : List α) (h : xs ≠ []) : List.length (List.reverse xs) = List.length xs
   -> {"match": null, "new_canonical": "", "reason": "extra hypothesis on candidate; strict AU does not weaken"}

E) No merge — different relation
   cluster 0 canonical: (n m : Nat) : n + m = m + n
   candidate:           (n m : Nat) : n + m ≤ m + n
   -> {"match": null, "new_canonical": "", "reason": "= vs ≤"}
"""


def _user_prompt(candidate: str, clusters: list[Cluster]) -> str:
    if not clusters:
        return f"Existing clusters: (none)\n\nCandidate:\n{candidate}\n"
    lines = ["Existing clusters:", ""]
    for i, c in enumerate(clusters):
        lines.append(f"[{i}] canonical: {c.canonical}")
        lines.append(f"    member:    {c.example_member()}")
    lines.append("")
    lines.append("Candidate:")
    lines.append(candidate)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM client + cache
# ---------------------------------------------------------------------------

@dataclass
class LLMDecision:
    match: int | None
    new_canonical: str
    reason: str


def _cache_path(cache_dir: Path, model: str, system: str, user: str) -> Path:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(b"\0")
    h.update(system.encode())
    h.update(b"\0")
    h.update(user.encode())
    return cache_dir / f"{h.hexdigest()}.json"


def _parse_decision(text: str) -> LLMDecision:
    obj = json.loads(text)
    m = obj.get("match")
    if m is not None and not isinstance(m, int):
        m = None
    return LLMDecision(
        match=m,
        new_canonical=str(obj.get("new_canonical", "") or ""),
        reason=str(obj.get("reason", "") or ""),
    )


class LLMClusterer:
    def __init__(self, model: str, cache_dir: Path, use_cache: bool = True):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = model
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        if use_cache:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def decide(self, candidate: str, clusters: list[Cluster]) -> LLMDecision:
        user = _user_prompt(candidate, clusters)
        cache_file = _cache_path(self.cache_dir, self.model, SYSTEM_PROMPT, user)
        if self.use_cache and cache_file.exists():
            payload = json.loads(cache_file.read_text())
            return _parse_decision(payload["response"])
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or "{}"
        if self.use_cache:
            cache_file.write_text(json.dumps(
                {"model": self.model, "system": SYSTEM_PROMPT,
                 "user": user, "response": text},
                ensure_ascii=False, indent=2,
            ))
        return _parse_decision(text)


# ---------------------------------------------------------------------------
# Clustering loop
# ---------------------------------------------------------------------------

def cluster_lemmas(
    records: list[LemmaRecord],
    clusterer: LLMClusterer,
    verbose: bool = False,
) -> list[Cluster]:
    buckets = group_records(records, canonical_key)
    # Shorter statements tend to be less specific; seeding clusters with them
    # first reduces order-dependence of the incremental merge.
    buckets.sort(key=lambda b: len(b[0].statement))
    if verbose:
        print(f"[anti_unify] {len(records)} input lemmas → "
              f"{len(buckets)} prefilter buckets", file=sys.stderr)

    clusters: list[Cluster] = []
    for bi, bucket in enumerate(buckets):
        rep = bucket[0]
        rep_stmt = strip_type_binders(rep.statement)
        if not clusters:
            clusters.append(Cluster(canonical=rep_stmt, members=list(bucket)))
            if verbose:
                print(f"[anti_unify] bucket {bi}: new cluster 0", file=sys.stderr)
            continue

        decision = clusterer.decide(rep_stmt, clusters)
        if (decision.match is not None
                and 0 <= decision.match < len(clusters)
                and decision.new_canonical):
            target = clusters[decision.match]
            target.canonical = decision.new_canonical
            target.members.extend(bucket)
            if verbose:
                print(f"[anti_unify] bucket {bi}: merged into cluster "
                      f"{decision.match} ({decision.reason})", file=sys.stderr)
        else:
            clusters.append(Cluster(canonical=rep_stmt, members=list(bucket)))
            if verbose:
                print(f"[anti_unify] bucket {bi}: new cluster "
                      f"{len(clusters) - 1} ({decision.reason})", file=sys.stderr)

    clusters.sort(key=lambda c: -c.frequency)
    return clusters


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _prompt_hash() -> str:
    return hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:16]


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
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+",
                        help="lemma JSON file(s); globs accepted")
    parser.add_argument("--out", type=Path, required=True,
                        help="output JSON path")
    parser.add_argument("--model", default="gpt-4o",
                        help="OpenAI model id (default: gpt-4o)")
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(__file__).resolve().parent / ".cache" / "anti_unify")
    parser.add_argument("--no-cache", action="store_true",
                        help="bypass the LLM response cache")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N input lemmas (for dev)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if not args.no_cache and "OPENAI_API_KEY" not in os.environ:
        print("[anti_unify] warning: OPENAI_API_KEY not set; will fail on any cache miss",
              file=sys.stderr)

    input_paths = _expand_inputs(args.inputs)
    records = load_lemmas(input_paths)
    if args.limit is not None:
        records = records[:args.limit]
    if not records:
        print("[anti_unify] no lemmas loaded", file=sys.stderr)
        return 1

    clusterer = LLMClusterer(
        model=args.model,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
    )
    clusters = cluster_lemmas(records, clusterer, verbose=args.verbose)
    emit_clusters(
        clusters,
        args.out,
        meta={
            "method": "llm-anti-unification",
            "model": args.model,
            "prompt_template_hash": _prompt_hash(),
            "input_files": [str(p) for p in input_paths],
        },
    )

    if args.verbose:
        print(f"[anti_unify] wrote {len(clusters)} clusters to {args.out}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
