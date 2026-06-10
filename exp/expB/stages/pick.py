"""Stage 2 of Experiment B — pick study (study a).

For each theorem in the hard set, presents the LLM with the theorem plus a
menu of candidate lemma statements (admitted in scope, labeled L0..Ln-1).
Runs the fix-loop prover: the first attempt uses the pick prompt (with the
menu); subsequent fix attempts use the standard fix prompt (the LLM has
already seen the candidates in the prior proof body and error context).

Records which candidate indices the LLM reports using, and whether the
theorem was ultimately closed — this is the extra success signal alongside
the preference signal.

Outputs (under ``output_dir``):
    02_picks.json
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

from exp.lib.corpus import CandidateSet, load_candidates, load_theorems
from exp.lib.lean_check import check_proof
from exp.lib.llm import LLM
from exp.lib.prover import (
    SYSTEM_PROMPT,
    Attempt,
    parse_proof_response,
    render_fix,
)

PICKS_JSON = "02_picks.json"
CACHE_SUBDIR = "cache"

_PICKS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_PICK_TEMPLATE = (_PICKS_DIR / "pick.md").read_text()
_FIX_TEMPLATE = (_PICKS_DIR / "fix.md").read_text()

_USED_LEMMAS_RE = re.compile(r"<used_lemmas>(.*?)</used_lemmas>", re.DOTALL)


@dataclass
class PickResult:
    all_candidates: list[str]
    used_indices: list[int]
    used_statements: list[str]
    proof_body: str
    ok: bool
    attempts: list[Attempt] = field(default_factory=list)


def _build_candidate_menu(candidates: list[str]) -> str:
    return "\n".join(f"[L{i}] {stmt}" for i, stmt in enumerate(candidates))


def _build_preamble(candidates: list[str]) -> str:
    return "\n".join(
        f"theorem L{i} {stmt} := by admit" for i, stmt in enumerate(candidates)
    )


def _render_pick(thm, imports: list[str], candidates: list[str]) -> str:
    menu = _build_candidate_menu(candidates)
    return (
        _PICK_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<candidates>>", menu)
    )


def _parse_used_lemmas(text: str, n_candidates: int) -> list[int]:
    m = _USED_LEMMAS_RE.search(text)
    if not m:
        return []
    raw = m.group(1).strip().lower()
    if raw == "none" or not raw:
        return []
    indices: list[int] = []
    for token in re.split(r"[,\s]+", raw):
        token = token.strip()
        if not token:
            continue
        try:
            idx = int(token)
        except ValueError:
            continue
        if 0 <= idx < n_candidates:
            indices.append(idx)
    return sorted(set(indices))


def _run_pick_loop(
    thm,
    candidates: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
) -> PickResult:
    preamble = _build_preamble(candidates)
    attempts: list[Attempt] = []
    used_indices: list[int] = []

    for i in range(max_attempts):
        if i == 0:
            user_prompt = _render_pick(thm, imports, candidates)
        else:
            user_prompt = render_fix(thm, imports, attempts[-1], _FIX_TEMPLATE)

        resp = llm.chat(SYSTEM_PROMPT, user_prompt)
        proof_body = parse_proof_response(resp.text)

        if i == 0:
            used_indices = _parse_used_lemmas(resp.text, len(candidates))

        check = check_proof(
            thm.statement_text,
            proof_body,
            lake_project=lake_project,
            imports=imports,
            decl_name=f"expB_pick_{thm.theorem_id}",
            preamble=preamble,
        )
        attempts.append(Attempt(proof_body=proof_body, ok=check.ok, error_text=check.error_text))

        if check.ok:
            return PickResult(
                all_candidates=candidates,
                used_indices=used_indices,
                used_statements=[candidates[i] for i in used_indices],
                proof_body=proof_body,
                ok=True,
                attempts=attempts,
            )

    last_proof = attempts[-1].proof_body if attempts else ""
    return PickResult(
        all_candidates=candidates,
        used_indices=used_indices,
        used_statements=[candidates[i] for i in used_indices],
        proof_body=last_proof,
        ok=False,
        attempts=attempts,
    )


def _pick_record(result: PickResult) -> dict:
    return {
        "all_candidates": result.all_candidates,
        "used_indices": result.used_indices,
        "used_statements": result.used_statements,
        "proof_body": result.proof_body,
        "ok": result.ok,
        "attempts": [asdict(a) for a in result.attempts],
    }


def _pick_one(
    thm,
    cset: CandidateSet,
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
) -> tuple[str, dict | None]:
    candidates = cset.entries.get(thm.theorem_id)
    if not candidates:
        print(f"[skip] {thm.theorem_id}: no candidates", file=sys.stderr)
        return thm.theorem_id, None
    print(f"[pick] {thm.theorem_id} ({len(candidates)} candidates)", file=sys.stderr)
    result = _run_pick_loop(
        thm, candidates, llm,
        lake_project=lake_project,
        imports=imports,
        max_attempts=max_attempts,
    )
    status = "ok" if result.ok else "FAIL"
    picked = result.used_indices if result.used_indices else "none"
    print(f"  -> {status} after {len(result.attempts)} attempt(s), used={picked}", file=sys.stderr)
    return thm.theorem_id, _pick_record(result)


def run_pick(
    *,
    hard_set_path: Path,
    candidates_path: Path,
    output_dir: Path,
    force: bool,
    llm_model: str,
    max_attempts: int,
    num_workers: int = 1,
    lake_project_override: Path | None = None,
    imports_override: list[str] | None = None,
) -> None:
    output_dir = Path(output_dir)
    picks_path = output_dir / PICKS_JSON

    if picks_path.exists() and not force:
        print(f"[skip] {picks_path} exists (use --force to overwrite)", file=sys.stderr)
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

    results: dict[str, dict] = {}
    skipped = 0

    if num_workers > 1:
        results_map: dict[str, dict | None] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(_pick_one, thm, cset, llm, lake_project, imports, max_attempts): thm
                for thm in tset.theorems
            }
            for fut in as_completed(futures):
                tid, record = fut.result()
                results_map[tid] = record
        for thm in tset.theorems:
            record = results_map.get(thm.theorem_id)
            if record is None:
                skipped += 1
            else:
                results[thm.theorem_id] = record
    else:
        for thm in tset.theorems:
            tid, record = _pick_one(thm, cset, llm, lake_project, imports, max_attempts)
            if record is None:
                skipped += 1
            else:
                results[tid] = record

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "lake_project": str(lake_project),
        "imports": imports,
        "results": results,
    }
    picks_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
    print(
        f"[done] {len(results)} theorems processed, {skipped} skipped -> {picks_path}",
        file=sys.stderr,
    )
