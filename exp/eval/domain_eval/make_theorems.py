"""Scaffold domain_theorems.json from a Lean source file.

Standalone authoring tool — not part of the run.py pipeline.
Run once, review/edit the output, then feed it to `run.py split`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Sequence

from .stages.prep_lean import _Block, _segment

# Captures everything after "theorem/lemma NAME" (including leading whitespace).
_DECL_RE = re.compile(r'\b(?:theorem|lemma)\s+\S+(.*)', re.DOTALL)


def _is_attr_only(block: _Block) -> bool:
    """Return True if the block is a standalone attribute annotation (e.g. '@[simp]').

    Such blocks have no standalone meaning in local_ctx — they're prefixes of
    the theorem declaration that follows and should not be accumulated.
    """
    for line in block.lines:
        s = line.strip()
        if not s or s.startswith("--") or s.startswith("/-"):
            continue
        return s.startswith("@[")
    return False


def _extract_statement(block: _Block) -> str | None:
    """Return the statement text: from after the theorem name up to ':='.

    Uses a parenthesis-depth scan so ':=' inside a type (e.g. '(h : a := b)')
    is not mistaken for the definition separator.
    Whitespace is normalised (newlines → spaces, runs collapsed).
    Returns None if the block has no recognisable theorem declaration.
    """
    text = "".join(block.lines)
    m = _DECL_RE.search(text)
    if not m:
        return None
    after_name = m.group(1)
    depth = 0
    for i, c in enumerate(after_name):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and depth == 0 and after_name[i : i + 2] == ":=":
            return " ".join(after_name[:i].split())
    # No ':=' found — return everything (e.g. tactic-style 'where' blocks are rare)
    return " ".join(after_name.split())


def _build_theorems(
    lean_file: Path,
    lake_project: Path,
    imports: list[str],
) -> dict:
    blocks = _segment(lean_file.read_text())
    lean_path = str(lean_file.relative_to(lake_project))

    theorems: list[dict] = []
    non_thm_blocks: list[_Block] = []  # only structural blocks (no theorem bodies)

    for block in blocks:
        if block.theorem_name is None:
            if not _is_attr_only(block):
                non_thm_blocks.append(block)
            continue

        stmt = _extract_statement(block)
        if stmt is None:
            print(
                f"[warn] could not extract statement for {block.theorem_name!r}; skipping",
                file=sys.stderr,
            )
            continue

        local_ctx = "".join("".join(b.lines) for b in non_thm_blocks).strip()
        theorems.append({
            "theorem_id": block.theorem_name,
            "lean_path": lean_path,
            "statement_text": stmt,
            "local_ctx": local_ctx,
        })

    return {
        "lake_project": str(lake_project),
        "imports": imports,
        "theorems": theorems,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    _DEFAULT_OUTPUT = Path(__file__).resolve().parent / "input" / "domain_theorems.json"

    p = argparse.ArgumentParser(
        prog="make_theorems",
        description="Scaffold domain_theorems.json from a Lean source file.",
    )
    p.add_argument("--lean-file", type=Path, required=True,
                   help="Lean source file to extract theorems from")
    p.add_argument("--lake-project", type=Path, required=True,
                   help="Lake project root (used to compute lean_path)")
    p.add_argument("--imports", type=str, required=True,
                   help="comma-separated Lean module imports")
    p.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    p.add_argument("--force", action="store_true",
                   help="overwrite output if it already exists")
    args = p.parse_args(argv)

    if args.output.exists() and not args.force:
        print(f"[skip] {args.output} exists (use --force to overwrite)", file=sys.stderr)
        return 0

    imports = [tok.strip() for tok in args.imports.split(",") if tok.strip()]
    data = _build_theorems(args.lean_file, args.lake_project, imports)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        f"[make_theorems] {len(data['theorems'])} theorem(s) -> {args.output}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
