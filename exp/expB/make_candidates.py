#!/usr/bin/env python3
"""Build exp/expB/input/candidates.json for stages 2 and 3.

For each theorem in 01_hard_set.json, reads data/<theorem_id>_lemmas.json,
computes proof_effort for every lemma statement, samples up to 50 with
variety across the effort range (sorted-linspace), then shuffles and writes
candidates.json in the format expected by load_candidates().
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from exp.count_hyps import proof_effort

REPO_ROOT = Path(__file__).resolve().parents[2]
HARD_SET = REPO_ROOT / "exp/expB/output/01_hard_set.json"
DATA_DIR = REPO_ROOT / "data"
OUT_PATH = REPO_ROOT / "exp/expB/input/candidates.json"

SAMPLE_SIZE = 20
SEED = 42


def load_statements(theorem_id: str) -> list[str]:
    path = DATA_DIR / f"{theorem_id}_lemmas.json"
    data = json.loads(path.read_text())
    lemmas = data["lemmas"] if isinstance(data, dict) else data
    return [lem["statement"] for lem in lemmas if lem.get("statement")]


def linspace_sample(items: list, k: int) -> list:
    """Pick k items at evenly-spaced indices from a sorted list."""
    n = len(items)
    if n <= k:
        return list(items)
    indices = {round(i * (n - 1) / (k - 1)) for i in range(k)}
    return [items[i] for i in sorted(indices)]


def sample_with_variety(statements: list[str], k: int, rng: random.Random) -> list[str]:
    scored = sorted(statements, key=proof_effort)
    sampled = linspace_sample(scored, k)
    rng.shuffle(sampled)
    return sampled


def main() -> None:
    hard_set = json.loads(HARD_SET.read_text())
    theorem_ids = [t["theorem_id"] for t in hard_set["theorems"]]

    rng = random.Random(SEED)
    candidates: dict[str, list[str]] = {}

    for tid in theorem_ids:
        statements = load_statements(tid)
        sampled = sample_with_variety(statements, SAMPLE_SIZE, rng)
        candidates[tid] = sampled
        print(f"{tid}: {len(statements)} lemmas → {len(sampled)} sampled")

    OUT_PATH.write_text(json.dumps(candidates, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
