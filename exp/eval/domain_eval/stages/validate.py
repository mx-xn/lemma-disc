"""Interactive Lean validation for raw lemma statements.

Reads raw_lemmas.json, pre-filters obvious garbage, runs a batch Lean
type-check, then prompts the user to discard or fix each failing statement.
Writes the accepted set to learned_lemmas.json.

Supports two input formats:
  - legacy: ``{"lemmas": ["stmt1", "stmt2", ...]}``  — validates with sorry
  - proof-aware: ``{"lemmas": [{"statement": ..., "proof": ...}, ...]}``
    — validates against the actual proof body
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from exp.lib.lean_check import _LOC_RE, _parse_errors

_SORRY_RE = re.compile(r"declaration uses [`']sorry[`']")


# ---------------------------------------------------------------------------
# Lean checking (binder-syntax statements)
# ---------------------------------------------------------------------------

def _batch_check(
    stmts: dict[int, str],
    lake_project: Path,
    imports: list[str],
) -> dict[int, str]:
    """Lean-check {idx: statement} using sorry as placeholder proof.

    Returns {idx: error_text} for failing statements.
    """
    if not stmts:
        return {}

    import_block = "\n".join(f"import {m}" for m in imports)
    lines: list[str] = import_block.splitlines() if import_block else []
    lines.append("")

    current_line = len(lines) + 1
    decl_line: dict[int, int] = {}
    for idx in sorted(stmts):
        decl_line[idx] = current_line
        decl_text = f"lemma validate_{idx} {stmts[idx]} := by sorry"
        lines.append(decl_text)
        current_line += decl_text.count('\n') + 1

    return _run_lean_check(lines, decl_line, lake_project, filter_sorry=True)


def _batch_check_with_proofs(
    entries: dict[int, tuple[str, str]],
    lake_project: Path,
    imports: list[str],
) -> dict[int, str]:
    """Lean-check {idx: (statement, proof)} using the actual proof body.

    Returns {idx: error_text} for failing entries.
    """
    if not entries:
        return {}

    import_block = "\n".join(f"import {m}" for m in imports)
    lines: list[str] = import_block.splitlines() if import_block else []
    lines.append("")

    current_line = len(lines) + 1
    decl_line: dict[int, int] = {}
    for idx in sorted(entries):
        stmt, proof = entries[idx]
        decl_line[idx] = current_line
        decl_text = f"lemma validate_{idx} {stmt} := {proof}"
        lines.append(decl_text)
        current_line += decl_text.count('\n') + 1

    return _run_lean_check(lines, decl_line, lake_project, filter_sorry=False)


def _run_lean_check(
    lines: list[str],
    decl_line: dict[int, int],
    lake_project: Path,
    filter_sorry: bool,
) -> dict[int, str]:
    source = "\n".join(lines) + "\n"
    h = hashlib.sha256(source.encode()).hexdigest()[:16]
    scratch = lake_project / f"_validate_{h}.lean"
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
        return {i: "lean timed out" for i in decl_line}
    finally:
        scratch.unlink(missing_ok=True)

    combined = (proc.stdout or "") + (proc.stderr or "")
    if filter_sorry:
        combined = "\n".join(
            line for line in combined.splitlines()
            if not _SORRY_RE.search(line)
        )
    # Drop warning-only diagnostic blocks; only actual errors should fail a lemma.
    filtered: list[str] = []
    in_warning = False
    for raw_line in combined.splitlines():
        if _LOC_RE.search(raw_line):
            in_warning = (
                re.search(r'\bwarning:', raw_line) is not None
                and re.search(r'\berror:', raw_line) is None
            )
        if not in_warning:
            filtered.append(raw_line)
    combined = "\n".join(filtered)
    if proc.returncode == 0 and "error:" not in combined:
        return {}

    sorted_decls = sorted(decl_line.items(), key=lambda kv: kv[1])

    def _owner(line_num: int) -> int | None:
        owner: int | None = None
        for idx, start in sorted_decls:
            if start <= line_num:
                owner = idx
        return owner

    broken: dict[int, list[str]] = {}
    for line, _col, msg in _parse_errors(combined):
        o = _owner(line)
        if o is not None:
            broken.setdefault(o, []).append(msg)
    return {idx: "\n".join(msgs) for idx, msgs in broken.items()}


# ---------------------------------------------------------------------------
# Pre-filter heuristics
# ---------------------------------------------------------------------------

def _brackets_balanced(stmt: str) -> bool:
    close_for: dict[str, str] = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    for ch in stmt:
        if ch in close_for:
            stack.append(close_for[ch])
        elif ch in close_for.values():
            if not stack or stack[-1] != ch:
                return False
            stack.pop()
    return not stack


def _truncated(stmt: str) -> bool:
    s = stmt.rstrip()
    if not s.endswith("="):
        return False
    return len(s) < 2 or s[-2] not in ("=", ":", ">")


def _prefilter_stmts(stmts: list[str]) -> tuple[list[str], int]:
    kept: list[str] = []
    dropped = 0
    for s in stmts:
        s = s.strip()
        if not s or not _brackets_balanced(s) or _truncated(s):
            dropped += 1
        else:
            kept.append(s)
    return kept, dropped


def _prefilter_entries(
    entries: list[dict[str, str]],
) -> tuple[list[dict[str, str]], int]:
    kept: list[dict[str, str]] = []
    dropped = 0
    for e in entries:
        stmt = e.get("statement", "").strip()
        if not stmt or not _brackets_balanced(stmt) or _truncated(stmt):
            dropped += 1
        else:
            kept.append({**e, "statement": stmt})
    return kept, dropped


# ---------------------------------------------------------------------------
# Single re-check helpers
# ---------------------------------------------------------------------------

def _recheck_stmt(stmt: str, lake_project: Path, imports: list[str]) -> str | None:
    broken = _batch_check({0: stmt}, lake_project, imports)
    return broken.get(0)


def _recheck_entry(
    stmt: str, proof: str, lake_project: Path, imports: list[str]
) -> str | None:
    broken = _batch_check_with_proofs({0: (stmt, proof)}, lake_project, imports)
    return broken.get(0)


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _handle_failure_stmt(
    stmt: str,
    error: str,
    failure_num: int,
    total_failures: int,
    lake_project: Path,
    imports: list[str],
) -> str | None:
    current_stmt = stmt
    current_error = error
    while True:
        print(f"\n── Failure {failure_num}/{total_failures} "
              f"{'─' * max(0, 50 - len(str(failure_num)) - len(str(total_failures)))}")
        print(f"Statement:\n  {current_stmt}")
        print(f"Error:\n  {current_error.strip()}")
        print()
        choice = input("[d] discard   [e] edit > ").strip().lower()
        if choice == "d":
            return None
        if choice == "e":
            print("Enter corrected statement (single line):")
            corrected = input("> ").strip()
            if not corrected:
                print("Empty — try again.")
                continue
            print("[validate] checking...", end=" ", flush=True)
            err = _recheck_stmt(corrected, lake_project, imports)
            if err is None:
                print("accepted.")
                return corrected
            print("still failing.")
            current_stmt = corrected
            current_error = err


def _handle_failure_entry(
    stmt: str,
    proof: str,
    error: str,
    failure_num: int,
    total_failures: int,
    lake_project: Path,
    imports: list[str],
) -> dict[str, str] | None:
    current_stmt = stmt
    current_proof = proof
    current_error = error
    while True:
        print(f"\n── Failure {failure_num}/{total_failures} "
              f"{'─' * max(0, 50 - len(str(failure_num)) - len(str(total_failures)))}")
        print(f"Statement:\n  {current_stmt}")
        print(f"Proof:\n  {current_proof}")
        print(f"Error:\n  {current_error.strip()}")
        print()
        choice = input("[d] discard   [s] edit statement   [p] edit proof > ").strip().lower()
        if choice == "d":
            return None
        if choice in ("s", "p"):
            if choice == "s":
                print("Enter corrected statement (single line):")
                current_stmt = input("> ").strip() or current_stmt
            else:
                print("Enter corrected proof body (single line; use \\n for newlines):")
                raw = input("> ").strip()
                if raw:
                    current_proof = raw.replace("\\n", "\n")
            if not current_stmt:
                print("Empty statement — try again.")
                continue
            print("[validate] checking...", end=" ", flush=True)
            err = _recheck_entry(current_stmt, current_proof, lake_project, imports)
            if err is None:
                print("accepted.")
                return {"statement": current_stmt, "proof": current_proof}
            print("still failing.")
            current_error = err


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_validate(
    lemmas_path: Path,
    output_dir: Path,
    lake_project: Path,
    imports: list[str],
    force: bool,
) -> None:
    output_dir = Path(output_dir)
    learned_path = output_dir / "learned_lemmas.json"

    if learned_path.exists() and not force:
        print(f"[skip] {learned_path} exists (use --force to overwrite)", file=sys.stderr)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    lake_project = Path(lake_project).resolve()

    raw = json.loads(Path(lemmas_path).read_text())
    raw_entries = raw.get("lemmas", []) if isinstance(raw, dict) else list(raw)
    print(f"[validate] {len(raw_entries)} raw entry/entries loaded", file=sys.stderr)

    proof_aware = raw_entries and isinstance(raw_entries[0], dict)

    if proof_aware:
        kept_dicts, n_dropped = _prefilter_entries(raw_entries)
        if n_dropped:
            print(
                f"[validate] pre-filter: dropped {n_dropped} malformed statement(s)",
                file=sys.stderr,
            )
        if not kept_dicts:
            print("[validate] nothing to check after pre-filter", file=sys.stderr)
            learned_path.write_text(json.dumps({"lemmas": []}, ensure_ascii=False, indent=2))
            return

        print(f"[validate] Lean-checking {len(kept_dicts)} lemma(s) with proofs...", file=sys.stderr)
        to_check = {i: (e["statement"], e["proof"]) for i, e in enumerate(kept_dicts)}
        broken = _batch_check_with_proofs(to_check, lake_project, imports)

        n_pass = len(kept_dicts) - len(broken)
        print(f"[validate] {n_pass} passed, {len(broken)} failed", file=sys.stderr)

        if not broken:
            learned_path.write_text(
                json.dumps({"lemmas": kept_dicts}, ensure_ascii=False, indent=2)
            )
            print(f"[validate] wrote {len(kept_dicts)} lemma(s) to {learned_path}", file=sys.stderr)
            return

        accepted: list[dict[str, str]] = []
        failure_num = 0
        for i, entry in enumerate(kept_dicts):
            if i not in broken:
                accepted.append(entry)
                continue
            failure_num += 1
            result = _handle_failure_entry(
                stmt=entry["statement"],
                proof=entry["proof"],
                error=broken[i],
                failure_num=failure_num,
                total_failures=len(broken),
                lake_project=lake_project,
                imports=imports,
            )
            if result is not None:
                accepted.append(result)

        print(f"\n[validate] {len(accepted)} lemma(s) accepted", file=sys.stderr)
        learned_path.write_text(
            json.dumps({"lemmas": accepted}, ensure_ascii=False, indent=2)
        )

    else:
        raw_stmts: list[str] = [e if isinstance(e, str) else e.get("statement", "") for e in raw_entries]
        kept, n_dropped = _prefilter_stmts(raw_stmts)
        if n_dropped:
            print(
                f"[validate] pre-filter: dropped {n_dropped} malformed statement(s)",
                file=sys.stderr,
            )
        if not kept:
            print("[validate] nothing to check after pre-filter", file=sys.stderr)
            learned_path.write_text(json.dumps({"lemmas": []}, ensure_ascii=False, indent=2))
            return

        print(f"[validate] Lean-checking {len(kept)} statement(s)...", file=sys.stderr)
        broken = _batch_check({i: s for i, s in enumerate(kept)}, lake_project, imports)

        n_pass = len(kept) - len(broken)
        print(f"[validate] {n_pass} passed, {len(broken)} failed", file=sys.stderr)

        if not broken:
            learned_path.write_text(
                json.dumps({"lemmas": kept}, ensure_ascii=False, indent=2)
            )
            print(f"[validate] wrote {len(kept)} lemma(s) to {learned_path}", file=sys.stderr)
            return

        accepted_stmts: list[str] = []
        failure_num = 0
        for i, stmt in enumerate(kept):
            if i not in broken:
                accepted_stmts.append(stmt)
                continue
            failure_num += 1
            result = _handle_failure_stmt(
                stmt=stmt,
                error=broken[i],
                failure_num=failure_num,
                total_failures=len(broken),
                lake_project=lake_project,
                imports=imports,
            )
            if result is not None:
                accepted_stmts.append(result)

        print(f"\n[validate] {len(accepted_stmts)} lemma(s) accepted", file=sys.stderr)
        learned_path.write_text(
            json.dumps({"lemmas": accepted_stmts}, ensure_ascii=False, indent=2)
        )

    print(f"[validate] wrote to {learned_path}", file=sys.stderr)
