"""Fix-loop prover: prompt → Lean check → retry up to ``max_attempts`` times.

With ``max_attempts=3`` this is the spec'd cadence: **1 initial sample + 2
fix-loops**. The initial attempt uses the baseline template; every subsequent
attempt uses the fix template, which receives the previous proof body and error.
Each attempt is a fresh ``llm.chat`` call and is independently cacheable.

Callers supply ``baseline_template`` and ``fix_template`` as strings so each
experiment can use its own prompt files.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from .corpus import Theorem
from .lean_check import check_proof
from .llm import LLM

SYSTEM_PROMPT = (
    "You are an expert Lean 4 theorem prover. Your output **must** strictly "
    "adhere to the XML-tag format specified in each request."
)

_PROOF_TAG_RE = re.compile(r"<lean4_proof>(.*?)</lean4_proof>", re.DOTALL)


def _strip_leading_by(body: str) -> str:
    """Remove a bare 'by' first line that duplicates the ':= by' in the wrapper."""
    lines = body.splitlines()
    if lines and lines[0].strip() == "by":
        # Drop the 'by' line and dedent the rest by 2 spaces if uniformly indented.
        rest = lines[1:]
        if all(ln == "" or ln.startswith("  ") for ln in rest):
            rest = [ln[2:] if ln.startswith("  ") else ln for ln in rest]
        body = "\n".join(rest)
    return body.strip("\n")


def parse_proof_response(text: str) -> str:
    """Extract proof body from <lean4_proof> tag.

    Falls back to fence-stripping if the tag is absent.
    """
    m = _PROOF_TAG_RE.search(text)
    if m:
        return _strip_leading_by(textwrap.dedent(m.group(1)).strip("\n"))
    raw = text.strip()
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        raw = raw[first_nl + 1:] if first_nl != -1 else raw
        if raw.endswith("```"):
            raw = raw[:-3]
    return _strip_leading_by(textwrap.dedent(raw).strip("\n"))


@dataclass(frozen=True)
class Attempt:
    proof_body: str
    ok: bool
    error_text: str


@dataclass
class ProverResult:
    ok: bool
    attempts: list[Attempt] = field(default_factory=list)
    final_error: str = ""


def _render_baseline(thm: Theorem, imports: list[str], baseline_template: str) -> str:
    return (
        baseline_template
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
    )


def render_fix(thm: Theorem, imports: list[str], last: Attempt, fix_template: str) -> str:
    indented_body = "\n".join("  " + l for l in last.proof_body.splitlines() or [""])
    return (
        fix_template
        .replace("<<imports>>", ", ".join(imports))
        .replace("<<local_ctx>>", thm.local_ctx)
        .replace("<<statement>>", thm.statement_text)
        .replace("<<proof_body>>", indented_body)
        .replace("<<error>>", last.error_text)
    )


def prove(
    thm: Theorem,
    llm: LLM,
    *,
    lake_project: Path,
    imports: list[str],
    max_attempts: int = 3,
    baseline_template: str,
    fix_template: str,
    lean_scratch_dir: Path | None = None,
) -> ProverResult:
    """Run the fix-loop. Returns as soon as any attempt succeeds."""
    result = ProverResult(ok=False)
    for i in range(max_attempts):
        user_prompt = (
            _render_baseline(thm, imports, baseline_template)
            if i == 0
            else render_fix(thm, imports, result.attempts[-1], fix_template)
        )
        resp = llm.chat(SYSTEM_PROMPT, user_prompt)
        proof_body = parse_proof_response(resp.text)

        check = check_proof(
            thm.statement_text,
            proof_body,
            lake_project=lake_project,
            imports=imports,
            decl_name=f"expB_{thm.theorem_id}",
            scratch_dir=lean_scratch_dir,
        )

        result.attempts.append(Attempt(
            proof_body=proof_body,
            ok=check.ok,
            error_text=check.error_text,
        ))

        if check.ok:
            result.ok = True
            result.final_error = ""
            return result

    result.final_error = result.attempts[-1].error_text if result.attempts else ""
    return result
