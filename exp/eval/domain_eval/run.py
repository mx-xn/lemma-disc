"""CLI for domain-scoped train/test lemma evaluation.

Usage:
    python -m exp.eval.domain_eval.run split  [options]
    python -m exp.eval.domain_eval.run learn  [options]
    python -m exp.eval.domain_eval.run eval   [options]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .stages.split import run_split
from .stages.learn import run_learn
from .stages.eval import run_eval

DOMAIN_EVAL_ROOT = Path(__file__).resolve().parent
DEFAULT_THEOREMS = DOMAIN_EVAL_ROOT / "input" / "domain_theorems.json"
DEFAULT_OUTPUT_DIR = DOMAIN_EVAL_ROOT / "output"


def _split_imports(s: str | None) -> list[str] | None:
    if s is None:
        return None
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def _add_split_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("split", help="partition TheoremSet into train/test")
    p.add_argument("--theorems", type=Path, default=DEFAULT_THEOREMS)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--train-frac", type=float, default=None,
                   help="fraction of theorems for training (default: 0.7)")
    g.add_argument("--train-n", type=int, default=None,
                   help="absolute number of theorems for training")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--force", action="store_true")


def _add_learn_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("learn", help="learn lemma library from training split")
    p.add_argument("--method", choices=["pipeline", "llm"], default="pipeline")
    p.add_argument("--train", type=Path, default=DEFAULT_OUTPUT_DIR / "train.json",
                   dest="train_path")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--lake-project", type=Path, default=None)
    p.add_argument("--imports", type=str, default=None,
                   help="comma-separated imports (overrides train.json)")
    p.add_argument("--skip-fix", action="store_true",
                   help="skip lemma_fixer (for testing)")
    p.add_argument("--force", action="store_true")
    # pipeline only
    p.add_argument("--trace", type=Path, default=None, dest="trace_path",
                   help="trace.json from digestion (pipeline only)")
    p.add_argument("--skip-pipeline", action="store_true",
                   help="skip run_full.sh; write empty raw_lemmas.json")
    # llm only
    p.add_argument("--lean-file", type=Path, default=None,
                   help="Lean source with training proofs only (llm only)")
    p.add_argument("--model", default="gpt-5.4-mini", dest="llm_model")


def _add_eval_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("eval", help="prove test split (baseline or lemma-augmented)")
    p.add_argument("--theorems", type=Path, default=DEFAULT_OUTPUT_DIR / "test.json")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR / "eval")
    p.add_argument("--lemmas", type=Path, default=None, dest="lemmas_path",
                   help="learned_lemmas.json; if absent runs baseline")
    p.add_argument("--top-k", type=int, default=None,
                   help="retrieve top-K lemmas per theorem via ByT5Retriever")
    p.add_argument("--model", default="gpt-5.4-mini", dest="llm_model")
    p.add_argument("--max-attempts", type=int, default=3)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--lake-project", type=Path, default=None)
    p.add_argument("--imports", type=str, default=None,
                   help="comma-separated imports (overrides test.json)")
    p.add_argument("--force", action="store_true")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="exp.eval.domain_eval.run")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_split_parser(sub)
    _add_learn_parser(sub)
    _add_eval_parser(sub)
    args = parser.parse_args(argv)

    if args.cmd == "split":
        train_frac = args.train_frac if args.train_frac is not None else (
            0.7 if args.train_n is None else None
        )
        run_split(
            theorems_path=args.theorems,
            output_dir=args.output_dir,
            train_frac=train_frac,
            train_n=args.train_n,
            seed=args.seed,
            force=args.force,
        )
        return 0

    if args.cmd == "learn":
        run_learn(
            method=args.method,
            train_path=args.train_path,
            output_dir=args.output_dir,
            lake_project_override=args.lake_project,
            imports_override=_split_imports(args.imports),
            trace_path=args.trace_path,
            skip_pipeline=args.skip_pipeline,
            lean_file=args.lean_file,
            llm_model=args.llm_model,
            skip_fix=args.skip_fix,
            force=args.force,
        )
        return 0

    if args.cmd == "eval":
        run_eval(
            theorems_path=args.theorems,
            output_dir=args.output_dir,
            lemmas_path=args.lemmas_path,
            top_k=args.top_k,
            llm_model=args.llm_model,
            max_attempts=args.max_attempts,
            num_workers=args.workers,
            lake_project_override=args.lake_project,
            imports_override=_split_imports(args.imports),
            force=args.force,
        )
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
