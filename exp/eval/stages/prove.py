"""One proving round for the iterative eval loop.

Like exp/expB/stages/solo.py but:
  - takes a ``lemma_pool`` (list of statement strings) instead of a static
    candidates file
  - stores ``raw_response`` on each Attempt so LemmaRegistry.record_usage can
    parse <used_lemmas> indices across attempts
  - writes prove_results.json in output_dir

``Attempt`` and ``RoundResult`` are defined here (not re-used from exp.lib.prover)
because eval needs the extra ``raw_response`` field in the JSON schema.
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

from exp.eval.lib.retriever import Retriever
from exp.lib.corpus import Theorem
from exp.lib.lean_check import check_proof
from exp.lib.llm import LLM
from exp.lib.prover import SYSTEM_PROMPT, parse_proof_response

PROVE_RESULTS_JSON = "prove_results.json"
CACHE_SUBDIR = "cache"

# Matches lemma_hint_N as a whole token; \b prevents lemma_hint_1 from matching
# inside lemma_hint_10.
_HINT_RE = re.compile(r"\blemma_hint_(\d+)\b")

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_SOLO_TEMPLATE = (_PROMPTS_DIR / "solo.md").read_text()
_SOLO_FIX_TEMPLATE = (_PROMPTS_DIR / "solo_fix.md").read_text()


def _extract_used_indices(proof_body: str, pool_size: int) -> list[int]:
    """Return sorted indices of lemma_hint_N names that appear in proof_body."""
    found = {
        int(m.group(1))
        for m in _HINT_RE.finditer(proof_body)
        if int(m.group(1)) < pool_size
    }
    return sorted(found)


@dataclass
class Attempt:
    proof_body: str
    ok: bool
    error_text: str
    raw_response: str = ""
    used_indices: list[int] = field(default_factory=list)


@dataclass
class RoundResult:
    ok: bool
    attempts: list[Attempt] = field(default_factory=list)
    final_error: str = ""


def _build_hint_preamble(lemma_pool: list[str]) -> str:
    return "\n".join(
        f"theorem lemma_hint_{i} {stmt} := by admit"
        for i, stmt in enumerate(lemma_pool)
    )


def _build_hint_block(lemma_pool: list[str]) -> str:
    return "\n".join(
        f"    theorem lemma_hint_{i} {stmt} := by admit"
        for i, stmt in enumerate(lemma_pool)
    )


def _render_first(thm: Theorem, imports: list[str], lemma_pool: list[str]) -> str:
    return (
        _SOLO_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<hints>>", _build_hint_block(lemma_pool))
    )


def _render_fix(
    thm: Theorem,
    imports: list[str],
    lemma_pool: list[str],
    last: Attempt,
) -> str:
    indented_body = "\n".join("  " + l for l in last.proof_body.splitlines() or [""])
    return (
        _SOLO_FIX_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<proof_body>>", indented_body)
        .replace("<<error>>", last.error_text)
        .replace("<<hints>>", _build_hint_block(lemma_pool))
    )


def _run_prove_loop(
    thm: Theorem,
    lemma_pool: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
) -> RoundResult:
    preamble = _build_hint_preamble(lemma_pool)
    attempts: list[Attempt] = []

    for i in range(max_attempts):
        user_prompt = (
            _render_first(thm, imports, lemma_pool)
            if i == 0
            else _render_fix(thm, imports, lemma_pool, attempts[-1])
        )
        resp = llm.chat(SYSTEM_PROMPT, user_prompt)
        proof_body = parse_proof_response(resp.text)

        check = check_proof(
            thm.statement_text,
            proof_body,
            lake_project=lake_project,
            imports=imports,
            decl_name=f"eval_{thm.theorem_id}",
            preamble=preamble,
        )
        attempts.append(Attempt(
            proof_body=proof_body,
            ok=check.ok,
            error_text=check.error_text,
            raw_response=resp.text,
            used_indices=_extract_used_indices(proof_body, len(lemma_pool)),
        ))
        if check.ok:
            return RoundResult(ok=True, attempts=attempts)

    return RoundResult(
        ok=False,
        attempts=attempts,
        final_error=attempts[-1].error_text if attempts else "",
    )


def _prove_one(
    thm: Theorem,
    lemma_pool: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    retriever: Retriever | None = None,
    top_k: int | None = None,
    per_theorem_pools: dict[str, list[str]] | None = None,
) -> tuple[str, RoundResult]:
    pool = per_theorem_pools[thm.theorem_id] if per_theorem_pools else lemma_pool
    effective_pool = (
        retriever.retrieve(thm.statement_text, pool, top_k)
        if retriever is not None and top_k is not None
        else pool
    )
    print(f"[prove] {thm.theorem_id} ({len(effective_pool)} hint(s))", file=sys.stderr)
    result = _run_prove_loop(thm, effective_pool, llm, lake_project, imports, max_attempts)
    status = "ok" if result.ok else "FAIL"
    print(
        f"  -> {thm.theorem_id}: {status} after {len(result.attempts)} attempt(s)",
        file=sys.stderr,
    )
    return thm.theorem_id, result


def prove_round(
    theorems: list[Theorem],
    lemma_pool: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    output_dir: Path,
    num_workers: int = 1,
    retriever: Retriever | None = None,
    top_k: int | None = None,
    per_theorem_pools: dict[str, list[str]] | None = None,
) -> dict[str, RoundResult]:
    """Prove all theorems in this round using lemma_pool as hints.

    Writes prove_results.json under output_dir. Returns theorem_id -> RoundResult.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, RoundResult] = {}

    if num_workers > 1:
        results_map: dict[str, RoundResult] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(
                    _prove_one, thm, lemma_pool, llm, lake_project, imports,
                    max_attempts, retriever, top_k, per_theorem_pools,
                ): thm
                for thm in theorems
            }
            for fut in as_completed(futures):
                tid, result = fut.result()
                results_map[tid] = result
        results = {
            t.theorem_id: results_map[t.theorem_id]
            for t in theorems
            if t.theorem_id in results_map
        }
    else:
        for thm in theorems:
            tid, result = _prove_one(
                thm, lemma_pool, llm, lake_project, imports,
                max_attempts, retriever, top_k, per_theorem_pools,
            )
            results[tid] = result

    artifact = {
        "lake_project": str(lake_project),
        "imports": imports,
        "results": {
            tid: {
                "ok": r.ok,
                "final_error": r.final_error,
                "attempts": [asdict(a) for a in r.attempts],
            }
            for tid, r in results.items()
        },
    }
    (output_dir / PROVE_RESULTS_JSON).write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2)
    )
    n_ok = sum(1 for r in results.values() if r.ok)
    print(
        f"[done] {len(results)} theorems, {n_ok} ok -> {output_dir / PROVE_RESULTS_JSON}",
        file=sys.stderr,
    )
    return results
