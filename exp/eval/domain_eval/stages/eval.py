"""Evaluate the test split under baseline or lemma-augmented conditions.

Thin dispatch only — no proving logic here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def run_eval(
    theorems_path: Path,
    output_dir: Path,
    lemmas_path: Path | None,
    top_k: int | None,
    llm_model: str,
    max_attempts: int,
    num_workers: int,
    lake_project_override: Path | None,
    imports_override: list[str] | None,
    force: bool,
) -> None:
    output_dir = Path(output_dir)

    if lemmas_path is None:
        from exp.eval.stages.baseline import BASELINE_JSON, run_baseline
        out_file = output_dir / BASELINE_JSON
        if out_file.exists() and not force:
            print(f"[skip] {out_file} exists (use --force to overwrite)", file=sys.stderr)
            return
        run_baseline(
            theorems_path=theorems_path,
            output_dir=output_dir,
            limit=None,
            force=force,
            llm_model=llm_model,
            max_attempts=max_attempts,
            num_workers=num_workers,
            lake_project_override=lake_project_override,
            imports_override=imports_override,
        )
        return

    # Lemma-augmented path.
    out_file = output_dir / "prove_results.json"
    if out_file.exists() and not force:
        print(f"[skip] {out_file} exists (use --force to overwrite)", file=sys.stderr)
        return

    from exp.lib.corpus import load_theorems
    from exp.lib.llm import LLM
    from exp.eval.lib.retriever import ByT5Retriever
    from exp.eval.stages.prove import prove_round

    data = json.loads(Path(lemmas_path).read_text())
    lemma_pool: list[str] = data.get("lemmas", [])

    tset = load_theorems(Path(theorems_path))
    lake_project = lake_project_override or tset.lake_project
    imports = imports_override or tset.imports
    if lake_project is None:
        raise ValueError(
            "lake_project is required: set 'lake_project' in test.json "
            "or pass --lake-project"
        )
    if not imports:
        raise ValueError(
            "imports is required: set 'imports' in test.json or pass --imports"
        )
    lake_project = Path(lake_project)
    imports = list(imports)

    llm = LLM(model=llm_model, cache_dir=output_dir / "cache")
    retriever = ByT5Retriever() if top_k is not None else None

    prove_round(
        theorems=tset.theorems,
        lemma_pool=lemma_pool,
        llm=llm,
        lake_project=lake_project,
        imports=imports,
        max_attempts=max_attempts,
        output_dir=output_dir,
        num_workers=num_workers,
        retriever=retriever,
        top_k=top_k,
    )
