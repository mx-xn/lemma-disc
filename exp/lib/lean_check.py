"""Run a synthesized Lean 4 file through ``lake env lean`` and return success/error.

Single entry point: ``check_proof``. The caller supplies the Lake project and
the import list, so this module is corpus-agnostic.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ERROR_TEXT_LIMIT = 4096


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    error_text: str


def _scratch_name(decl_name: str, statement_text: str, proof_body: str, preamble: str = "") -> str:
    h = hashlib.sha256()
    h.update(decl_name.encode())
    h.update(b"\0")
    h.update(statement_text.encode())
    h.update(b"\0")
    h.update(proof_body.encode())
    h.update(b"\0")
    h.update(preamble.encode())
    return f"_expB_scratch_{h.hexdigest()[:16]}.lean"


def _render_source(
    imports: list[str], decl_name: str, statement_text: str, proof_body: str,
    preamble: str = "",
) -> str:
    import_lines = "\n".join(f"import {m}" for m in imports)
    indented_body = "\n".join("  " + line for line in proof_body.splitlines() or [""])

    # remove by if indented body contain by and make sure indentation is still correct
    if indented_body.strip().startswith("by "):
        indented_body = "  " + indented_body.strip()[3:].strip()
    preamble_block = f"\n{preamble}\n" if preamble else ""
    return (
        f"{import_lines}\n"
        f"{preamble_block}\n"
        f"theorem {decl_name} {statement_text} := by\n"
        f"{indented_body}\n"
    )


def _truncate(text: str) -> str:
    if len(text) <= ERROR_TEXT_LIMIT:
        return text
    return text[:ERROR_TEXT_LIMIT] + f"\n... [truncated, {len(text)} bytes total]"


# Matches any of the 4 Lean error/warning location formats, capturing line and col:
#   Format 1: "warning: file.lean:L:C: msg"
#   Format 2: "file.lean:L:C: error: msg"
#   Format 3: "error: file.lean:L:C: msg"
#   Format 4: "error: file.lean:L:C-L:C: msg"  (range)
_LOC_RE = re.compile(
    r'(?:(?:error|warning):\s+)?'
    r'[^\s:]+?\.lean:'
    r'(\d+):(\d+)'
    r'(?:-\d+:\d+)?:'
    r'\s*(?:(?:error|warning):\s*)?'
)


def _parse_errors(raw_output: str) -> list[tuple[int, int, str]]:
    """Return (line, col, message) tuples from Lean output, deduplicated by location."""
    results: list[tuple[int, int, str]] = []
    seen: set[tuple[int, int]] = set()
    lines = raw_output.splitlines()
    i = 0
    while i < len(lines):
        m = _LOC_RE.search(lines[i])
        if m:
            loc = (int(m.group(1)), int(m.group(2)))
            msg_head = lines[i][m.end():].strip()
            j = i + 1
            cont: list[str] = []
            while j < len(lines) and not _LOC_RE.search(lines[j]):
                if lines[j].strip():
                    cont.append(lines[j])
                j += 1
            msg_parts = ([msg_head] if msg_head else []) + cont
            msg = "\n".join(msg_parts).strip()
            if msg and loc not in seen:
                seen.add(loc)
                results.append((loc[0], loc[1], msg))
            i = j
        else:
            i += 1
    return results


def _context_snippet(source_lines: list[str], line: int, col: int) -> str:
    """Return up to 3 source lines around ``line`` with a caret at ``col`` (1-indexed)."""
    idx = line - 1
    parts: list[str] = []
    if idx > 0:
        parts.append(f"    {source_lines[idx - 1]}")
    if 0 <= idx < len(source_lines):
        parts.append(f"    {source_lines[idx]}")
        parts.append(f"    {' ' * (col - 1)}^")
    if idx + 1 < len(source_lines):
        parts.append(f"    {source_lines[idx + 1]}")
    return "\n".join(parts)


def format_error(raw_output: str, source: str, proof_body: str = "") -> str:
    """Enrich Lean's raw compiler output before it is stored and shown to the LLM.

    Returns "proof contains sorry/admit" when applicable; otherwise extracts
    each error location and renders a 3-line context snippet with a caret.
    Falls back to the raw output when no location markers are found.
    """
    # Only flag sorry/admit if it appears in the proof being tested, not in
    # preamble lemmas (which may legitimately use sorry as placeholders).
    check_text = proof_body if proof_body else source
    for kw in ("sorry", "admit"):
        if kw in check_text:
            return f"proof contains {kw}"

    errors = _parse_errors(raw_output)
    if not errors:
        return raw_output

    source_lines = source.splitlines()
    parts: list[str] = []
    for line, col, msg in errors:
        snippet = _context_snippet(source_lines, line, col)
        parts.append(f"location:\n{snippet}\nerror: {msg}")

    print(f"error: {"\n\n".join(parts)}\n")
    return "\n\n".join(parts)


def _save_scratch(
    scratch_dir: Path, decl_name: str, source: str, result: CheckResult
) -> None:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = Path(scratch_dir) / f"{ts}_{decl_name}"
    folder.mkdir(parents=True, exist_ok=True)
    if result.ok:
        comment = "/- lean_check result: ok -/"
    else:
        comment = f"/- lean_check result: FAIL\nerror:\n{result.error_text}\n-/"
    (folder / "scratch.lean").write_text(source + "\n\n" + comment + "\n")


def check_proof(
    statement_text: str,
    proof_body: str,
    *,
    lake_project: Path,
    imports: list[str],
    decl_name: str = "expB_target",
    preamble: str = "",
    timeout_s: float = 180.0,
    scratch_dir: Path | None = None,
) -> CheckResult:
    """Synthesize a .lean file in ``lake_project`` and run ``lake env lean``.

    Returns ``ok=True`` iff Lean exits 0 with no ``error:`` line in its output.
    The scratch file is always deleted before return. If ``scratch_dir`` is
    given, a copy is saved there under a timestamped subfolder with the
    result/error appended as a Lean block comment.
    """
    lake_project = Path(lake_project).resolve()
    if not lake_project.is_dir():
        return CheckResult(ok=False, error_text=f"lake project not found: {lake_project}")

    scratch_path = lake_project / _scratch_name(decl_name, statement_text, proof_body, preamble)
    source = _render_source(imports, decl_name, statement_text, proof_body, preamble)
    scratch_path.write_text(source)

    try:
        proc = subprocess.run(
            ["lake", "env", "lean", str(scratch_path.name)],
            cwd=lake_project,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        scratch_path.unlink(missing_ok=True)
        result = CheckResult(ok=False, error_text=f"lean timed out after {timeout_s}s")
        if scratch_dir is not None:
            _save_scratch(scratch_dir, decl_name, source, result)
        return result
    finally:
        scratch_path.unlink(missing_ok=True)

    combined = (proc.stdout or "") + (proc.stderr or "")
    # Preamble lemmas may use sorry, causing Lean to propagate "declaration uses 'sorry'"
    # onto every dependent declaration including ours. Strip those lines — we detect
    # sorry/admit in proof_body explicitly below.
    combined = "\n".join(
        line for line in combined.splitlines()
        if not re.search(r"declaration uses [`']sorry[`']", line)
    )
    # Lean linters (e.g. unusedSimpArgs) emit lines formatted as "error: ..."
    # even though they are warnings and the process exits 0. Strip those lines
    # only for the ok-check so real errors are still passed to format_error.
    combined_real_errors = "\n".join(
        line for line in combined.splitlines()
        if not re.search(r"error:.*\bThis\b.*\bis unused\b", line)
    )
    ok = proc.returncode == 0 and "error:" not in combined_real_errors
    if ok:
        # Lean exits 0 for sorry/admit (warning only) — intercept before returning success.
        for kw in ("sorry", "admit"):
            if kw in proof_body:
                result = CheckResult(ok=False, error_text=f"proof contains {kw}")
                if scratch_dir is not None:
                    _save_scratch(scratch_dir, decl_name, source, result)
                return result
        result = CheckResult(ok=True, error_text="")
    else:
        error_text = format_error(_truncate(combined), source, proof_body)
        result = CheckResult(ok=False, error_text=error_text)
    if scratch_dir is not None:
        _save_scratch(scratch_dir, decl_name, source, result)
    return result
