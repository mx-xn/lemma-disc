"""Data types + JSON I/O for lemma clustering experiments.

This module is pure: no string algorithms, no clustering logic, no LLM
plumbing. Clustering scripts (``syntactic_cluster.py``, ``anti_unify.py``)
import from here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


@dataclass
class LemmaRecord:
    statement: str
    fragment_id: int | None = None
    decl_name: str | None = None
    source_file: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "LemmaRecord":
        return cls(
            statement=d.get("statement", ""),
            fragment_id=d.get("fragment_id"),
            decl_name=d.get("decl_name"),
            source_file=d.get("source_file"),
        )

    def to_member_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "decl_name": self.decl_name,
            "fragment_id": self.fragment_id,
            "statement": self.statement,
        }


@dataclass
class Cluster:
    canonical: str
    members: list[LemmaRecord] = field(default_factory=list)

    @property
    def frequency(self) -> int:
        return len(self.members)

    def example_member(self) -> str:
        return self.members[0].statement if self.members else ""


def load_lemmas(paths: Sequence[Path]) -> list[LemmaRecord]:
    """Read one or more lemma JSON files in the standard shape.

    Accepts both ``{"lemmas": [...]}`` and top-level list inputs.
    """
    records: list[LemmaRecord] = []
    for p in paths:
        data = json.loads(Path(p).read_text())
        items = data["lemmas"] if isinstance(data, dict) and "lemmas" in data else data
        if not isinstance(items, list):
            items = [items]
        for d in items:
            if not isinstance(d, dict):
                continue
            stmt = (d.get("statement") or "").strip()
            if not stmt:
                continue
            records.append(LemmaRecord.from_dict(d))
    return records


def group_records(
    records: Sequence[LemmaRecord],
    key_fn: Callable[[str], str],
) -> list[list[LemmaRecord]]:
    """Partition records into ordered buckets, one per distinct ``key_fn(stmt)``.

    Insertion order of first appearance is preserved across buckets.
    """
    by_key: dict[str, list[LemmaRecord]] = {}
    order: list[str] = []
    for r in records:
        key = key_fn(r.statement)
        if key not in by_key:
            by_key[key] = []
            order.append(key)
        by_key[key].append(r)
    return [by_key[k] for k in order]


def emit_clusters(
    clusters: Sequence[Cluster],
    out_path: Path,
    meta: dict,
) -> None:
    """Write clusters to JSON. ``meta`` provides per-method header fields
    (e.g. ``method``, ``model``, ``input_files``)."""
    payload = {
        **meta,
        "num_input_lemmas": sum(c.frequency for c in clusters),
        "num_clusters": len(clusters),
        "clusters": [
            {
                "canonical": c.canonical,
                "frequency": c.frequency,
                "members": [m.to_member_dict() for m in c.members],
            }
            for c in clusters
        ],
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
