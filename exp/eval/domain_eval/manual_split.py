"""Split a TheoremSet into train/test by explicit theorem ID lists.

Standalone authoring tool — not part of the run.py pipeline.
Run once to produce train.json and test.json, then feed them to run.py learn/eval.

Usage:
    python -m exp.eval.domain_eval.manual_split \\
        --source  input/sorts_mathlib_theorems.json \\
        --train-ids "Sorted.nlt,Sorted.sub,Permut.refl" \\
        --output-dir output/sorts_mathlib \\
        [--clear-local-ctx] [--force]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

from exp.lib.corpus import load_theorems
from .stages.split import _thm_dict


def run_manual_split(
    source_path: Path,
    train_ids: list[str],
    output_dir: Path,
    force: bool,
) -> None:
    train_path = output_dir / "train.json"
    test_path = output_dir / "test.json"

    if not force:
        for p in (train_path, test_path):
            if p.exists():
                print(f"[skip] {p} exists (use --force to overwrite)", file=sys.stderr)
                return

    tset = load_theorems(source_path)
    train_id_set = set(train_ids)

    unknown = train_id_set - {t.theorem_id for t in tset.theorems}
    if unknown:
        raise ValueError(f"--train-ids not found in source: {sorted(unknown)}")

    train_theorems = [t for t in tset.theorems if t.theorem_id in train_id_set]
    test_theorems = [t for t in tset.theorems if t.theorem_id not in train_id_set]

    base = {
        "lake_project": str(tset.lake_project) if tset.lake_project else None,
        "imports": list(tset.imports) if tset.imports else [],
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    train_path.write_text(json.dumps(
        {**base, "theorems": [_thm_dict(t) for t in train_theorems]},
        ensure_ascii=False, indent=2,
    ))
    test_path.write_text(json.dumps(
        {**base, "theorems": [_thm_dict(t) for t in test_theorems]},
        ensure_ascii=False, indent=2,
    ))

    print(
        f"[manual_split] {len(tset.theorems)} total → "
        f"{len(train_theorems)} train, {len(test_theorems)} test",
        file=sys.stderr,
    )
    print(f"  train -> {train_path}", file=sys.stderr)
    print(f"  test  -> {test_path}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    _DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"

    p = argparse.ArgumentParser(
        prog="manual_split",
        description="Split a TheoremSet by explicit theorem ID lists.",
    )
    p.add_argument("--source", type=Path, required=True,
                   help="TheoremSet JSON to split (e.g. input/sorts_mathlib_theorems.json)")
    p.add_argument("--train-ids", type=str, required=True,
                   help="comma-separated theorem_id values for the training split")
    p.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--force", action="store_true",
                   help="overwrite train.json/test.json if they exist")
    args = p.parse_args(argv)

    train_ids = [t.strip() for t in args.train_ids.split(",") if t.strip()]
    run_manual_split(
        source_path=args.source,
        train_ids=train_ids,
        output_dir=args.output_dir,
        force=args.force,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
