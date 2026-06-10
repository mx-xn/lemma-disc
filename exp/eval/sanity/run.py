"""Sanity check: prove theorems with and without the learned lemma library.

Step 1 (without lemmas): runs run_baseline, which uses baseline.md — a prompt
  with no hint section — so the LLM is never told lemmas exist.

Step 2 (with lemmas): runs prove_round with the full flat lemma pool loaded
  from Lemmas.lean, using the solo.md hint-aware prompt.

Outputs written under --output-dir:
  theorems_sanity.json      filtered theorems (only those covered in Lemmas.lean)
  without_lemmas/           run_baseline artifacts (01_baseline.json, etc.)
  with_lemmas/              prove_results.json from prove_round
  comparison.json           side-by-side ok/fail per theorem + aggregate counts

Usage:
    python -m exp.eval.sanity.run [options]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from exp.eval.lib.retriever import ByT5Retriever, Retriever
from exp.eval.sanity.lemma_loader import load_by_prop, load_flat
from exp.eval.stages.baseline import BASELINE_JSON, run_baseline
from exp.eval.stages.prove import RoundResult, prove_round
from exp.lib.corpus import Theorem, TheoremSet, load_theorems
from exp.lib.llm import LLM

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_THEOREMS = _REPO_ROOT / "exp" / "expB" / "input" / "theorems.json"
_DEFAULT_LEMMAS = (
    _REPO_ROOT / "data" / "input" / "MiniCodePropsLeanSrc" / "LeanSrc" / "Lemmas.lean"
)
_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"


# ---------------------------------------------------------------------------
# Pure helpers (exported for testing)
# ---------------------------------------------------------------------------

def filter_by_ids(
    theorems: list[Theorem],
    ids: list[str] | None,
) -> list[Theorem]:
    """Return only theorems whose theorem_id is in ids, preserving order.

    If ids is None or empty, the full list is returned unchanged.
    Unknown ids in the filter set are silently ignored.
    """
    if not ids:
        return theorems
    keep = set(ids)
    return [t for t in theorems if t.theorem_id in keep]


def filter_theorems(
    theorems: list[Theorem],
    lemma_dict: dict[str, list[str]],
) -> list[Theorem]:
    """Return theorems whose prop_N id appears as a key in lemma_dict."""
    return [t for t in theorems if _prop_num(t.theorem_id) in lemma_dict]


def build_comparison(
    baseline_ok: dict[str, bool],
    with_lemma_ok: dict[str, bool],
    lemma_pool_size: int,
) -> dict:
    """Return the comparison summary dict.

    Args:
        baseline_ok:    {theorem_id -> ok} for the no-hint condition.
        with_lemma_ok:  {theorem_id -> ok} for the with-lemma condition.
        lemma_pool_size: total number of hint statements supplied.
    """
    theorem_ids = sorted(set(baseline_ok) | set(with_lemma_ok))
    per_theorem = {
        tid: {
            "without_lemmas": baseline_ok.get(tid, False),
            "with_lemmas": with_lemma_ok.get(tid, False),
        }
        for tid in theorem_ids
    }
    return {
        "total_theorems": len(theorem_ids),
        "lemma_pool_size": lemma_pool_size,
        "without_lemmas": {
            "solved": sum(1 for v in baseline_ok.values() if v),
            "failed": sum(1 for v in baseline_ok.values() if not v),
        },
        "with_lemmas": {
            "solved": sum(1 for v in with_lemma_ok.values() if v),
            "failed": sum(1 for v in with_lemma_ok.values() if not v),
        },
        "per_theorem": per_theorem,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _prop_num(theorem_id: str) -> str | None:
    """Extract '29' from 'prop_29', or None if the ID doesn't match."""
    m = re.match(r"^prop_(\d+)$", theorem_id)
    return m.group(1) if m else None


def _resolve_setup(tset: TheoremSet) -> tuple[Path, list[str]]:
    if tset.lake_project is None:
        raise ValueError("lake_project must be set in theorems.json")
    if not tset.imports:
        raise ValueError("imports must be set in theorems.json")
    return Path(tset.lake_project), list(tset.imports)


