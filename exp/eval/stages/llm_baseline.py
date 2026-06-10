"""LLM-baseline variant of the iterative eval loop (step 9b).

Same outer loop structure as loop.py, including the corpus construction step.
Instead of running phases 1-5, concatenates the corpus .lean files and sends
them to the LLM (llm_generate.md) to produce candidate lemma statements.
The candidates are then validated and fixed with fix_lemmas. No registry or
scoring — the pool is rebuilt from scratch each round.

CLI entry-point: run.py llm-baseline

Outputs per round: output_dir/round_NN/prove_results.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from exp.lib.corpus import Theorem, TheoremSet, load_theorems
from exp.lib.llm import LLM
from exp.eval.lib.lemma_fixer import fix_lemmas
from exp.eval.stages.extract import build_corpus
from exp.eval.stages.prove import RoundResult, prove_round

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_GENERATE_TEMPLATE = (_PROMPTS_DIR / "llm_generate.md").read_text()
_GENERATE_SYSTEM = "You are a helpful Lean 4 assistant."


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


def _llm_generate_lemmas(
    corpus_dir: Path,
    llm: LLM,
    imports: list[str],
) -> list[str]:
    """Concatenate corpus .lean files and ask the LLM for candidate lemma statements."""
    corpus_files = sorted(corpus_dir.glob("*.lean"))
    corpus_text = "\n\n".join(f.read_text() for f in corpus_files)
    prompt = (
        _GENERATE_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<corpus>>", corpus_text)
    )
    resp = llm.chat(_GENERATE_SYSTEM, prompt)
    return [line.strip() for line in resp.text.splitlines() if line.strip()]


def run_llm_baseline(
    *,
    theorems_path: Path,
    output_dir: Path,
    rounds: int,
    llm_model: str,
    max_attempts: int,
    max_fix_rounds: int = 2,
    num_workers: int = 1,
    force: bool = False,
    lake_project_override: Path | None = None,
    imports_override: list[str] | None = None,
) -> None:
    output_dir = Path(output_dir)
    tset = load_theorems(Path(theorems_path))
    lake_project, imports = _resolve_setup(tset, lake_project_override, imports_override)

    llm = LLM(model=llm_model, cache_dir=output_dir / "cache")
    theorems: list[Theorem] = list(tset.theorems)
    unsolved: list[Theorem] = list(theorems)
    all_results: dict[str, RoundResult] = {}
    lemma_pool: list[str] = []  # empty on round 1; rebuilt each round thereafter

    for r in range(rounds):
        round_dir = output_dir / f"round_{r + 1:02d}"
        prove_out = round_dir / "prove_results.json"

        if prove_out.exists() and not force:
            print(f"[skip] {prove_out} exists (use --force to overwrite)", file=sys.stderr)
            # Reload round_results so all_results stays consistent.
            data = json.loads(prove_out.read_text())
            round_results: dict[str, RoundResult] = {}
            for tid, rec in data.get("results", {}).items():
                attempts = [
                    type("Attempt", (), {
                        "proof_body": a["proof_body"],
                        "ok": a["ok"],
                        "error_text": a["error_text"],
                        "raw_response": a.get("raw_response", ""),
                    })()
                    for a in rec.get("attempts", [])
                ]
                rr = RoundResult(ok=rec["ok"], final_error=rec.get("final_error", ""))
                # Attach reconstructed attempts (list assignment on dataclass).
                object.__setattr__(rr, "attempts", attempts) if hasattr(rr, "__dataclass_fields__") else None
                rr.attempts = attempts  # type: ignore[assignment]
                round_results[tid] = rr
            all_results.update(round_results)
            unsolved = [t for t in unsolved if not all_results.get(t.theorem_id, RoundResult(ok=False)).ok]
            if not unsolved:
                print(f"[done] all theorems solved (loaded from disk)", file=sys.stderr)
                return
            continue

        # ── Step 1: prove ────────────────────────────────────────────────────
        round_results = prove_round(
            unsolved, lemma_pool, llm, lake_project, imports,
            max_attempts, round_dir, num_workers,
        )
        all_results.update(round_results)

        newly_solved = [t for t in unsolved if round_results[t.theorem_id].ok]
        unsolved = [t for t in unsolved if not round_results[t.theorem_id].ok]

        n_ok = sum(1 for rv in round_results.values() if rv.ok)
        print(
            f"[round {r + 1}] {n_ok}/{len(round_results)} solved; "
            f"{len(unsolved)} unsolved remain",
            file=sys.stderr,
        )

        if not unsolved:
            print(f"[done] all theorems solved after round {r + 1}", file=sys.stderr)
            break

        # ── Step 2: build extraction corpus ─────────────────────────────────
        corpus_dir = build_corpus(
            all_results, theorems, lake_project, imports, round_dir
        )

        # ── Step 3: LLM generate candidate lemma statements ─────────────────
        raw_lemmas = _llm_generate_lemmas(corpus_dir, llm, imports)
        print(
            f"[round {r + 1}] LLM generated {len(raw_lemmas)} raw candidates",
            file=sys.stderr,
        )

        # ── Step 4: validate and fix ─────────────────────────────────────────
        lemma_pool = fix_lemmas(raw_lemmas, llm, lake_project, imports, max_fix_rounds)
        print(
            f"[round {r + 1}] {len(lemma_pool)} lemmas validated for next round",
            file=sys.stderr,
        )
