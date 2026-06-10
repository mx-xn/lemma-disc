"""Persistent registry of extracted lemma candidates and their usage scores.

Each entry tracks three signals:
  extraction_freq   — how many corpus fragments this lemma was extracted from
  success_cited     — rounds where it was cited in a verified-ok proof
  attempted_cited   — rounds where it was cited in a failed proof attempt

Deduplication key: statement.strip() (exact string after stripping whitespace).

The ``record_usage`` caller must pass the same ``lemma_pool`` list that was
given to the prover for that round so indices in <used_lemmas> tags can be
resolved back to statement strings.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LemmaEntry:
    statement: str
    extraction_freq: int = 0
    success_cited: int = 0
    attempted_cited: int = 0

    def score(self) -> float:
        return (
            self.success_cited * 1.0
            + self.attempted_cited * 0.2
            + math.log1p(self.extraction_freq) * 0.5
        )


class LemmaRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, LemmaEntry] = {}

    @classmethod
    def load_or_empty(cls, path: Path) -> LemmaRegistry:
        reg = cls()
        if not Path(path).exists():
            return reg
        data = json.loads(Path(path).read_text())
        for e in data.get("entries", []):
            key = e["statement"].strip()
            if not key:
                continue
            reg._entries[key] = LemmaEntry(
                statement=key,
                extraction_freq=e.get("extraction_freq", 0),
                success_cited=e.get("success_cited", 0),
                attempted_cited=e.get("attempted_cited", 0),
            )
        return reg

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entries": [
                {
                    "statement": e.statement,
                    "extraction_freq": e.extraction_freq,
                    "success_cited": e.success_cited,
                    "attempted_cited": e.attempted_cited,
                }
                for e in self._entries.values()
            ]
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def entries(self) -> list[LemmaEntry]:
        return list(self._entries.values())

    def add_extracted(self, statements: list[str]) -> None:
        """Register newly extracted lemma statements.

        Duplicate statements (after strip) increment extraction_freq rather than
        creating a new entry, so the same lemma appearing in multiple corpus
        fragments accumulates frequency naturally.
        """
        for stmt in statements:
            key = stmt.strip()
            if not key:
                continue
            if key in self._entries:
                self._entries[key].extraction_freq += 1
            else:
                self._entries[key] = LemmaEntry(statement=key, extraction_freq=1)

    def record_usage(
        self,
        round_results: dict[str, Any],
        lemma_pool: list[str],
    ) -> None:
        """Update cited counts from one round of prove results.

        Args:
            round_results: maps theorem_id → object with .ok (bool) and
                .attempts (list of objects with .used_indices list[int]).
            lemma_pool: ordered list of statement strings shown to the LLM
                this round (the return value of selector.select()).

        Per-theorem, the union of used_indices across all attempts is taken so
        that repeated citations across fix-loop attempts count only once.
        """
        pool = {i: s.strip() for i, s in enumerate(lemma_pool)}
        for result in round_results.values():
            used: set[int] = set()
            for attempt in result.attempts:
                used |= set(getattr(attempt, "used_indices", []))
            for idx in used:
                stmt = pool.get(idx)
                if stmt and stmt in self._entries:
                    if result.ok:
                        self._entries[stmt].success_cited += 1
                    else:
                        self._entries[stmt].attempted_cited += 1
