"""Stage 4 of Experiment B — aggregate and export CSVs.

Joins 02_picks.json (study a) and 03_solo.json (study b) with per-statement
complexity metrics from exp/count_hyps.py.

Outputs (under output_dir/04_csv/):
    study_a_flat.csv     — one row per (theorem, candidate) presentation
    study_a_summary.csv  — pick rate grouped by proof_effort
    study_b_flat.csv     — one row per (theorem, hint) in each solo run
    study_b_summary.csv  — success rate grouped by proof_effort
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from exp.count_hyps import count_hyps, proof_effort as calc_proof_effort

CSV_SUBDIR = "04_csv"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[wrote] {path} ({len(rows)} rows)", file=sys.stderr)


def _aggregate_picks(picks_data: dict, out_dir: Path) -> None:
    results = picks_data.get("results", {})

    flat_rows: list[dict] = []
    for theorem_id, rec in results.items():
        all_candidates: list[str] = rec.get("all_candidates", [])
        used_indices = set(rec.get("used_indices", []))
        theorem_ok = rec.get("ok", False)
        for idx, stmt in enumerate(all_candidates):
            flat_rows.append({
                "theorem_id": theorem_id,
                "candidate_idx": idx,
                "num_hyps": count_hyps(stmt),
                "proof_effort": calc_proof_effort(stmt),
                "was_picked": int(idx in used_indices),
                "theorem_ok": int(theorem_ok),
            })

    _write_csv(
        out_dir / "study_a_flat.csv",
        ["theorem_id", "candidate_idx", "num_hyps", "proof_effort", "was_picked", "theorem_ok"],
        flat_rows,
    )

    by_pe: dict[int, list[dict]] = defaultdict(list)
    for r in flat_rows:
        by_pe[r["proof_effort"]].append(r)

    summary_rows = []
    for pe in sorted(by_pe):
        group = by_pe[pe]
        n = len(group)
        n_picked = sum(r["was_picked"] for r in group)
        summary_rows.append({
            "proof_effort": pe,
            "n_presentations": n,
            "n_picked": n_picked,
            "pick_rate": round(n_picked / n, 4) if n else 0.0,
        })

    _write_csv(
        out_dir / "study_a_summary.csv",
        ["proof_effort", "n_presentations", "n_picked", "pick_rate"],
        summary_rows,
    )


def _aggregate_solo(solo_data: dict, out_dir: Path) -> None:
    results = solo_data.get("results", {})

    flat_rows: list[dict] = []
    for theorem_id, rec in results.items():
        hint_stmts: list[str] = rec.get("hint_statements", [])
        ok = rec.get("ok", False)
        n_hints = len(hint_stmts)
        for idx, stmt in enumerate(hint_stmts):
            flat_rows.append({
                "theorem_id": theorem_id,
                "hint_idx": idx,
                "num_hyps": count_hyps(stmt),
                "proof_effort": calc_proof_effort(stmt),
                "ok": int(ok),
                "n_hints_in_run": n_hints,
            })

    _write_csv(
        out_dir / "study_b_flat.csv",
        ["theorem_id", "hint_idx", "num_hyps", "proof_effort", "ok", "n_hints_in_run"],
        flat_rows,
    )

    by_pe: dict[int, list[dict]] = defaultdict(list)
    for r in flat_rows:
        by_pe[r["proof_effort"]].append(r)

    summary_rows = []
    for pe in sorted(by_pe):
        group = by_pe[pe]
        n = len(group)
        n_ok = sum(r["ok"] for r in group)
        summary_rows.append({
            "proof_effort": pe,
            "n_runs": n,
            "n_ok": n_ok,
            "success_rate": round(n_ok / n, 4) if n else 0.0,
        })

    _write_csv(
        out_dir / "study_b_summary.csv",
        ["proof_effort", "n_runs", "n_ok", "success_rate"],
        summary_rows,
    )


def run_aggregate(
    *,
    picks_path: Path,
    solo_path: Path,
    output_dir: Path,
    force: bool,
) -> None:
    output_dir = Path(output_dir)
    csv_dir = output_dir / CSV_SUBDIR

    if csv_dir.exists() and any(csv_dir.iterdir()) and not force:
        print(f"[skip] {csv_dir} exists (use --force to overwrite)", file=sys.stderr)
        return

    picks_path = Path(picks_path)
    solo_path = Path(solo_path)

    if picks_path.exists():
        print(f"[load] {picks_path}", file=sys.stderr)
        _aggregate_picks(_load_json(picks_path), csv_dir)
    else:
        print(f"[warn] {picks_path} not found — skipping study a", file=sys.stderr)

    if solo_path.exists():
        print(f"[load] {solo_path}", file=sys.stderr)
        _aggregate_solo(_load_json(solo_path), csv_dir)
    else:
        print(f"[warn] {solo_path} not found — skipping study b", file=sys.stderr)