def _write_theorems_json(
    theorems: list[Theorem],
    lake_project: Path,
    imports: list[str],
    path: Path,
) -> None:
    """Write a theorems.json file compatible with load_theorems."""
    data = {
        "lake_project": str(lake_project),
        "imports": imports,
        "theorems": [
            {
                "theorem_id": t.theorem_id,
                "lean_path": t.lean_path,
                "statement_text": t.statement_text,
                "local_ctx": t.local_ctx,
            }
            for t in theorems
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _load_baseline_ok(baseline_dir: Path) -> dict[str, bool]:
    """Load {theorem_id -> ok} from the JSON written by run_baseline."""
    data = json.loads((baseline_dir / BASELINE_JSON).read_text())
    return {tid: rec["ok"] for tid, rec in data["results"].items()}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(
    *,
    theorems_path: Path,
    lemmas_path: Path,
    output_dir: Path,
    llm_model: str,
    max_attempts: int,
    num_workers: int,
    force: bool,
    theorem_ids: list[str] | None = None,
    retriever: Retriever | None = None,
    top_k: int | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tset = load_theorems(theorems_path)
    lake_project, imports = _resolve_setup(tset)

    lemma_dict = load_by_prop(lemmas_path)
    lemma_pool = load_flat(lemmas_path)
    filtered = filter_theorems(filter_by_ids(list(tset.theorems), theorem_ids), lemma_dict)

    if not filtered:
        print("[sanity] no theorems matched the learned lemmas — nothing to do", file=sys.stderr)
        return

    per_theorem_pools = {
        thm.theorem_id: lemma_dict[_prop_num(thm.theorem_id)]
        for thm in filtered
    }
    pool_sizes = {tid: len(pool) for tid, pool in per_theorem_pools.items()}
    print(
        f"[sanity] {len(filtered)} theorems, "
        f"{len(lemma_pool)} total lemmas ({pool_sizes})",
        file=sys.stderr,
    )

    # Write filtered theorems to disk so run_baseline can load them.
    theorems_json = output_dir / "theorems_sanity.json"
    _write_theorems_json(filtered, lake_project, imports, theorems_json)

    # -- Condition A: no hints ------------------------------------------------
    baseline_dir = output_dir / "without_lemmas"
    run_baseline(
        theorems_path=theorems_json,
        output_dir=baseline_dir,
        limit=None,
        force=force,
        llm_model=llm_model,
        max_attempts=max_attempts,
        num_workers=num_workers,
    )
    baseline_ok = _load_baseline_ok(baseline_dir)

    # -- Condition B: with lemma library -------------------------------------
    with_dir = output_dir / "with_lemmas"
    llm = LLM(model=llm_model, cache_dir=with_dir / "cache")
    round_results: dict[str, RoundResult] = prove_round(
        filtered, lemma_pool, llm, lake_project, imports,
        max_attempts, with_dir, num_workers,
        retriever=retriever, top_k=top_k,
        per_theorem_pools=per_theorem_pools,
    )
    with_lemma_ok = {tid: r.ok for tid, r in round_results.items()}

    # -- Comparison -----------------------------------------------------------
    comparison = build_comparison(baseline_ok, with_lemma_ok, len(lemma_pool))
    comp_path = output_dir / "comparison.json"
    comp_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2))

    wo = comparison["without_lemmas"]
    wl = comparison["with_lemmas"]
    total = comparison["total_theorems"]
    print(f"[sanity] without lemmas : {wo['solved']}/{total} solved", file=sys.stderr)
    print(f"[sanity]  with  lemmas  : {wl['solved']}/{total} solved", file=sys.stderr)
    print(f"[sanity] comparison     -> {comp_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Prove theorems with and without the learned lemma library."
    )
    p.add_argument("--theorems", type=Path, default=_DEFAULT_THEOREMS,
                   metavar="PATH", help="theorems.json input")
    p.add_argument("--lemmas", type=Path, default=_DEFAULT_LEMMAS,
                   metavar="PATH", help="Lemmas.lean with pre-learned hints")
    p.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT,
                   metavar="DIR", help="directory for all outputs")
    p.add_argument("--model", default="gpt-5.2",
                   help="LLM model identifier")
    p.add_argument("--max-attempts", type=int, default=3,
                   help="fix-loop budget per theorem per condition (default: 3)")
    p.add_argument("--workers", type=int, default=1,
                   help="parallel workers (default: 1)")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing results")
    p.add_argument("--theorem-ids", nargs="+", default=None,
                   metavar="ID", help="run only these theorem IDs (e.g. prop_29 prop_36); "
                                      "default: all theorems covered in Lemmas.lean")
    p.add_argument("--retriever", choices=["none", "byt5"], default="none",
                   help="retriever to use for condition B (default: none = pass all lemmas)")
    p.add_argument("--top-k", type=int, default=None, metavar="K",
                   help="retrieve top-K lemmas per theorem (required when --retriever byt5)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    retriever: Retriever | None = None
    if args.retriever == "byt5":
        if args.top_k is None:
            import sys
            print("[sanity] --top-k is required when --retriever byt5", file=sys.stderr)
            sys.exit(1)
        retriever = ByT5Retriever()

    run(
        theorems_path=args.theorems,
        lemmas_path=args.lemmas,
        output_dir=args.output_dir,
        llm_model=args.model,
        max_attempts=args.max_attempts,
        num_workers=args.workers,
        force=args.force,
        theorem_ids=args.theorem_ids,
        retriever=retriever,
        top_k=args.top_k,
    )
