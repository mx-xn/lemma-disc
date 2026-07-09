"""Lean round-trip + on-disk cache for elaborating lemma statements into term trees."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from lemma_generalization.models import Statement

_DUMPTERM_SOURCE = (Path(__file__).resolve().parents[1] / "lean" / "DumpTerm.lean").read_text()
DECL_PREFIX = "__gen_"


def _decl_name(fragment_id: int) -> str:
    """f"__gen_{fragment_id}" -- the scratch declaration name for one lemma."""
    return f"{DECL_PREFIX}{fragment_id}"


def _fragment_id_of(decl_name: str) -> int:
    """Inverse of _decl_name; strips DECL_PREFIX and parses the int suffix."""
    return int(decl_name.removeprefix(DECL_PREFIX))


def _cache_path(cache_dir: Path, statement: str, imports: list[str], lake_project: Path) -> Path:
    """cache_dir / f"{sha256(statement, imports, lake_project)}.json" -- elaborating a
    statement is a pure function of this triple, so it's the whole cache key."""
    h = hashlib.sha256()
    h.update(statement.encode())
    h.update(b"\0")
    h.update(",".join(imports).encode())
    h.update(b"\0")
    h.update(str(lake_project).encode())
    return cache_dir / f"{h.hexdigest()}.json"


def _read_cache(path: Path) -> dict[str, Any] | None:
    """Parsed JSON payload ({"statement": ...} or {"error": ...}), or None if no entry yet."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    """Write payload as-is; caller decides the {"statement"|"error"} shape."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False))


def _render_batch(batch: list[tuple[int, str]], imports: list[str]) -> str:
    """Scratch .lean source: project imports, then DumpTerm.lean verbatim (its own
    `import Lean` must stay contiguous with the project imports above it -- Lean
    requires all imports before any other command), then one
    `theorem __gen_i <statement> := sorry` per (fragment_id, statement) in batch,
    then a trailing `#eval DumpTerm.dumpMatching "__gen_"`."""
    lines = [f"import {m}" for m in imports]
    lines.append(_DUMPTERM_SOURCE)
    for fragment_id, statement in batch:
        lines.append(f"theorem {_decl_name(fragment_id)} {statement} := sorry")
    lines.append(f'#eval DumpTerm.dumpMatching "{DECL_PREFIX}"')
    return "\n".join(lines)


def _run_lean(scratch_path: Path, lake_project: Path, timeout_s: float) -> str:
    """`lake env lean <scratch>` in lake_project, combined stdout+stderr.
    Same subprocess pattern as lemma_emission.validator._run_lean."""
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", scratch_path.name],
            cwd=lake_project,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"lean timed out after {timeout_s}s"
    return (proc.stdout or "") + (proc.stderr or "")


def _parse_output(raw: str, expected_fragment_ids: set[int]) -> tuple[dict[int, Statement], dict[int, str]]:
    """JSON lines ({"decl_name","statement"} or {"decl_name","error"}) are parsed
    directly into the two dicts, keyed by fragment_id. Any fragment_id in
    expected_fragment_ids that got neither a statement nor a JSON error line
    (its `theorem` failed to elaborate at all, so DumpTerm never ran on it) is
    marked failed using whatever non-JSON, non-"declaration uses" diagnostic text
    is left over in raw -- deliberately not attributed per-line (inputs are
    pre-validated by phase 5, so this path is a rare defensive fallback, not
    something worth a full line-attribution parser for)."""
    statements: dict[int, Statement] = {}
    errors: dict[int, str] = {}
    leftover: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("{"):
            obj = json.loads(stripped)
            fragment_id = _fragment_id_of(obj["decl_name"])
            if "error" in obj:
                errors[fragment_id] = obj["error"]
            else:
                statements[fragment_id] = Statement.from_dict(obj["statement"])
        elif "declaration uses" not in stripped:
            leftover.append(line)

    missing = expected_fragment_ids - statements.keys() - errors.keys()
    if missing:
        diagnostic = "\n".join(leftover).strip() or "no diagnostic output captured"
        for fragment_id in missing:
            errors[fragment_id] = diagnostic

    return statements, errors


def _elaborate_batch(
    batch: list[tuple[int, str]],
    lake_project: Path,
    imports: list[str],
    timeout_s: float,
) -> tuple[dict[int, Statement], dict[int, str]]:
    """Render -> write scratch file under lake_project -> run -> parse, deleting
    the scratch file in a finally block (mirrors validator._validate_batch)."""
    source = _render_batch(batch, imports)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", dir=lake_project, delete=False
    ) as f:
        scratch_path = Path(f.name)
        f.write(source)

    try:
        raw = _run_lean(scratch_path, lake_project, timeout_s)
    finally:
        scratch_path.unlink(missing_ok=True)

    expected_fragment_ids = {fragment_id for fragment_id, _ in batch}
    return _parse_output(raw, expected_fragment_ids)


def elaborate_statements(
    statements: dict[int, str],
    *,
    lake_project: Path,
    imports: list[str],
    cache_dir: Path,
    batch_size: int = 50,
    timeout_s: float = 300.0,
) -> tuple[dict[int, Statement], dict[int, str]]:
    """Public entry point. For each (fragment_id, statement): cache hit -> use
    directly; miss -> collect for batching. Misses are grouped into batch_size
    chunks and run through _elaborate_batch; every fresh result (success or
    error) is written back to cache before returning. A fragment_id appears in
    exactly one of the two returned dicts, never both, never neither."""
    lake_project = Path(lake_project).resolve()
    cache_dir = Path(cache_dir)

    results: dict[int, Statement] = {}
    errors: dict[int, str] = {}
    misses: list[tuple[int, str]] = []

    for fragment_id, statement in statements.items():
        path = _cache_path(cache_dir, statement, imports, lake_project)
        cached = _read_cache(path)
        if cached is None:
            misses.append((fragment_id, statement))
        elif "error" in cached:
            errors[fragment_id] = cached["error"]
        else:
            results[fragment_id] = Statement.from_dict(cached["statement"])

    for i in range(0, len(misses), batch_size):
        batch = misses[i : i + batch_size]
        batch_statements, batch_errors = _elaborate_batch(batch, lake_project, imports, timeout_s)
        results.update(batch_statements)
        errors.update(batch_errors)
        for fragment_id, statement in batch:
            path = _cache_path(cache_dir, statement, imports, lake_project)
            if fragment_id in batch_statements:
                _write_cache(path, {"statement": batch_statements[fragment_id].to_dict()})
            else:
                _write_cache(path, {"error": batch_errors[fragment_id]})

    return results, errors
