"""Merge-aware I/O for theorem result files.

Both 01_baseline.json and prove_results.json share the schema::

    {
        "lake_project": str,
        "imports":      [str, ...],
        "results":      { theorem_id: { ... } }
    }

Merge rule (``force=False``):
    If the on-disk file has the *same* ``lake_project``, results are upserted
    by ``theorem_id``: new entries overwrite existing ones for the same id,
    while entries for unseen theorem_ids are preserved.  A mismatched
    ``lake_project`` is treated as a stale file and replaced entirely.

When ``force=True`` the on-disk file is always replaced.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_results_file(path: Path) -> dict:
    """Return the parsed JSON from path, or {} if the file does not exist."""
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_results_file(
    path: Path,
    lake_project: str,
    imports: list[str],
    new_results: dict[str, dict],
    *,
    force: bool = False,
) -> dict[str, dict]:
    """Upsert new_results into the results file at path; write and return merged map.

    Args:
        path:          Destination file path.
        lake_project:  Absolute path string identifying the Lean project.
        imports:       Module import list written into the file header.
        new_results:   Mapping of theorem_id → result dict for this run.
        force:         When True, skip reading the existing file (full replace).

    Returns:
        The full merged ``results`` dict that was written to disk.
    """
    if not force:
        existing = load_results_file(path)
        if existing.get("lake_project") == lake_project:
            merged: dict[str, dict] = dict(existing.get("results", {}))
            merged.update(new_results)
        else:
            merged = dict(new_results)
    else:
        merged = dict(new_results)

    path.write_text(
        json.dumps(
            {"lake_project": lake_project, "imports": imports, "results": merged},
            ensure_ascii=False,
            indent=2,
        )
    )
    return merged
