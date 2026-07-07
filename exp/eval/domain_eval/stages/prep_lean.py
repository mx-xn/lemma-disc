"""Produce a training-only copy of a Lean source file.

Segments the file into top-level declaration blocks, then drops every
theorem/lemma whose name is not in the training split.  Non-theorem blocks
(imports, defs, opens, comments, blank lines) are always kept.

Known limitation: a multi-line attribute annotation written as
    @[simp]
    theorem foo ...
produces two consecutive block-start lines; `foo` is still detected
correctly, but if `foo` is dropped the orphaned `@[simp]` line remains.
Single-line form `@[simp] theorem foo` is handled correctly.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from exp.lib.corpus import load_theorems

# Lines that start a new top-level declaration (must be at column 0).
# Comments (`--`) and blank lines are deliberately excluded so they accumulate
# into the preceding block and are never dropped on their own.
_BLOCK_START_RE = re.compile(
    r'^(?:theorem|lemma|def|abbrev|noncomputable|private|protected'
    r'|instance|class|structure|inductive|mutual|section|namespace'
    r'|end|open|import|variable|attribute|@\[|#)'
)

# Finds `theorem Name` or `lemma Name` anywhere in a line (handles
# `@[attr] theorem Name` on a single line).
_THEOREM_NAME_RE = re.compile(r'\b(?:theorem|lemma)\s+(\S+)')


@dataclass
class _Block:
    lines: list[str]
    theorem_name: str | None  # None for non-theorem blocks


def _is_block_start(line: str) -> bool:
    return bool(_BLOCK_START_RE.match(line))


def _extract_theorem_name(lines: list[str]) -> str | None:
    """Return theorem/lemma name from the block's opening lines, or None.

    Checks up to 3 lines to handle a preceding `@[attr]` line.
    """
    for line in lines[:3]:
        m = _THEOREM_NAME_RE.search(line)
        if m:
            return m.group(1)
    return None


def _segment(text: str) -> list[_Block]:
    """Split Lean source text into a list of top-level blocks.

    Each block spans from one column-0 declaration keyword to just before
    the next.  Preamble lines (comments, blank lines before the first keyword)
    become an initial block with theorem_name=None.
    """
    all_lines = text.splitlines(keepends=True)
    blocks: list[_Block] = []
    current: list[str] = []

    for line in all_lines:
        if _is_block_start(line) and current:
            blocks.append(_Block(lines=current, theorem_name=_extract_theorem_name(current)))
            current = []
        current.append(line)

    if current:
        blocks.append(_Block(lines=current, theorem_name=_extract_theorem_name(current)))

    return blocks


def _matches_train(name: str, train_ids: set[str]) -> bool:
    """Return True if `name` belongs to the training set.

    Handles qualified theorem_ids like ``MyNs.foo`` matching source name
    ``foo`` (inside a namespace block, the source still reads ``theorem foo``
    but the digestion full_name is ``MyNs.foo``).
    """
    if name in train_ids:
        return True
    return any(tid.rsplit(".", 1)[-1] == name for tid in train_ids)


def _keep_block(block: _Block, train_ids: set[str]) -> bool:
    if block.theorem_name is None:
        return True
    return _matches_train(block.theorem_name, train_ids)


def run_prep_lean(
    lean_file: Path,
    train_path: Path,
    output_path: Path | None,
    force: bool,
) -> None:
    lean_file = Path(lean_file)
    tset = load_theorems(Path(train_path))
    train_ids = {t.theorem_id for t in tset.theorems}

    if output_path is None:
        output_path = lean_file.parent / (lean_file.stem + "_train" + lean_file.suffix)
    output_path = Path(output_path)

    if output_path.exists() and not force:
        print(f"[skip] {output_path} exists (use --force to overwrite)", file=sys.stderr)
        return

    blocks = _segment(lean_file.read_text())
    kept = [b for b in blocks if _keep_block(b, train_ids)]

    n_total = sum(1 for b in blocks if b.theorem_name is not None)
    n_kept = sum(1 for b in kept if b.theorem_name is not None)

    output_path.write_text("".join("".join(b.lines) for b in kept))
    print(
        f"[prep-lean] {n_kept}/{n_total} theorem(s) kept -> {output_path}",
        file=sys.stderr,
    )
