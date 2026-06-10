"""Tests for lemma_loader.py."""
import textwrap
from pathlib import Path

import pytest

from exp.eval.sanity.lemma_loader import load_by_prop, load_flat

_SAMPLE = textwrap.dedent("""\
    import LeanSrc.Definitions

    lemma l1_prop_36 (xs: List α): xs = xs := by sorry
    lemma l2_prop_36 (x: α) (xs: List α): x :: xs = x :: xs := by sorry

    lemma l1_prop_29 (x: Nat): x = x := by sorry
""")


def _write(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "Lemmas.lean"
    f.write_text(content)
    return f


def test_grouping(tmp_path):
    result = load_by_prop(_write(tmp_path, _SAMPLE))
    assert set(result.keys()) == {"36", "29"}
    assert len(result["36"]) == 2
    assert len(result["29"]) == 1


def test_statement_content(tmp_path):
    result = load_by_prop(_write(tmp_path, _SAMPLE))
    assert result["29"][0] == "(x: Nat): x = x"
    assert result["36"][0] == "(xs: List α): xs = xs"


def test_flat_count_and_order(tmp_path):
    stmts = load_flat(_write(tmp_path, _SAMPLE))
    assert len(stmts) == 3
    # file order: two prop_36 lemmas, then one prop_29
    assert stmts[2] == "(x: Nat): x = x"


def test_empty_file(tmp_path):
    f = _write(tmp_path, "import LeanSrc.Definitions\n")
    assert load_by_prop(f) == {}
    assert load_flat(f) == []
