"""Stage 3 of Experiment B — solo study (study b).

For each theorem T in the hard set, selects up to ``num_lemmas`` candidate
lemmas whose ``num_hyps`` equals ``num_hyps_filter`` (both parameters are
optional; omitting them runs all candidates). All selected lemmas are injected
as admitted hints (``solo_hint_0``, ``solo_hint_1``, …) in a single fix-loop
prover run. Records whether the theorem is closed.

Outputs (under ``output_dir``):
    03_solo.json
"""
from __future__ import annotations

import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

from exp.count_hyps import proof_effort as _count_hyps

from exp.lib.corpus import load_candidates, load_theorems, CandidateSet, Theorem
from exp.lib.lean_check import check_proof
from exp.lib.llm import LLM
from exp.lib.prover import SYSTEM_PROMPT, Attempt, parse_proof_response

SOLO_JSON = "03_solo.json"
CACHE_SUBDIR = "cache"

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_SOLO_TEMPLATE = (_PROMPTS_DIR / "solo.md").read_text()
_SOLO_FIX_TEMPLATE = (_PROMPTS_DIR / "solo_fix.md").read_text()


@dataclass
class SoloResult:
    hint_statements: list[str]
    ok: bool
    attempts: list[Attempt] = field(default_factory=list)


def _build_hint_preamble(hint_stmts: list[str]) -> str:
    return "\n".join(
        f"theorem solo_hint_{i} {stmt} := by admit"
        for i, stmt in enumerate(hint_stmts)
    )


def _build_hint_block(hint_stmts: list[str]) -> str:
    return "\n".join(
        f"    theorem solo_hint_{i} {stmt} := by admit"
        for i, stmt in enumerate(hint_stmts)
    )


def _render_solo(thm: Theorem, imports: list[str], hint_stmts: list[str]) -> str:
    return (
        _SOLO_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<hints>>", _build_hint_block(hint_stmts))
    )


def _render_solo_fix(thm: Theorem, imports: list[str], hint_stmts: list[str], last: Attempt) -> str:
    indented_body = "\n".join("  " + l for l in last.proof_body.splitlines() or [""])
    return (
        _SOLO_FIX_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<proof_body>>", indented_body)
        .replace("<<error>>", last.error_text)
        .replace("<<hints>>", _build_hint_block(hint_stmts))
    )


def _run_solo_loop(
    thm: Theorem,
    hint_stmts: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
) -> SoloResult:
    preamble = _build_hint_preamble(hint_stmts)
    attempts: list[Attempt] = []

    for i in range(max_attempts):
        if i == 0:
            user_prompt = _render_solo(thm, imports, hint_stmts)
        else:
            user_prompt = _render_solo_fix(thm, imports, hint_stmts, attempts[-1])

        resp = llm.chat(SYSTEM_PROMPT, user_prompt)
        proof_body = parse_proof_response(resp.text)

        check = check_proof(
            thm.statement_text,
            proof_body,
            lake_project=lake_project,
            imports=imports,
            decl_name=f"expB_solo_{thm.theorem_id}",
            preamble=preamble,
        )
        attempts.append(Attempt(proof_body=proof_body, ok=check.ok, error_text=check.error_text))

        if check.ok:
            return SoloResult(hint_statements=hint_stmts, ok=True, attempts=attempts)

    return SoloResult(hint_statements=hint_stmts, ok=False, attempts=attempts)


def _select_candidates(
    candidates: list[str],
    num_hyps_filter: int | None,
    num_lemmas: int | None,
    rng: random.Random,
) -> list[str]:
    """Filter by num_hyps, then sample up to num_lemmas. Returns statement strings."""
    filtered = candidates

    if num_hyps_filter is not None:
        filtered = [s for s in filtered if _count_hyps(s) == num_hyps_filter]

    if num_lemmas is not None and len(filtered) > num_lemmas:
        filtered = rng.sample(filtered, num_lemmas)

    return filtered


def _solo_record(result: SoloResult) -> dict:
    return {
        "hint_statements": result.hint_statements,
        "ok": result.ok,
        "attempts": [asdict(a) for a in result.attempts],
    }


def _solo_one(
    thm: Theorem,
    selected: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    num_hyps_filter: int | None = None,
) -> tuple[str, dict]:
    print(
        f"[solo] {thm.theorem_id} ({len(selected)} hint(s)"
        + (f", num_hyps={num_hyps_filter}" if num_hyps_filter is not None else "")
        + ")",
        file=sys.stderr,
    )
    result = _run_solo_loop(
        thm, selected, llm,
        lake_project=lake_project,
        imports=imports,
        max_attempts=max_attempts,
    )
    status = "ok" if result.ok else "FAIL"
    print(
        f"  -> {status} after {len(result.attempts)} attempt(s) with {len(selected)} hint(s)",
        file=sys.stderr,
    )
    return thm.theorem_id, _solo_record(result)


def run_solo(
    *,
    hard_set_path: Path,
    candidates_path: Path,
    output_dir: Path,
    force: bool,
    llm_model: str,
    max_attempts: int,
    num_hyps_filter: int | None = None,
    num_lemmas: int | None = None,
    seed: int = 0,
    num_workers: int = 1,
    lake_project_override: Path | None = None,
    imports_override: list[str] | None = None,
) -> None:
    output_dir = Path(output_dir)
    solo_path = output_dir / SOLO_JSON

    if solo_path.exists() and not force:
        print(f"[skip] {solo_path} exists (use --force to overwrite)", file=sys.stderr)
        return

    tset = load_theorems(Path(hard_set_path))
    lake_project = Path(lake_project_override or tset.lake_project)
    imports = list(imports_override or tset.imports or [])

    if not lake_project or not imports:
        raise ValueError(
            "lake_project and imports are required: set them in the hard-set JSON "
            "or pass --lake-project / --imports"
        )

    cset: CandidateSet = load_candidates(Path(candidates_path))
    llm = LLM(model=llm_model, cache_dir=output_dir / CACHE_SUBDIR)
    rng = random.Random(seed)

    # Candidate selection is sequential to preserve rng ordering.
    work_items: list[tuple[Theorem, list[str]]] = []
    skipped = 0

    for thm in tset.theorems:
        candidates = cset.entries.get(thm.theorem_id)
        if not candidates:
            print(f"[skip] {thm.theorem_id}: no candidates", file=sys.stderr)
            skipped += 1
            continue
        selected = _select_candidates(candidates, num_hyps_filter, num_lemmas, rng)
        if not selected:
            print(
                f"[skip] {thm.theorem_id}: no candidates match num_hyps={num_hyps_filter}",
                file=sys.stderr,
            )
            skipped += 1
            continue
        work_items.append((thm, selected))

    results: dict[str, dict] = {}

    if num_workers > 1:
        results_map: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(
                    _solo_one, thm, selected, llm, lake_project, imports, max_attempts, num_hyps_filter
                ): thm
                for thm, selected in work_items
            }
            for fut in as_completed(futures):
                tid, record = fut.result()
                results_map[tid] = record
        for thm, _ in work_items:
            results[thm.theorem_id] = results_map[thm.theorem_id]
    else:
        for thm, selected in work_items:
            tid, record = _solo_one(thm, selected, llm, lake_project, imports, max_attempts, num_hyps_filter)
            results[tid] = record

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "lake_project": str(lake_project),
        "imports": imports,
        "num_hyps_filter": num_hyps_filter,
        "num_lemmas": num_lemmas,
        "results": results,
    }
    solo_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
    print(
        f"[done] {len(results)} theorems processed, {skipped} skipped -> {solo_path}",
        file=sys.stderr,
    )
