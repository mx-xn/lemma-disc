"""Selection algorithm: pick the top lemmas from the registry for a proving round."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from exp.count_hyps import count_hyps as num_hyps

if TYPE_CHECKING:
    from exp.eval.lib.lemma_registry import LemmaEntry, LemmaRegistry
    from exp.lib.llm import LLM

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_RANK_TEMPLATE = (_PROMPTS_DIR / "llm_rank.md").read_text()

_RANK_SYSTEM = "You are a helpful Lean 4 assistant."
_INT_LINE_RE = re.compile(r"^\d+$")


def _llm_rank(entries: list[LemmaEntry], llm: LLM, imports: list[str]) -> list[str]:
    """Ask the LLM to rank unscored lemma entries; return statements in ranked order."""
    candidates_text = "\n".join(f"L{i}: {e.statement}" for i, e in enumerate(entries))
    imports_text = ", ".join(imports)
    prompt = (
        _RANK_TEMPLATE
        .replace("<<imports>>", imports_text)
        .replace("<<candidates>>", candidates_text)
    )
    resp = llm.chat(_RANK_SYSTEM, prompt)
    indices: list[int] = []
    seen: set[int] = set()
    for line in resp.text.splitlines():
        line = line.strip()
        if _INT_LINE_RE.match(line):
            idx = int(line)
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)
    return [entries[i].statement for i in indices if 0 <= i < len(entries)]


def select(
    registry: LemmaRegistry,
    max_n: int,
    max_hyps: int,
    llm: LLM,
    lake_project: Path,
    imports: list[str],
) -> list[str]:
    """Select up to max_n lemma statements from the registry for a proving round."""
    candidates = [e for e in registry.entries() if num_hyps(e.statement) <= max_hyps]
    candidates.sort(key=lambda e: e.score(), reverse=True)
    top = [e.statement for e in candidates[:max_n]]

    tail = [e for e in candidates[max_n:] if e.score() == 0.0]
    if len(top) < max_n and tail:
        ranked_tail = _llm_rank(tail, llm, imports)
        ranked_tail = [s for s in ranked_tail if s in {e.statement for e in tail}]
        top += ranked_tail[: max_n - len(top)]

    return top
