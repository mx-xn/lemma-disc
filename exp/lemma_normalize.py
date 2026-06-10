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


# ---------------------------------------------------------------------------
# BEGIN free-variable workaround
#
# Phase4 lemma extraction sometimes omits free identifiers (e.g. n, x, y) from
# the binder prefix and from the ``premises`` list — apparently because Lean's
# surface display elides section-bound / outer-scope variables, and the
# extractor preserves that display form. As a result two alpha-equivalent
# statements that differ only by free-name spelling hash to different
# ``canonical_key``s and bucket apart.
#
# This block renames such free identifiers to ``_f0, _f1, ...`` (separate
# counter from ``_v*`` so they remain visually distinguishable while debugging)
# so syntactic clustering treats them as alpha-equivalent.
#
# TO REMOVE when phase4 lifts all free identifiers into top-level binders and
# reports them in ``premises``:
#   1. Delete this block (regex, keyword set, and ``rename_free_variables``).
#   2. Remove the ``rename_free_variables(...)`` wrapper from ``canonical_key``
#      so it reads simply ``normalize_bound_names(strip_type_binders(stmt))``.
# Nothing else in the codebase needs to change.
# ---------------------------------------------------------------------------

_FREE_IDENT_RE = re.compile(r"(?<![A-Za-z0-9_'.])([a-z][a-zA-Z0-9_']*)")
_FREE_IDENT_KEYWORDS = frozenset({
    "fun", "let", "in", "if", "then", "else", "match", "with",
    "do", "by", "have", "show", "this", "sorry", "rfl",
})


def rename_free_variables(stmt: str) -> str:
    """Rename free term-variable identifiers to ``_f0, _f1, ...``.

    A "free identifier" here is any token matching ``[a-z][a-zA-Z0-9_']*``
    that is not preceded by ``.`` or another identifier character, is not a
    top-level bound name of ``stmt``, and is not a Lean keyword. Renaming
    follows first-appearance order.
    """
    bound = set(_bound_names(stmt))
    seen: dict[str, str] = {}

    def _sub(m: re.Match) -> str:
        nm = m.group(1)
        if nm in bound or nm in _FREE_IDENT_KEYWORDS:
            return nm
        if nm not in seen:
            seen[nm] = f"_f{len(seen)}"
        return seen[nm]

    return _FREE_IDENT_RE.sub(_sub, stmt)

# END free-variable workaround
# ---------------------------------------------------------------------------


def canonical_key(stmt: str) -> str:
    """Equivalence-class key: type-binder-stripped + alpha-renamed
    (+ free-var-renamed; see workaround block above)."""
    return rename_free_variables(normalize_bound_names(strip_type_binders(stmt)))
