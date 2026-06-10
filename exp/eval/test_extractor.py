"""Tests for exp.eval.lib.extractor._merge_segments.

Run from the repo root:
    pytest exp/eval/test_extractor.py
"""
import json
import tempfile
from pathlib import Path

from exp.eval.lib.extractor import _merge_segments


def _write_segments(directory: Path, filename: str, fragments: list[dict]) -> None:
    (directory / filename).write_text(json.dumps({"fragments": fragments}))


def test_merge_renumbers_fragment_ids() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_segments(d, "a.json", [
            {"fragment_id": 0, "data": "x"},
            {"fragment_id": 1, "data": "y"},
        ])
        _write_segments(d, "b.json", [
            {"fragment_id": 0, "data": "z"},
        ])

        result = _merge_segments(d)

    frags = result["fragments"]
    assert len(frags) == 3
    assert [f["fragment_id"] for f in frags] == [0, 1, 2]
    assert [f["data"] for f in frags] == ["x", "y", "z"]


def test_merge_empty_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = _merge_segments(Path(tmp))
    assert result == {"fragments": []}


def test_merge_preserves_other_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_segments(d, "a.json", [
            {"fragment_id": 0, "source_file": "Foo.lean", "decl_name": "foo"},
        ])

        result = _merge_segments(d)

    frag = result["fragments"][0]
    assert frag["source_file"] == "Foo.lean"
    assert frag["decl_name"] == "foo"
    assert frag["fragment_id"] == 0
