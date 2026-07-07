"""One proving round for the iterative eval loop.

Like exp/expB/stages/solo.py but:
  - takes a ``lemma_pool`` (list of statement strings) instead of a static
    candidates file
  - stores ``raw_response`` on each Attempt so LemmaRegistry.record_usage can
    parse <used_lemmas> indices across attempts
  - supports M independent samples per theorem (pass@M); each sample is an
    independent prove loop with its own fix budget
  - writes per-attempt .txt debug files to the cache directory so results are
    human-readable without opening JSON
  - writes prove_results.json in output_dir

Schema for prove_results.json (per theorem_id):
    {
        "ok":          bool,          # true if any sample succeeded (pass@M)
        "final_error": str,           # last sample's error when ok is False
        "samples": [                  # one entry per sample
            {
                "ok":          bool,
                "final_error": str,
                "attempts":    [Attempt, ...]
            },
            ...
        ]
    }

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

from exp.eval.lib.result_store import merge_results_file
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


@dataclass
class TheoremResult:
    """Aggregate result for one theorem across all M samples."""
    ok: bool           # True if any sample succeeded (pass@M)
    samples: list[RoundResult] = field(default_factory=list)
    final_error: str = ""  # last sample's error when ok is False


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


def _write_attempt_txt(
    scratch_dir: Path,
    theorem_id: str,
    sample_index: int,
    attempt_index: int,
    proof_body: str,
    ok: bool,
    error_text: str,
) -> None:
    """Write a human-readable .txt file for one proving attempt."""
    label = "init" if attempt_index == 0 else f"fix_{attempt_index}"
    result_section = "[lean result]\nOK" if ok else f"[lean error]\n{error_text}"
    content = (
        f"theorem:  {theorem_id}\n"
        f"sample:   {sample_index}\n"
        f"attempt:  {label}\n"
        f"\n"
        f"[proof]\n"
        f"{proof_body}\n"
        f"\n"
        f"{result_section}\n"
    )
    path = scratch_dir / f"{theorem_id}__s{sample_index}__{label}.txt"
    path.write_text(content, encoding="utf-8")


def _run_prove_loop(
    thm: Theorem,
    lemma_pool: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    lean_scratch_dir: Path | None = None,
    sample_index: int = 0,
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
            scratch_dir=lean_scratch_dir,
        )

        if lean_scratch_dir is not None:
            _write_attempt_txt(
                lean_scratch_dir, thm.theorem_id, sample_index, i,
                proof_body, check.ok, check.error_text,
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


def _run_samples(
    thm: Theorem,
    lemma_pool: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_attempts: int,
    lean_scratch_dir: Path | None,
    num_samples: int,
) -> list[RoundResult]:
    """Run num_samples independent prove loops for one theorem."""
    return [
        _run_prove_loop(
            thm, lemma_pool, llm, lake_project, imports,
            max_attempts, lean_scratch_dir, sample_index=s,
        )
        for s in range(num_samples)
    ]


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
    lean_scratch_dir: Path | None = None,
    num_samples: int = 1,
) -> tuple[str, TheoremResult]:
    pool = per_theorem_pools[thm.theorem_id] if per_theorem_pools else lemma_pool
    effective_pool = (
        retriever.retrieve(thm.statement_text, pool, top_k)
        if retriever is not None and top_k is not None
        else pool
    )
    print(
        f"[prove] {thm.theorem_id} ({len(effective_pool)} hint(s), {num_samples} sample(s))",
        file=sys.stderr,
    )
    samples = _run_samples(
        thm, effective_pool, llm, lake_project, imports,
        max_attempts, lean_scratch_dir, num_samples,
    )
    ok = any(s.ok for s in samples)
    final_error = "" if ok else samples[-1].final_error
    n_ok = sum(1 for s in samples if s.ok)
    status = "ok" if ok else "FAIL"
    print(
        f"  -> {thm.theorem_id}: {status} ({n_ok}/{num_samples} samples ok)",
        file=sys.stderr,
    )
    return thm.theorem_id, TheoremResult(ok=ok, samples=samples, final_error=final_error)


def _serialize_sample(s: RoundResult) -> dict:
    return {
        "ok": s.ok,
        "final_error": s.final_error,
        "attempts": [asdict(a) for a in s.attempts],
    }


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
    force: bool = False,
    num_samples: int = 1,
) -> dict[str, TheoremResult]:
    """Prove all theorems using lemma_pool as hints.

    Writes prove_results.json under output_dir. Returns theorem_id -> TheoremResult.
    Per-attempt .txt debug files and Lean scratch files are saved under
    output_dir/cache/ for inspection; LLM JSON cache lives in output_dir/cache/llm/.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lean_scratch_dir = output_dir / CACHE_SUBDIR
    lean_scratch_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, TheoremResult] = {}

    if num_workers > 1:
        results_map: dict[str, TheoremResult] = {}
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = {
                pool.submit(
                    _prove_one, thm, lemma_pool, llm, lake_project, imports,
                    max_attempts, retriever, top_k, per_theorem_pools,
                    lean_scratch_dir, num_samples,
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
                lean_scratch_dir, num_samples,
            )
            results[tid] = result

    merge_results_file(
        output_dir / PROVE_RESULTS_JSON,
        str(lake_project),
        imports,
        {
            tid: {
                "ok": r.ok,
                "final_error": r.final_error,
                "samples": [_serialize_sample(s) for s in r.samples],
            }
            for tid, r in results.items()
        },
        force=force,
    )
    n_ok = sum(1 for r in results.values() if r.ok)
    print(
        f"[done] {len(results)} theorems, {n_ok} ok -> {output_dir / PROVE_RESULTS_JSON}",
        file=sys.stderr,
    )
    return results
