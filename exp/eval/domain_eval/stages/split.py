"""Partition a TheoremSet into train and test splits."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from exp.lib.corpus import load_theorems


def run_split(
    theorems_path: Path,
    output_dir: Path,
    train_frac: float | None,
    train_n: int | None,
    seed: int,
    force: bool,
) -> None:
    if (train_frac is None) == (train_n is None):
        raise ValueError("exactly one of train_frac or train_n must be set")

    output_dir = Path(output_dir)
    train_path = output_dir / "train.json"
    test_path = output_dir / "test.json"

    if not force:
        for p in (train_path, test_path):
            if p.exists():
                print(f"[skip] {p} exists (use --force to overwrite)", file=sys.stderr)
                return

    tset = load_theorems(Path(theorems_path))
    theorems = list(tset.theorems)

    rng = random.Random(seed)
    rng.shuffle(theorems)

    k = round(len(theorems) * train_frac) if train_frac is not None else train_n
    k = max(0, min(k, len(theorems)))

    train_theorems = theorems[:k]
    test_theorems = theorems[k:]

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
        f"[split] {len(theorems)} total → {len(train_theorems)} train, "
        f"{len(test_theorems)} test (seed={seed})",
        file=sys.stderr,
    )
    print(f"  train -> {train_path}", file=sys.stderr)
    print(f"  test  -> {test_path}", file=sys.stderr)


def _thm_dict(t) -> dict:
    return {
        "theorem_id": t.theorem_id,
        "lean_path": t.lean_path,
        "statement_text": t.statement_text,
        "local_ctx": t.local_ctx,
    }
