#!/usr/bin/env python3
"""Two complexity metrics for Lean 4 lemma statements.

Both metrics ignore the lemma's overall conclusion (the term after the final
top-level ``:``) and sum contributions across the top-level binders.

num_hyps  —  ``count_hyps`` (context-match difficulty)
------------------------------------------------------
A binder ``(name : T)`` contributes only when T is proposition-valued:

  1. T is a type/sort (``Type u_1``, ``Sort``, ``ℕ``, ``List α``, bare term
     variable like ``x : α``) → 0.
  2. T is a function or quantifier type (top-level ``→`` / ``->`` present, or
     T starts with ``∀`` / ``∃``) → 1.  Internal conjunctions inside a
     function body are NOT unfolded; the whole obligation counts as one.
  3. T is a top-level conjunction ``A ∧ B ∧ …`` (no top-level ``→``) →
     recurse into each conjunct and sum.
  4. Any other proposition (equality, inequality, …) → 1.

proof_effort  —  ``proof_effort`` (total propositional work)
------------------------------------------------------------
Like num_hyps, but also descends into arrows and quantifier bodies:

  * Non-prop binder → 0.
  * Conjunction ``A ∧ B ∧ …`` → sum of effort of each conjunct.
  * Arrow ``A → B`` → ``effort(A) + effort(B)`` (recurse into both sides).
  * Quantifier ``∀ binders, body`` / ``∃ binders, body`` → effort over
    prop-typed binders plus effort of the body.
  * Negation ``¬ P`` → ``effort(P) + 1`` (as if desugared to ``P → False``).
  * Any other proposition (leaf) → 1.

The two metrics target different reuse failure modes: num_hyps captures how
many distinct things the surrounding context must supply to apply the lemma;
proof_effort captures how much nested propositional structure has to be
threaded through, even if much of it sits inside one outer binder.

Usage
-----
Single statement (prints ``num_hyps\\tproof_effort``):
    python exp/count_hyps.py --stmt "(h : a = b) (n : ℕ) : a = b"

JSON lemma file (TSV with both columns, or --json for structured output):
    python exp/count_hyps.py data/prop_85_lemmas.json
    python exp/count_hyps.py data/prop_85_lemmas.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

# ---------------------------------------------------------------------------
# Bracket-depth utilities
# ---------------------------------------------------------------------------

_OPEN_TO_CLOSE: dict[str, str] = {"(": ")", "[": "]", "{": "}"}
_CLOSE_CHARS: frozenset[str] = frozenset(_OPEN_TO_CLOSE.values())


def _adj(ch: str, d: int) -> int:
    if ch in _OPEN_TO_CLOSE:
        return d + 1
    if ch in _CLOSE_CHARS:
        return max(0, d - 1)
    return d


def _first_colon(s: str) -> int | None:
    """Index of the first ':' at bracket depth 0, or None."""
    d = 0
    for i, ch in enumerate(s):
        d = _adj(ch, d)
        if ch == ":" and d == 0:
            return i
    return None


def _has_tok(s: str, tok: str) -> bool:
    """True if ``tok`` appears at bracket depth 0 in ``s``."""
    d = 0
    for i, ch in enumerate(s):
        d = _adj(ch, d)
        if d == 0 and s.startswith(tok, i):
            return True
    return False


def _split_tok(s: str, sep: str) -> list[str]:
    """Split ``s`` on ``sep`` occurrences at bracket depth 0."""
    parts: list[str] = []
    d, i, start = 0, 0, 0
    while i < len(s):
        ch = s[i]
        d = _adj(ch, d)
        if d == 0 and s.startswith(sep, i):
            parts.append(s[start:i].strip())
            i += len(sep)
            start = i
            continue
        i += 1
    parts.append(s[start:].strip())
    return [p for p in parts if p]


def _strip_brackets(s: str) -> str:
    """Remove matched outermost bracket pairs repeatedly."""
    s = s.strip()
    while len(s) >= 2 and s[0] in _OPEN_TO_CLOSE:
        close = _OPEN_TO_CLOSE[s[0]]
        if s[-1] != close:
            break
        # verify the opening bracket really closes at the very last char
        d = 0
        closes_at_end = False
        for i, ch in enumerate(s):
            if ch == s[0]:
                d += 1
            elif ch == close:
                d -= 1
                if d == 0:
                    closes_at_end = i == len(s) - 1
                    break
        if not closes_at_end:
            break
        s = s[1:-1].strip()
    return s


# ---------------------------------------------------------------------------
# Proposition heuristic
# ---------------------------------------------------------------------------

_NON_PROP_PREFIXES = ("Type", "Sort")
_NON_PROP_ATOMS = frozenset({
    "ℕ", "Nat", "Int", "ℤ", "Bool", "String", "Char", "Float",
    "Unit", "Empty", "PUnit", "UInt8", "UInt16", "UInt32", "UInt64",
})
_PROP_CONNECTIVES = (
    "=", "≠", "↔", "∧", "∨", "→", "->", "≤", "≥", "<", ">", "∈", "⊆", "⊂",
)
_PROP_STARTERS = ("∀", "∃", "¬")


def _is_prop(s: str) -> bool:
    """Heuristic: return True if ``s`` is proposition-valued."""
    s = _strip_brackets(s)
    if not s:
        return False
    for p in _NON_PROP_PREFIXES:
        if s.startswith(p):
            return False
    if s in _NON_PROP_ATOMS:
        return False
    for p in _PROP_STARTERS:
        if s.startswith(p):
            return True
    if s in ("True", "False"):
        return True
    if any(c in s for c in _PROP_CONNECTIVES):
        return True
    # bare identifier: lowercase → term variable, not Prop
    tokens = s.split()
    if tokens:
        first = tokens[0]
        alnum = first.replace("'", "").replace("_", "").replace("✝", "")
        if alnum and alnum[0].islower():
            return False
        # single non-ASCII letter (α, β, γ …) → type variable
        if len(first) == 1 and not first.isascii():
            return False
    return False


# ---------------------------------------------------------------------------
# Core counting
# ---------------------------------------------------------------------------

def count_hyps_in_type(s: str) -> int:
    """Hypothesis count for a single binder type string.

    Applies rules 1–4 from the module docstring.
    """
    s = _strip_brackets(s)
    if not _is_prop(s):
        return 0                                    # rule 1
    if s.startswith(("∀", "∃")):
        return 1                                    # rule 2 (quantifier)
    if _has_tok(s, "→") or _has_tok(s, "->"):
        return 1                                    # rule 2 (function type)
    if _has_tok(s, "∧"):
        return sum(count_hyps_in_type(p)            # rule 3 (conjunction)
                   for p in _split_tok(s, "∧"))
    return 1                                        # rule 4


def _binder_groups(prefix: str) -> list[str]:
    """Extract each bracketed binder group from a binder prefix string."""
    groups: list[str] = []
    i, n = 0, len(prefix)
    while i < n:
        while i < n and prefix[i].isspace():
            i += 1
        if i >= n:
            break
        if prefix[i] not in _OPEN_TO_CLOSE:
            # bare token (e.g. implicit universe var) — skip
            while i < n and not prefix[i].isspace() and prefix[i] not in _OPEN_TO_CLOSE:
                i += 1
            continue
        open_ch, close_ch = prefix[i], _OPEN_TO_CLOSE[prefix[i]]
        d, j = 0, i
        while j < n:
            if prefix[j] == open_ch:
                d += 1
            elif prefix[j] == close_ch:
                d -= 1
                if d == 0:
                    j += 1
                    break
            j += 1
        groups.append(prefix[i:j])
        i = j
    return groups


def count_hyps(statement: str) -> int:
    """Count proposition-valued hypotheses in a full Lean 4 statement string."""
    return _sum_over_binders(statement, count_hyps_in_type)


# ---------------------------------------------------------------------------
# Proof effort (recursive variant)
# ---------------------------------------------------------------------------

def _split_quantifier_body(s: str) -> tuple[list[str], str]:
    """Split ``∀ binders, body`` or ``∃ binders, body`` on the top-level comma."""
    rest = s[1:].lstrip()
    d = 0
    for i, ch in enumerate(rest):
        d = _adj(ch, d)
        if d == 0 and ch == ",":
            return _binder_groups(rest[:i].strip()), rest[i + 1:].strip()
    return [], rest


def _find_leftmost_arrow(s: str) -> tuple[int | None, int]:
    """Return ``(index, length)`` of the leftmost top-level → / ->, else (None, 0)."""
    d = 0
    for i, ch in enumerate(s):
        d = _adj(ch, d)
        if d == 0:
            if s.startswith("→", i):
                return i, 1
            if s.startswith("->", i):
                return i, 2
    return None, 0


def _binder_type_effort(binder_text: str) -> int:
    """Effort for a ∀-bound binder text like ``(h : P)`` / ``(x : ℕ)``."""
    inner = _strip_brackets(binder_text)
    c = _first_colon(inner)
    if c is None:
        return 0
    return proof_effort_in_type(inner[c + 1:].strip())


def _antecedent_effort(s: str) -> int:
    """Effort for an arrow antecedent (named binder ``(h : P)`` or bare ``P``)."""
    inner = _strip_brackets(s)
    c = _first_colon(inner)
    if c is not None:
        return proof_effort_in_type(inner[c + 1:].strip())
    return proof_effort_in_type(s)


def proof_effort_in_type(s: str) -> int:
    """Total propositional sub-obligations encountered inside a binder type.

    Descends through arrows, quantifiers, conjunctions and negation; see the
    module docstring for the per-construct contributions.
    """
    s = _strip_brackets(s)
    if not _is_prop(s):
        return 0
    if s.startswith("¬"):
        return proof_effort_in_type(s[1:].lstrip()) + 1   # ¬ P ≡ P → False
    if s.startswith(("∀", "∃")):
        binders, body = _split_quantifier_body(s)
        return (sum(_binder_type_effort(b) for b in binders)
                + proof_effort_in_type(body))
    pos, alen = _find_leftmost_arrow(s)
    if pos is not None:
        return (_antecedent_effort(s[:pos].strip())
                + proof_effort_in_type(s[pos + alen:].strip()))
    if _has_tok(s, "∧"):
        return sum(proof_effort_in_type(c) for c in _split_tok(s, "∧"))
    return 1


def proof_effort(statement: str) -> int:
    """Total proof effort for a full Lean 4 statement (sum over top-level binders)."""
    return _sum_over_binders(statement, proof_effort_in_type)


def _sum_over_binders(statement: str, score) -> int:
    colon = _first_colon(statement)
    if colon is None:
        return 0
    total = 0
    for group in _binder_groups(statement[:colon]):
        inner = _strip_brackets(group)
        c = _first_colon(inner)
        if c is None:
            continue
        total += score(inner[c + 1:].strip())
    return total


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _load_lemmas(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "lemmas" in data:
        return list(data["lemmas"])
    if isinstance(data, list):
        return list(data)
    return [data]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", nargs="?", type=Path,
                        help="lemma JSON file (omit when using --stmt)")
    parser.add_argument("--stmt", metavar="STATEMENT",
                        help="count hyps for a single statement string and exit")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of TSV")
    args = parser.parse_args(argv)

    if args.stmt:
        print(f"{count_hyps(args.stmt)}\t{proof_effort(args.stmt)}")
        return 0

    if args.input is None:
        parser.error("provide an input file or use --stmt")

    lemmas = _load_lemmas(args.input)
    rows = []
    for lem in lemmas:
        stmt = lem.get("statement", "")
        rows.append({
            "fragment_id": lem.get("fragment_id"),
            "decl_name": lem.get("decl_name"),
            "num_hyps": count_hyps(stmt) if stmt else 0,
            "proof_effort": proof_effort(stmt) if stmt else 0,
        })

    if args.json:
        print(json.dumps({"input": str(args.input), "lemmas": rows}, indent=2))
    else:
        print("fragment_id\tdecl_name\tnum_hyps\tproof_effort")
        for r in rows:
            fid = "" if r["fragment_id"] is None else str(r["fragment_id"])
            dn = r["decl_name"] or ""
            print(f"{fid}\t{dn}\t{r['num_hyps']}\t{r['proof_effort']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
