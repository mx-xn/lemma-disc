"""Parse a Lemmas.lean file to extract hint statements grouped by theorem ID.

Each entry in the file has the form:
    lemma l{N}_prop_{M} <statement> := by sorry

``load_by_prop`` returns a dict mapping prop number strings (e.g. "36") to
the list of binder-syntax statements for that prop, in file order.

``load_flat`` returns all statements as a flat list, in file order.
"""
from __future__ import annotations

import re
from pathlib import Path

# Captures: (prop_number, statement)
# Statement is everything between the lemma name and ':= by sorry'.
# re.DOTALL lets '.' cross newlines for future multi-line statements.
_LEMMA_RE = re.compile(
    r"lemma\s+l\d+_prop_(\d+)\s+(.*?)\s*:=\s*by\s+sorry",
    re.DOTALL,
)


def load_by_prop(path: Path) -> dict[str, list[str]]:
    """Return {prop_id -> [stmt, ...]} parsed from path.

    prop_id is the raw digit string (e.g. "36" for l1_prop_36).
    Each stmt is the binder-syntax statement ready for use as a lemma hint.
    Order within each group follows file order.
    """
    text = Path(path).read_text()
    result: dict[str, list[str]] = {}
    for m in _LEMMA_RE.finditer(text):
        prop_id = m.group(1)
        stmt = m.group(2).strip()
        result.setdefault(prop_id, []).append(stmt)
    return result


def load_flat(path: Path) -> list[str]:
    """Return all statement strings in file order, ignoring prop grouping."""
    text = Path(path).read_text()
    return [m.group(2).strip() for m in _LEMMA_RE.finditer(text)]
