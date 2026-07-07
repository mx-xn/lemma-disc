"""Pure syntactic transforms on Lean 4 lemma statement strings.

No I/O. Reuses bracket-parsing helpers from ``count_hyps``.

Order matters: ``strip_type_binders`` must run before ``normalize_bound_names``,
since stripping changes which names are bound. The ``canonical_key`` helper
encapsulates this so callers can't get it wrong.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_hyps import _binder_groups, _first_colon, _strip_brackets  # noqa: E402


_IDENT_CHAR = r"[A-Za-z0-9_'Ͱ-Ͽἀ-῿⁰-₟℀-⅏✝]"


def strip_type_binders(stmt: str) -> str:
    """Remove ``(α : Type u_1)`` / ``(β : Sort u)`` style binders.

    These binders are normally inferable from later binders (e.g.
    ``(xs : List α)``) and pollute clustering keys without carrying
    mathematical content.
    """
    colon = _first_colon(stmt)
    if colon is None:
        return stmt
    prefix, tail = stmt[:colon], stmt[colon:]
    kept: list[str] = []
    for g in _binder_groups(prefix):
        inner = _strip_brackets(g)
        c = _first_colon(inner)
        if c is None:
            kept.append(g)
            continue
        rhs = inner[c + 1:].strip()
        if rhs.startswith(("Type", "Sort")):
            continue
        kept.append(g)
    new_prefix = " ".join(kept)
    return (new_prefix + " " + tail.lstrip()) if new_prefix else tail.lstrip()


def _bound_names(stmt: str) -> list[str]:
    colon = _first_colon(stmt)
    if colon is None:
        return []
    names: list[str] = []
    for group in _binder_groups(stmt[:colon]):
        inner = _strip_brackets(group)
        c = _first_colon(inner)
        if c is None:
            continue
        for tok in inner[:c].split():
            if tok:
                names.append(tok)
    return names


def normalize_bound_names(stmt: str) -> str:
    """Rename bound variables to ``_v0, _v1, ...`` in left-to-right order.

    Imperfect (ignores shadowing inside binder bodies) but sufficient for
    collapsing the obvious alpha-equivalent duplicates.
    """
    names = _bound_names(stmt)
    if not names:
        return " ".join(stmt.split())
    seen: dict[str, str] = {}
    for nm in names:
        if nm not in seen:
            seen[nm] = f"_v{len(seen)}"
    result = stmt
    # Longer names first to avoid prefix collisions.
    for nm in sorted(seen.keys(), key=len, reverse=True):
        pattern = re.compile(
            rf"(?<!{_IDENT_CHAR}){re.escape(nm)}(?!{_IDENT_CHAR})"
        )
        result = pattern.sub(seen[nm], result)
    return " ".join(result.split())


def canonical_key(stmt: str) -> str:
    """Equivalence-class key: type-binder-stripped + alpha-renamed."""
    return normalize_bound_names(strip_type_binders(stmt))
