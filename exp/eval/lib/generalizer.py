"""Optional LLM generalizer for validated Lean 4 lemma statements.

``generalize_one`` asks the LLM to produce a strictly more general statement,
then validates it with Lean; if validation fails it falls back to the original.
``generalize_lemmas`` applies ``generalize_one`` to every statement in a list.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from exp.eval.lib.lemma_fixer import batch_validate

if TYPE_CHECKING:
    from exp.lib.llm import LLM

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_GEN_TEMPLATE = (_PROMPTS_DIR / "generalize.md").read_text()
_GEN_SYSTEM = "You are a helpful Lean 4 assistant."


def _lean_check_stmt(stmt: str, lake_project: Path, imports: list[str]) -> bool:
    broken = batch_validate({0: stmt}, lake_project, imports)
    return 0 not in broken


def _llm_generalize(stmt: str, llm: LLM, imports: list[str]) -> str:
    prompt = (
        _GEN_TEMPLATE
        .replace("<<statement>>", stmt)
        .replace("<<imports>>", ", ".join(imports))
    )
    return llm.chat(_GEN_SYSTEM, prompt).text.strip()


def generalize_one(
    stmt: str,
    llm: LLM,
    lake_project: Path,
    imports: list[str],
) -> str:
    """Return a generalized version of stmt if the LLM produces a valid one, else stmt."""
    generalized = _llm_generalize(stmt, llm, imports)
    if generalized and _lean_check_stmt(generalized, lake_project, imports):
        return generalized
    return stmt


def generalize_lemmas(
    stmts: list[str],
    llm: LLM,
    lake_project: Path,
    imports: list[str],
) -> list[str]:
    """Generalize each statement; fall back to original when generalization is invalid."""
    return [generalize_one(s, llm, lake_project, imports) for s in stmts]
