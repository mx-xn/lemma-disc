"""Subprocess bridge to the phases 1-4 extraction pipeline.

Thin wrapper: spins up digestion (Python, phase 1), then pog / fragmentation /
support (Scala phases 2-4) via sbt, merges the per-file segment outputs,
deduplicates, and returns extracted lemma statement strings.

Phase 5 (Lean emission / validation) is not yet implemented; fix_lemmas in
lemma_fixer.py handles post-hoc statement validation instead.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_REPO_ROOT    = Path(__file__).resolve().parents[3]  # /nas/lemma-disc
_SCALA_CORE   = _REPO_ROOT / "scala-core"
_PIPELINE_DIR = _REPO_ROOT / "pipeline"
_LEMMA_PYTHON = "/nas/conda-envs/lemma/bin/python"
_CONDA_BIN    = "/nas/conda-envs/lemma/bin"
_SBT_ENV      = {**os.environ, "PATH": f"{_CONDA_BIN}:{os.environ.get('PATH', '')}"}


def _run(cmd: list[str], *, cwd: Path | None = None, env=None) -> None:
    subprocess.run(cmd, check=True, cwd=cwd, env=env)


def _sbt(cmd: str) -> None:
    _run(["sbt", cmd], cwd=_SCALA_CORE, env=_SBT_ENV)


def _git_init(path: Path) -> None:
    """Ensure path is a git repo so LeanDojo can trace it."""
    if (path / ".git").exists():
        return
    for cmd in [
        ["git", "init"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", "corpus"],
    ]:
        subprocess.run(cmd, check=True, cwd=path)


def _merge_segments(segments_dir: Path) -> dict:
    """Merge all per-file segments JSONs into one, renumbering fragment_ids."""
    fragments: list[dict] = []
    for path in sorted(segments_dir.rglob("*.json")):
        for frag in json.loads(path.read_text())["fragments"]:
            fragments.append({**frag, "fragment_id": len(fragments)})
    return {"fragments": fragments}


def extract_lemmas(lean_files_dir: Path, work_dir: Path) -> list[str]:
    """Run phases 1-4 on lean_files_dir; return list of statement strings."""
    traces_dir    = work_dir / "traces"
    pogs_dir      = work_dir / "pogs"
    segments_dir  = work_dir / "segments"
    segments_json = work_dir / "segments.json"
    lemmas_json   = work_dir / "lemmas.json"

    # Phase 1: digestion — requires a git repo
    _git_init(lean_files_dir)
    _run([
        _LEMMA_PYTHON, "-m", "digestion.extractor",
        "--local", str(lean_files_dir),
        "--out-dir", str(traces_dir),
    ], cwd=_REPO_ROOT)

    # Phases 2–3: pog and fragmentation (batch over the traces directory)
    _sbt(f"pog/run {traces_dir} {pogs_dir}")
    _sbt(f"fragmentation/run {pogs_dir} {segments_dir}")

    # Merge per-file segment files before feeding support (phase 4)
    segments_json.write_text(
        json.dumps(_merge_segments(segments_dir), ensure_ascii=False)
    )

    # Phase 4: support minimization
    _sbt(f"support/run {segments_json} {lemmas_json}")

    # Dedup: drop fragments whose (statement, root_obligation) already appeared
    _run([
        _LEMMA_PYTHON, str(_PIPELINE_DIR / "dedup_lemmas.py"),
        str(lemmas_json), str(segments_json),
    ])

    return [l["statement"] for l in json.loads(lemmas_json.read_text())["lemmas"]]
