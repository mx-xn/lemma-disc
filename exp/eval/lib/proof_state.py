"""Convert Lean 4 binder-syntax theorem statements to LeanDojo proof-state format.

Input (statement_text from Theorem dataclass):
    '(x: Nat) (xs: List Nat) : x ∈ ins1 x xs'

Output (proof state as shown in Lean infoview):
    'x : Nat\nxs : List Nat\n⊢ x ∈ ins1 x xs'

Only handles explicit binders of the form (name : Type).  Implicit {..} and
instance [...] binders are not present in the current MiniCodeProps corpus; if
they appear in the future, extend _parse_binders.
"""
from __future__ import annotations


def _find_toplevel_colon(s: str) -> int:
    """Return the index of the first ':' at paren-depth 0 that is not '::' or ':='."""
    depth = 0
    for i, ch in enumerate(s):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            next_ch = s[i + 1] if i + 1 < len(s) else ""
            if next_ch not in (":", "="):
                return i
    return -1


def _parse_binders(binders_str: str) -> list[tuple[str, str]]:
    """Return list of (name, type) pairs extracted from a binder prefix string.

    Each binder has the form '(name1 name2 ... : type)'.  Multiple names in one
    binder are expanded to separate (name, type) pairs.
    """
    pairs: list[tuple[str, str]] = []
    i = 0
    n = len(binders_str)
    while i < n:
        if binders_str[i] != "(":
            i += 1
            continue
        # Find the matching closing paren.
        depth = 1
        j = i + 1
        while j < n and depth > 0:
            if binders_str[j] == "(":
                depth += 1
            elif binders_str[j] == ")":
                depth -= 1
            j += 1
        content = binders_str[i + 1 : j - 1].strip()
        colon = _find_toplevel_colon(content)
        if colon != -1:
            names_str = content[:colon].strip()
            type_str = content[colon + 1 :].strip()
            for name in names_str.split():
                pairs.append((name, type_str))
        i = j
    return pairs


def statement_to_proof_state(stmt: str) -> str:
    """Convert a binder-syntax statement string to a LeanDojo proof-state string.

    Args:
        stmt: e.g. '(x: Nat) (xs: List Nat) : x ∈ ins1 x xs'

    Returns:
        e.g. 'x : Nat\\nxs : List Nat\\n⊢ x ∈ ins1 x xs'
    """
    stmt = stmt.strip()
    split = _find_toplevel_colon(stmt)
    if split == -1:
        return f"⊢ {stmt}"

    binders_str = stmt[:split].strip()
    conclusion = stmt[split + 1 :].strip()

    if not binders_str:
        return f"⊢ {conclusion}"

    pairs = _parse_binders(binders_str)
    lines = [f"{name} : {typ}" for name, typ in pairs]
    lines.append(f"⊢ {conclusion}")
    return "\n".join(lines)
