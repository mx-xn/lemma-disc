"""CLI orchestrator for Experiment B.

Usage:
    python -m exp.expB.run baseline [--theorems P] [--output-dir P]
                                    [--limit N] [--force]
                                    [--model M] [--max-attempts K]
                                    [--lake-project P] [--imports X,Y,Z]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .stages.aggregate import run_aggregate
from .stages.baseline import run_baseline
from .stages.pick import run_pick
from .stages.solo import run_solo

EXPB_ROOT = Path(__file__).resolve().parent
DEFAULT_THEOREMS = EXPB_ROOT / "input" / "theorems.json"
DEFAULT_OUTPUT_DIR = EXPB_ROOT / "output"


def _split_imports(s: str | None) -> list[str] | None:
    if s is None:
        return None
    return [tok.strip() for tok in s.split(",") if tok.strip()]


def _add_baseline_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("baseline", help="run stage 1: baseline prover -> hard set")
    p.add_argument("--theorems", type=Path, default=DEFAULT_THEOREMS,
                   help=f"input theorems JSON (default: {DEFAULT_THEOREMS})")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--limit", type=int, default=None,
                   help="stop once N hard theorems have been found")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing 01_baseline.json")
    p.add_argument("--model", default="gpt-5.4-mini",
                   help="LLM model id (default: gpt-5.4-mini)")
    p.add_argument("--max-attempts", type=int, default=3,
                   help="LLM calls per theorem (default: 3 = 1 sample + 2 fixes)")
    p.add_argument("--workers", type=int, default=1,
                   help="number of parallel prove workers (default: 1)")
    p.add_argument("--lake-project", type=Path, default=None,
                   help="path to the Lake project (overrides input file)")
    p.add_argument("--imports", type=str, default=None,
                   help="comma-separated imports (overrides input file)")


def _add_pick_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("pick", help="run stage 2: pick study (study a) -> 02_picks.json")
    p.add_argument("--hard-set", type=Path, default=DEFAULT_OUTPUT_DIR / "01_hard_set.json",
                   help="hard-set JSON produced by stage 1 (default: output/01_hard_set.json)")
    p.add_argument("--candidates", type=Path, default=EXPB_ROOT / "input" / "candidates.json",
                   help="candidates JSON: {theorem_id: [stmt, ...]} (default: input/candidates.json)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing 02_picks.json")
    p.add_argument("--model", default="gpt-5.4-mini",
                   help="LLM model id (default: gpt-5.4-mini)")
    p.add_argument("--max-attempts", type=int, default=3,
                   help="LLM calls per theorem (default: 3 = 1 pick + 2 fix loops)")
    p.add_argument("--workers", type=int, default=1,
                   help="number of parallel prove workers (default: 1)")
    p.add_argument("--lake-project", type=Path, default=None,
                   help="path to the Lake project (overrides hard-set file)")
    p.add_argument("--imports", type=str, default=None,
                   help="comma-separated imports (overrides hard-set file)")


def _add_solo_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("solo", help="run stage 3: solo study (study b) -> 03_solo.json")
    p.add_argument("--hard-set", type=Path, default=DEFAULT_OUTPUT_DIR / "01_hard_set.json",
                   help="hard-set JSON produced by stage 1 (default: output/01_hard_set.json)")
    p.add_argument("--candidates", type=Path, default=EXPB_ROOT / "input" / "candidates.json",
                   help="candidates JSON: {theorem_id: [stmt, ...]} (default: input/candidates.json)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing 03_solo.json")
    p.add_argument("--model", default="gpt-5.4-mini",
                   help="LLM model id (default: gpt-5.4-mini)")
    p.add_argument("--max-attempts", type=int, default=3,
                   help="LLM calls per (theorem, lemma) pair (default: 3 = 1 sample + 2 fixes)")
    p.add_argument("--workers", type=int, default=1,
                   help="number of parallel prove workers (default: 1)")
    p.add_argument("--num-hyps", type=int, default=None,
                   help="only run lemmas with exactly this many hypotheses")
    p.add_argument("--num-lemmas", type=int, default=None,
                   help="randomly sample up to this many lemmas per theorem (after --num-hyps filter)")
    p.add_argument("--seed", type=int, default=0,
                   help="random seed for lemma sampling (default: 0)")
    p.add_argument("--lake-project", type=Path, default=None,
                   help="path to the Lake project (overrides hard-set file)")
    p.add_argument("--imports", type=str, default=None,
                   help="comma-separated imports (overrides hard-set file)")


def _add_aggregate_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("aggregate", help="run stage 4: aggregate -> 04_csv/")
    p.add_argument("--picks", type=Path, default=DEFAULT_OUTPUT_DIR / "02_picks.json",
                   help="picks JSON produced by stage 2 (default: output/02_picks.json)")
    p.add_argument("--solo", type=Path, default=DEFAULT_OUTPUT_DIR / "03_solo.json",
                   help="solo JSON produced by stage 3 (default: output/03_solo.json)")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing 04_csv/ contents")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="exp.expB.run")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_baseline_parser(sub)
    _add_pick_parser(sub)
    _add_solo_parser(sub)
    _add_aggregate_parser(sub)
    args = parser.parse_args(argv)

    if args.cmd == "baseline":
        run_baseline(
            theorems_path=args.theorems,
            output_dir=args.output_dir,
            limit=args.limit,
            force=args.force,
            llm_model=args.model,
            max_attempts=args.max_attempts,
            num_workers=args.workers,
            lake_project_override=args.lake_project,
            imports_override=_split_imports(args.imports),
        )
        return 0

    if args.cmd == "pick":
        run_pick(
            hard_set_path=args.hard_set,
            candidates_path=args.candidates,
            output_dir=args.output_dir,
            force=args.force,
            llm_model=args.model,
            max_attempts=args.max_attempts,
            num_workers=args.workers,
            lake_project_override=args.lake_project,
            imports_override=_split_imports(args.imports),
        )
        return 0

    if args.cmd == "solo":
        run_solo(
            hard_set_path=args.hard_set,
            candidates_path=args.candidates,
            output_dir=args.output_dir,
            force=args.force,
            llm_model=args.model,
            max_attempts=args.max_attempts,
            num_hyps_filter=args.num_hyps,
            num_lemmas=args.num_lemmas,
            seed=args.seed,
            num_workers=args.workers,
            lake_project_override=args.lake_project,
            imports_override=_split_imports(args.imports),
        )
        return 0

    if args.cmd == "aggregate":
        run_aggregate(
            picks_path=args.picks,
            solo_path=args.solo,
            output_dir=args.output_dir,
            force=args.force,
        )
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
