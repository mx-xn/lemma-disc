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


def _write_artifacts(
    output_dir: Path,
    lake_project: Path,
    imports: list[str],
    rows: list[tuple[Theorem, ProverResult]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline = {
        "lake_project": str(lake_project),
        "imports": imports,
        "results": {t.theorem_id: _theorem_record(t, r) for t, r in rows},
    }
    (output_dir / BASELINE_JSON).write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2)
    )

    hard = {
        "lake_project": str(lake_project),
        "imports": imports,
        "theorems": [_hard_theorem_record(t, r) for t, r in rows if not r.ok],
    }
    (output_dir / HARD_SET_JSON).write_text(
        json.dumps(hard, ensure_ascii=False, indent=2)
    )


def _prove_one(
    thm: Theorem,
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
) -> tuple[Theorem, ProverResult]:
    print(f"[prove] {thm.theorem_id}", file=sys.stderr)
    result = prove(
        thm, llm,
        lake_project=lake_project,
        imports=imports,
        max_attempts=max_attempts,
        baseline_template=_BASELINE_TEMPLATE,
        fix_template=_FIX_TEMPLATE,
    )
    status = "ok" if result.ok else "HARD"
    print(f"  -> {thm.theorem_id}: {status} after {len(result.attempts)} attempt(s)", file=sys.stderr)
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
    lake_project_override: Path | None = None,
    imports_override: list[str] | None = None,
) -> None:
    output_dir = Path(output_dir)
    baseline_path = output_dir / BASELINE_JSON

    if baseline_path.exists() and not force:
        print(f"[skip] {baseline_path} exists (use --force to overwrite)", file=sys.stderr)
        return

    tset = load_theorems(Path(theorems_path))
    lake_project, imports = _resolve_setup(tset, lake_project_override, imports_override)

    llm = LLM(model=llm_model, cache_dir=output_dir / CACHE_SUBDIR)

    rows: list[tuple[Theorem, ProverResult]] = []

    if num_workers > 1:
        results_map: dict[str, tuple[Theorem, ProverResult]] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(_prove_one, thm, llm, lake_project, imports, max_attempts): thm
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
            thm, result = _prove_one(thm, llm, lake_project, imports, max_attempts)
            rows.append((thm, result))
            if not result.ok:
                hard_count += 1
                if limit is not None and hard_count >= limit:
                    print(f"[stop] reached --limit {limit}", file=sys.stderr)
                    break

    _write_artifacts(output_dir, lake_project, imports, rows)
    n_hard = sum(1 for _, r in rows if not r.ok)
    print(
        f"[done] {len(rows)} attempted, {n_hard} hard -> "
        f"{output_dir / BASELINE_JSON}, {output_dir / HARD_SET_JSON}",
        file=sys.stderr,
    )
