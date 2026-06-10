"""Corpus construction and lemma extraction for the iterative eval loop.

``build_corpus`` writes one .lean file per theorem into a ``corpus/``
subdirectory of ``work_dir``:
  - Solved theorems (result.ok) use their last attempted proof body.
  - Unsolved theorems with attempts: admit-patch failing tactics identified
    in the last attempt's error text; fall back to ``sorry`` when no patch
    is possible (empty error, "proof contains sorry/admit", or no lines match).
  - Theorems with no result or no attempts use ``sorry``.

``extract_lemmas`` delegates to ``exp.eval.lib.extractor``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from exp.eval.lib.extractor import extract_lemmas as _extract_lemmas_impl
from exp.lib.corpus import Theorem

_FILE_TEMPLATE = """\
{import_block}

{local_ctx_block}theorem {theorem_id} {statement_text} := by
{proof_body}
"""

# Matches a lean_check context-snippet caret line: exactly 4 leading spaces
# (snippet prefix), then any number of additional spaces, then a single "^".
_CARET_LINE_RE = re.compile(r"^    \s*\^$")


def _indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines()) if text.strip() else pad + "sorry"


def _extract_failing_line_content(error_text: str) -> list[str]:
    """Return stripped source-line content for each error location in error_text.

    error_text is lean_check.format_error output with blocks of the form:
        location:
            <prev_src_line>
            <failing_src_line>    ← 4-space snippet prefix + original source line
            <spaces>^
        error: <msg>

    Returns the stripped tactic strings (snippet prefix and proof-body
    2-space indent both removed), deduplicated, in order of appearance.
    """
    result: list[str] = []
    lines = error_text.splitlines()
    for i, line in enumerate(lines):
        if i > 0 and _CARET_LINE_RE.match(line):
            prev = lines[i - 1]
            if prev.startswith("    "):
                stripped = prev[4:].strip()
                if stripped:
                    result.append(stripped)
    seen: set[str] = set()
    deduped: list[str] = []
    for s in result:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def _admit_patch(proof_body: str, error_text: str) -> str | None:
    """Replace failing tactic lines in proof_body with 'admit'.

    Returns the patched proof body if at least one line was replaced,
    or None when no patch is possible (unrecognised error format, no lines
    matched, or "proof contains sorry/admit" error).
    """
    if not error_text or error_text.startswith("proof contains"):
        return None
    failing = _extract_failing_line_content(error_text)
    if not failing:
        return None
    failing_set = set(failing)
    changed = False
    patched: list[str] = []
    for line in proof_body.splitlines():
        if line.strip() in failing_set:
            indent = len(line) - len(line.lstrip())
            patched.append(" " * indent + "admit")
            changed = True
        else:
            patched.append(line)
    return "\n".join(patched) if changed else None


def build_corpus(
    all_results: dict[str, Any],
    theorems: list[Theorem],
    lake_project: Path,
    imports: list[str],
    work_dir: Path,
) -> Path:
    """Write one .lean file per theorem into work_dir/corpus/.

    Returns the corpus directory path.
    """
    corpus_dir = work_dir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    import_block = "\n".join(f"import {m}" for m in imports)

    for thm in theorems:
        result = all_results.get(thm.theorem_id)
        if result is not None and result.ok and result.attempts:
            proof_body = _indent(result.attempts[-1].proof_body)
        elif result is not None and result.attempts:
            last = result.attempts[-1]
            err = (
                getattr(result, "final_error", None)
                or getattr(last, "error_text", "")
                or ""
            )
            patched = _admit_patch(last.proof_body, err)
            proof_body = _indent(patched) if patched is not None else "  sorry"
        else:
            proof_body = "  sorry"

        local_ctx_block = (thm.local_ctx.rstrip() + "\n\n") if thm.local_ctx.strip() else ""

        source = _FILE_TEMPLATE.format(
            import_block=import_block,
            local_ctx_block=local_ctx_block,
            theorem_id=thm.theorem_id,
            statement_text=thm.statement_text,
            proof_body=proof_body,
        )
        (corpus_dir / f"{thm.theorem_id}.lean").write_text(source)

    return corpus_dir


def extract_lemmas(lean_files_dir: Path, work_dir: Path) -> list[str]:
    """Run phases 1-4 on lean_files_dir; return list of statement strings."""
    return _extract_lemmas_impl(lean_files_dir, work_dir)
