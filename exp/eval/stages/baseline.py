"""Stage 0 of the iterative eval loop — baseline prover (no lemma hints).

Same logic as exp/expB/stages/baseline.py; reads its prompt templates from
exp/eval/prompts/ so it is independent of expB.

Outputs (under ``output_dir``):
    01_baseline.json   — full record for every theorem
    01_hard_set.json   — input-compatible record for the failing subset
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from exp.eval.lib.result_store import load_results_file, merge_results_file
from exp.lib.corpus import Theorem, TheoremSet, load_theorems
from exp.lib.llm import LLM
from exp.lib.prover import ProverResult, prove

BASELINE_JSON = "01_baseline.json"
HARD_SET_JSON = "01_hard_set.json"
CACHE_SUBDIR = "cache"

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_BASELINE_TEMPLATE = (_PROMPTS_DIR / "baseline.md").read_text()
_FIX_TEMPLATE = (_PROMPTS_DIR / "fix.md").read_text()


def _resolve_setup(
    tset: TheoremSet,
    lake_project_override: Path | None,
    imports_override: list[str] | None,
) -> tuple[Path, list[str]]:
    lake_project = lake_project_override or tset.lake_project
    imports = imports_override or tset.imports
    if lake_project is None:
        raise ValueError(
            "lake_project is required: set 'lake_project' in theorems.json "
            "or pass --lake-project"
        )
    if not imports:
        raise ValueError(
            "imports is required: set 'imports' in theorems.json or pass --imports"
        )
    return Path(lake_project), list(imports)


def _theorem_record(thm: Theorem, result: ProverResult) -> dict:
    return {
        "ok": result.ok,
        "attempts": [asdict(a) for a in result.attempts],
        "final_error": result.final_error,
    }


def _hard_theorem_record(thm: Theorem, result: ProverResult) -> dict:
    return {
        "theorem_id": thm.theorem_id,
        "lean_path": thm.lean_path,
        "statement_text": thm.statement_text,
        "final_error": result.final_error,
    }


def _merge_hard_set(
    path: Path,
    lake_project: str,
    imports: list[str],
    rows: list[tuple[Theorem, ProverResult]],
) -> None:
    """Upsert the hard-set file: remove re-evaluated theorem_ids, add failing ones."""
    existing = load_results_file(path)
    if existing.get("lake_project") == lake_project:
        hard_map: dict[str, dict] = {t["theorem_id"]: t for t in existing.get("theorems", [])}
    else:
        hard_map = {}

    for thm, _ in rows:
        hard_map.pop(thm.theorem_id, None)
    for thm, result in rows:
        if not result.ok:
            hard_map[thm.theorem_id] = _hard_theorem_record(thm, result)

    path.write_text(
        json.dumps(
            {"lake_project": lake_project, "imports": imports, "theorems": list(hard_map.values())},
            ensure_ascii=False,
            indent=2,
        )
    )


def _write_artifacts(
    output_dir: Path,
    lake_project: Path,
    imports: list[str],
    rows: list[tuple[Theorem, ProverResult]],
    *,
    force: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lp = str(lake_project)

    merge_results_file(
        output_dir / BASELINE_JSON,
        lp,
        imports,
        {t.theorem_id: _theorem_record(t, r) for t, r in rows},
        force=force,
    )
    _merge_hard_set(output_dir / HARD_SET_JSON, lp, imports, rows)


def _prove_one(
    thm: Theorem,
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    lean_scratch_dir: Path | None = None,
    num_samples: int = 1,
) -> tuple[Theorem, ProverResult]:
    print(f"[prove] {thm.theorem_id} ({num_samples} sample(s))", file=sys.stderr)
    results = [
        prove(
            thm, llm,
            lake_project=lake_project,
            imports=imports,
            max_attempts=max_attempts,
            baseline_template=_BASELINE_TEMPLATE,
            fix_template=_FIX_TEMPLATE,
            lean_scratch_dir=lean_scratch_dir,
        )
        for _ in range(num_samples)
    ]
    # pass@M: succeed if any sample succeeded
    winning = next((r for r in results if r.ok), None)
    result = winning if winning is not None else results[-1]
    n_ok = sum(1 for r in results if r.ok)
    status = "ok" if result.ok else "HARD"
    print(f"  -> {thm.theorem_id}: {status} ({n_ok}/{num_samples} samples ok)", file=sys.stderr)
    return thm, result


def run_baseline(
    *,
    theorems_path: Path,
    output_dir: Path,
    limit: int | None,
    force: bool,
    llm_model: str,
    max_attempts: int,
    num_workers: int = 1,
    num_samples: int = 1,
    lake_project_override: Path | None = None,
    imports_override: list[str] | None = None,
) -> None:
    output_dir = Path(output_dir)
    tset = load_theorems(Path(theorems_path))
    lake_project, imports = _resolve_setup(tset, lake_project_override, imports_override)

    llm = LLM(model=llm_model, cache_dir=output_dir / CACHE_SUBDIR)
    lean_scratch_dir = output_dir / CACHE_SUBDIR

    rows: list[tuple[Theorem, ProverResult]] = []

    if num_workers > 1:
        results_map: dict[str, tuple[Theorem, ProverResult]] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(
                    _prove_one, thm, llm, lake_project, imports, max_attempts, lean_scratch_dir, num_samples
                ): thm
                for thm in tset.theorems
            }
            for fut in as_completed(futures):
                thm, result = fut.result()
                results_map[thm.theorem_id] = (thm, result)
        rows = [results_map[t.theorem_id] for t in tset.theorems if t.theorem_id in results_map]
        if limit is not None:
            trimmed: list[tuple[Theorem, ProverResult]] = []
            hard_count = 0
            for thm, result in rows:
                trimmed.append((thm, result))
                if not result.ok:
                    hard_count += 1
                    if hard_count >= limit:
                        print(f"[stop] reached --limit {limit}", file=sys.stderr)
                        break
            rows = trimmed
    else:
        hard_count = 0
        for thm in tset.theorems:
            thm, result = _prove_one(thm, llm, lake_project, imports, max_attempts, lean_scratch_dir, num_samples)
            rows.append((thm, result))
            if not result.ok:
                hard_count += 1
                if limit is not None and hard_count >= limit:
                    print(f"[stop] reached --limit {limit}", file=sys.stderr)
                    break

    _write_artifacts(output_dir, lake_project, imports, rows, force=force)
    n_hard = sum(1 for _, r in rows if not r.ok)
    print(
        f"[done] {len(rows)} attempted, {n_hard} hard -> "
        f"{output_dir / BASELINE_JSON}, {output_dir / HARD_SET_JSON}",
        file=sys.stderr,
    )
