"""Validate and LLM-fix malformed Lean 4 lemma statements.

``batch_validate`` writes all statements into a single scratch .lean file,
runs ``lake env lean`` once, and maps error locations back to statement indices
using ``_parse_errors`` from ``exp.lib.lean_check``.

``fix_lemmas`` iterates up to ``max_fix_rounds``, retrying only still-broken
statements each round; the final pass confirms last-round LLM fixes.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from exp.lib.lean_check import _parse_errors

if TYPE_CHECKING:
    from exp.lib.llm import LLM

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_FIX_TEMPLATE = (_PROMPTS_DIR / "fix_lemma.md").read_text()
_FIX_SYSTEM = "You are a helpful Lean 4 assistant."

_SORRY_RE = re.compile(r"declaration uses [`']sorry[`']")


def batch_validate(
    stmts: dict[int, str],
    lake_project: Path,
    imports: list[str],
) -> dict[int, str]:
    """Lean-check a batch of lemma statements.

    Returns ``{idx: error_text}`` for every statement that fails to type-check.
    Statements not in the returned dict are confirmed valid.
    """
    if not stmts:
        return {}

    lake_project = Path(lake_project).resolve()
    import_block = "\n".join(f"import {m}" for m in imports)

    source_lines: list[str] = import_block.splitlines() if import_block else []
    source_lines.append("")

    decl_line: dict[int, int] = {}  # idx → 1-indexed line number of declaration
    for idx in sorted(stmts):
        decl_line[idx] = len(source_lines) + 1
        source_lines.append(f"lemma validate_{idx} : {stmts[idx]} := by sorry")

    source = "\n".join(source_lines) + "\n"

    h = hashlib.sha256(source.encode()).hexdigest()[:16]
    scratch = lake_project / f"_eval_validate_{h}.lean"
    scratch.write_text(source)

    try:
        proc = subprocess.run(
            ["lake", "env", "lean", scratch.name],
            cwd=lake_project,
            capture_output=True,
            text=True,
            timeout=300.0,
        )
    except subprocess.TimeoutExpired:
        return {i: "lean timed out" for i in stmts}
    finally:
        scratch.unlink(missing_ok=True)

    combined = (proc.stdout or "") + (proc.stderr or "")
    combined = "\n".join(
        line for line in combined.splitlines()
        if not _SORRY_RE.search(line)
    )

    if proc.returncode == 0 and "error:" not in combined:
        return {}

    # Map each error's line number to the owning declaration index.
    # The owner is the last declaration whose start line is <= the error line.
    sorted_decls = sorted(decl_line.items(), key=lambda kv: kv[1])

    def _line_to_decl(line_num: int) -> int | None:
        owner: int | None = None
        for idx, start in sorted_decls:
            if start <= line_num:
                owner = idx
        return owner

    errors = _parse_errors(combined)
    broken: dict[int, list[str]] = {}
    for line, _col, msg in errors:
        owner = _line_to_decl(line)
        if owner is not None:
            broken.setdefault(owner, []).append(msg)

    return {idx: "\n".join(msgs) for idx, msgs in broken.items()}


def _llm_fix_one(stmt: str, error: str, llm: LLM, imports: list[str]) -> str:
    prompt = (
        _FIX_TEMPLATE
        .replace("<<statement>>", stmt)
        .replace("<<error>>", error)
        .replace("<<imports>>", ", ".join(imports))
    )
    return llm.chat(_FIX_SYSTEM, prompt).text.strip()


def fix_lemmas(
    statements: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
    max_fix_rounds: int = 2,
) -> list[str]:
    """Return the subset of statements that are (or become) valid Lean 4 propositions.

    Broken statements are sent to the LLM for repair up to ``max_fix_rounds``
    times. Only statements confirmed valid by Lean are included in the result.
    """
    current = list(statements)
    valid_mask = [False] * len(current)

    for _ in range(max_fix_rounds):
        to_check = {i: current[i] for i in range(len(current)) if not valid_mask[i]}
        broken = batch_validate(to_check, lake_project, imports)

        for i in to_check:
            if i not in broken:
                valid_mask[i] = True

        if not broken:
            break

        for idx, err in broken.items():
            fixed = _llm_fix_one(current[idx], err, llm, imports)
            if fixed:
                current[idx] = fixed

    # Final pass: confirm any statements fixed in the last round.
    to_check = {i: current[i] for i in range(len(current)) if not valid_mask[i]}
    broken = batch_validate(to_check, lake_project, imports)
    for i in to_check:
        if i not in broken:
            valid_mask[i] = True

    return [current[i] for i in range(len(current)) if valid_mask[i]]
