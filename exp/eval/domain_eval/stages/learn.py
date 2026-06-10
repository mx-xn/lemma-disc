"""Learn a lemma library from the training split.

Two methods:
  pipeline — filter trace to training decls, run phases 2-4, then lemma_fixer
  llm      — read a Lean source file, ask LLM for lemma statements, then lemma_fixer
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from exp.lib.corpus import load_theorems

if TYPE_CHECKING:
    from exp.lib.llm import LLM

_PIPELINE_SCRIPT = Path(__file__).resolve().parents[4] / "pipeline" / "run_full.sh"
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_LLM_GENERATE_TEMPLATE = (_PROMPTS_DIR / "llm_generate.md").read_text()
_LLM_SYSTEM = "You are a helpful Lean 4 assistant."


def _resolve_setup(
    tset,
    lake_project_override: Path | None,
    imports_override: list[str] | None,
) -> tuple[Path, list[str]]:
    lake_project = lake_project_override or tset.lake_project
    imports = imports_override or tset.imports
    if lake_project is None:
        raise ValueError(
            "lake_project is required: set 'lake_project' in train.json "
            "or pass --lake-project"
        )
    if not imports:
        raise ValueError(
            "imports is required: set 'imports' in train.json or pass --imports"
        )
    return Path(lake_project), list(imports)


def _run_pipeline(
    train_path: Path,
    output_dir: Path,
    trace_path: Path | None,
    skip_pipeline: bool,
) -> list[str]:
    """Filter trace to training decls, run phases 2-4; return raw statement strings."""
    raw_lemmas_path = output_dir / "raw_lemmas.json"

    if skip_pipeline:
        raw_lemmas_path.write_text(json.dumps({"lemmas": []}, indent=2))
        print("[learn] --skip-pipeline: wrote empty raw_lemmas.json", file=sys.stderr)
        return []

    if trace_path is None:
        raise ValueError("--trace is required for --method pipeline")

    tset = load_theorems(train_path)
    train_ids = {t.theorem_id for t in tset.theorems}

    trace = json.loads(trace_path.read_text())
    # Keep only declarations whose name matches a training theorem ID.
    decls = [d for d in trace.get("declarations", []) if d.get("name") in train_ids]
    filtered_trace = {
        "source_file": trace.get("source_file", str(trace_path)),
        "declarations": decls,
    }
    train_trace_path = output_dir / "train_trace.json"
    train_trace_path.write_text(json.dumps(filtered_trace, ensure_ascii=False, indent=2))
    print(
        f"[learn] filtered trace: {len(decls)}/{len(trace.get('declarations', []))} decls",
        file=sys.stderr,
    )

    bash = shutil.which("bash") or "bash"
    cmd = [bash, str(_PIPELINE_SCRIPT), str(train_trace_path), "--output", str(raw_lemmas_path)]
    print(f"[learn] running pipeline: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, check=True)
    _ = result  # returncode checked by check=True

    data = json.loads(raw_lemmas_path.read_text())
    return [entry["statement"] for entry in data.get("lemmas", [])]


def _run_llm(
    train_path: Path,
    output_dir: Path,
    lean_file: Path | None,
    llm_model: str,
    imports: list[str],
) -> list[str]:
    """Ask LLM to generate lemmas from a Lean training file."""
    if lean_file is None:
        raise ValueError("--lean-file is required for --method llm")

    corpus_text = lean_file.read_text()
    prompt = (
        _LLM_GENERATE_TEMPLATE
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<corpus>>", corpus_text)
    )

    from exp.lib.llm import LLM
    llm = LLM(model=llm_model, cache_dir=output_dir / "cache")
    resp = llm.chat(_LLM_SYSTEM, prompt)

    raw_stmts = [line.strip() for line in resp.text.splitlines() if line.strip()]

    raw_lemmas_path = output_dir / "raw_lemmas.json"
    raw_lemmas_path.write_text(
        json.dumps({"lemmas": raw_stmts}, ensure_ascii=False, indent=2)
    )
    print(f"[learn] LLM generated {len(raw_stmts)} raw statement(s)", file=sys.stderr)
    return raw_stmts


def run_learn(
    method: str,
    train_path: Path,
    output_dir: Path,
    lake_project_override: Path | None,
    imports_override: list[str] | None,
    trace_path: Path | None,
    skip_pipeline: bool,
    lean_file: Path | None,
    llm_model: str,
    skip_fix: bool,
    force: bool,
) -> None:
    output_dir = Path(output_dir)
    learned_path = output_dir / "learned_lemmas.json"

    if learned_path.exists() and not force:
        print(f"[skip] {learned_path} exists (use --force to overwrite)", file=sys.stderr)
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    tset = load_theorems(train_path)
    lake_project, imports = _resolve_setup(tset, lake_project_override, imports_override)

    if method == "pipeline":
        raw_stmts = _run_pipeline(train_path, output_dir, trace_path, skip_pipeline)
    elif method == "llm":
        raw_stmts = _run_llm(train_path, output_dir, lean_file, llm_model, imports)
    else:
        raise ValueError(f"unknown method: {method!r}; expected 'pipeline' or 'llm'")

    if skip_fix or not raw_stmts:
        fixed = raw_stmts
        if skip_fix:
            print("[learn] --skip-fix: skipping lemma_fixer", file=sys.stderr)
    else:
        from exp.lib.llm import LLM
        from exp.eval.lib.lemma_fixer import fix_lemmas
        llm = LLM(model=llm_model, cache_dir=output_dir / "cache")
        fixed = fix_lemmas(raw_stmts, llm, lake_project, imports)
        print(
            f"[learn] lemma_fixer: {len(raw_stmts)} raw → {len(fixed)} valid",
            file=sys.stderr,
        )

    learned_path.write_text(
        json.dumps({"lemmas": fixed}, ensure_ascii=False, indent=2)
    )
    print(f"[learn] wrote {len(fixed)} lemma(s) to {learned_path}", file=sys.stderr)
