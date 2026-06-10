"""Load the input theorem set for Experiment B.

Input shape (preferred — object form):

    {
      "lake_project": "data/input/MiniCodePropsLeanSrc",
      "imports": ["Mathlib"],
      "theorems": [
        {"theorem_id": "prop_07",
         "lean_path": "LeanSrc/Properties.lean",
         "statement_text": "(n m : Nat) : ((n + m) - n = m)"}
      ]
    }

A top-level list of theorem records is also accepted; in that case
``lake_project`` and ``imports`` must be supplied by the caller (typically
via CLI flags in ``run.py``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theorem:
    theorem_id: str
    lean_path: str          # metadata: where the theorem came from
    statement_text: str     # binders + ": conclusion"
    local_ctx: str = ""     # local definitions preceding the theorem in the same file


@dataclass(frozen=True)
class TheoremSet:
    lake_project: Path | None
    imports: list[str] | None
    theorems: list[Theorem]


def _parse_theorem(obj: dict, index: int) -> Theorem:
    try:
        return Theorem(
            theorem_id=str(obj["theorem_id"]),
            lean_path=str(obj.get("lean_path", "")),
            statement_text=str(obj["statement_text"]),
            local_ctx=str(obj.get("local_ctx", "")),
        )
    except KeyError as e:
        raise ValueError(f"theorem #{index} missing required field {e}") from None


@dataclass(frozen=True)
class CandidateSet:
    entries: dict[str, list[str]]   # theorem_id -> [statement, ...]


def load_candidates(path: Path) -> CandidateSet:
    """Parse ``path`` into a ``CandidateSet``.

    Expected shape: ``{"theorem_id": ["stmt1", "stmt2", ...], ...}``.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("candidates file must be a JSON object mapping theorem_id -> [stmts]")
    entries: dict[str, list[str]] = {}
    for tid, stmts in data.items():
        if not isinstance(stmts, list) or not all(isinstance(s, str) for s in stmts):
            raise ValueError(f"candidates for {tid!r} must be a list of strings")
        entries[str(tid)] = list(stmts)
    return CandidateSet(entries=entries)


def load_theorems(path: Path) -> TheoremSet:
    """Parse ``path`` into a ``TheoremSet``.

    Accepts either the object form ({lake_project, imports, theorems}) or a
    bare list of theorem records.
    """
    data = json.loads(Path(path).read_text())

    if isinstance(data, list):
        return TheoremSet(
            lake_project=None,
            imports=None,
            theorems=[_parse_theorem(t, i) for i, t in enumerate(data)],
        )

    if not isinstance(data, dict) or "theorems" not in data:
        raise ValueError(
            "theorems file must be a list or an object with a 'theorems' key"
        )

    lake_project = data.get("lake_project")
    imports = data.get("imports")
    if imports is not None and not all(isinstance(i, str) for i in imports):
        raise ValueError("'imports' must be a list of strings")

    return TheoremSet(
        lake_project=Path(lake_project) if lake_project else None,
        imports=list(imports) if imports else None,
        theorems=[_parse_theorem(t, i) for i, t in enumerate(data["theorems"])],
    )
