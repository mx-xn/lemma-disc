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
    pipeline_timeout_ms: int | None,
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
    # Trace names are fully qualified (e.g. "Juvix.Core.Main.Env.Approx.Foo.bar");
    # theorem_ids may be partially qualified ("Env.Approx.Foo.bar") or bare ("bar").
    # Match any dot-delimited suffix of the trace name against the train ID set.
    def _matches(name: str) -> bool:
        if name in train_ids:
            return True
        parts = name.split(".")
        for i in range(1, len(parts)):
            if ".".join(parts[i:]) in train_ids:
                return True
        return False

    decls = [d for d in trace.get("declarations", []) if _matches(d.get("name", ""))]
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
    if pipeline_timeout_ms is not None:
        cmd += ["--timeout", str(pipeline_timeout_ms)]
    print(f"[learn] running pipeline: {' '.join(cmd)}", file=sys.stderr)
    # Prepend the lemma conda env's bin so sbt/java are found even without `conda activate`.
    import os
    env = os.environ.copy()
    lemma_bin = "/nas/conda-envs/lemma/bin"
    env["PATH"] = lemma_bin + os.pathsep + env.get("PATH", "")
    result = subprocess.run(cmd, check=True, env=env)
    _ = result  # returncode checked by check=True

    data = json.loads(raw_lemmas_path.read_text())
    return [entry["statement"] for entry in data.get("lemmas", [])]


def _extract_conclusion(stmt: str) -> str:
    """Return the conclusion of a binder-syntax statement (after the last depth-0 colon)."""
    depth = 0
    last_colon = -1
    for i, ch in enumerate(stmt):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            last_colon = i
    return stmt[last_colon + 1:].strip() if last_colon != -1 else stmt.strip()


def _extract_premises(stmt: str) -> frozenset[tuple[str, str]]:
    """Return frozenset of (var_name, type) pairs parsed from a binder-syntax statement.

    Handles multi-variable binders like ``(x y : T)`` and all bracket kinds
    ``()``, ``{}``, ``[]``.
    """
    depth = 0
    last_colon = -1
    for i, ch in enumerate(stmt):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            last_colon = i
    binder_text = stmt[:last_colon].strip() if last_colon != -1 else ""

    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(binder_text):
        if binder_text[i] in "([{":
            close = {"(": ")", "[": "]", "{": "}"}[binder_text[i]]
            j = i + 1
            d = 1
            while j < len(binder_text) and d > 0:
                if binder_text[j] in "([{":
                    d += 1
                elif binder_text[j] in ")]}":
                    d -= 1
                j += 1
            inner = binder_text[i + 1: j - 1].strip()
            colon_pos = inner.find(":")
            if colon_pos != -1:
                vars_part = inner[:colon_pos].strip()
                type_part = " ".join(inner[colon_pos + 1:].split())
                for v in vars_part.split():
                    v = v.strip()
                    if v:
                        pairs.append((v, type_part))
            i = j
        else:
            i += 1
    return frozenset(pairs)


def _strip_outer_parens(s: str) -> str:
    """Strip a single layer of balanced outer parentheses if present."""
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        matched = False
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth == 0:
                matched = (i == len(s) - 1)
                break
        if matched:
            s = s[1:-1].strip()
        else:
            break
    return s


def _normalize(s: str) -> str:
    return " ".join(_strip_outer_parens(s).split())


def _parse_llm_blocks(text: str) -> list[dict[str, str]]:
    """Parse <<<STATEMENT>>> / <<<PROOF>>> / <<<END>>> blocks from LLM response."""
    results: list[dict[str, str]] = []
    parts = text.split("<<<STATEMENT>>>")
    for part in parts[1:]:
        if "<<<PROOF>>>" not in part:
            continue
        stmt_raw, rest = part.split("<<<PROOF>>>", 1)
        proof_raw = rest.split("<<<END>>>", 1)[0] if "<<<END>>>" in rest else rest
        stmt = stmt_raw.strip()
        proof = proof_raw.strip()
        if stmt:
            results.append({"statement": stmt, "proof": proof})
    return results


def _build_theorem_signatures(
    tset,
) -> frozenset[tuple[frozenset[tuple[str, str]], str]]:
    """Build a (premises, conclusion) signature set from a TheoremSet."""
    sigs: set[tuple[frozenset[tuple[str, str]], str]] = set()
    for thm in tset.theorems:
        stmt = thm.statement_text
        conclusion = _normalize(_extract_conclusion(stmt))
        premises = _extract_premises(stmt)
        sigs.add((premises, conclusion))
    return frozenset(sigs)


def _is_duplicate(
    lemma: dict[str, str],
    theorem_sigs: frozenset[tuple[frozenset[tuple[str, str]], str]],
) -> bool:
    stmt = lemma["statement"]
    conclusion = _normalize(_extract_conclusion(stmt))
    premises = _extract_premises(stmt)
    return (premises, conclusion) in theorem_sigs


def _run_llm(
    train_path: Path,
    output_dir: Path,
    lean_file: Path | None,
    llm_model: str,
    imports: list[str],
    tset,
) -> list[dict[str, str]]:
    """Ask LLM to generate lemmas (with proofs) from a Lean training file."""
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

    lemmas = _parse_llm_blocks(resp.text)
    print(f"[learn] LLM generated {len(lemmas)} raw lemma(s)", file=sys.stderr)

    theorem_sigs = _build_theorem_signatures(tset)
    before = len(lemmas)
    lemmas = [l for l in lemmas if not _is_duplicate(l, theorem_sigs)]
    n_filtered = before - len(lemmas)
    if n_filtered:
        print(f"[learn] dedup filter: dropped {n_filtered} theorem-duplicate(s)", file=sys.stderr)

    raw_lemmas_path = output_dir / "raw_lemmas.json"
    raw_lemmas_path.write_text(
        json.dumps({"lemmas": lemmas}, ensure_ascii=False, indent=2)
    )
    return lemmas


def run_learn(
    method: str,
    train_path: Path,
    output_dir: Path,
    lake_project_override: Path | None,
    imports_override: list[str] | None,
    trace_path: Path | None,
    skip_pipeline: bool,
    pipeline_timeout_ms: int | None,
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
        raw_stmts = _run_pipeline(train_path, output_dir, trace_path, skip_pipeline, pipeline_timeout_ms)
    elif method == "llm":
        raw_stmts = _run_llm(train_path, output_dir, lean_file, llm_model, imports, tset)
    else:
        raise ValueError(f"unknown method: {method!r}; expected 'pipeline' or 'llm'")

    # llm method returns list[dict] with proofs — skip fix_lemmas (validation is
    # done via the separate `validate` command which handles proof-aware checking)
    has_proofs = raw_stmts and isinstance(raw_stmts[0], dict)

    if has_proofs or skip_fix or not raw_stmts:
        fixed = raw_stmts
        if skip_fix and not has_proofs:
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
