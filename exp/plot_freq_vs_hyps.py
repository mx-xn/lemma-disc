#!/usr/bin/env python3
"""Plot lemma appearance frequency vs. hypothesis count.

Reads an ``anti_unify.py`` output file, computes ``num_hyps`` and
``proof_effort`` for each cluster's canonical statement via ``count_hyps``,
and emits:

  - a CSV with one row per cluster: ``(num_hyps, proof_effort, frequency, canonical)``
  - a scatter PNG: ``num_hyps`` (or ``proof_effort``) on x, ``frequency`` on y

Usage
-----
    python exp/plot_freq_vs_hyps.py data/output/anti_unify_prop_56.json \\
        --csv data/output/anti_unify_prop_56.csv \\
        --png data/output/anti_unify_prop_56.png
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_hyps import count_hyps, proof_effort  # noqa: E402


def _rows(payload: dict) -> list[dict]:
    rows = []
    for c in payload.get("clusters", []):
        stmt = c.get("canonical", "")
        rows.append({
            "frequency": int(c.get("frequency", 0)),
            "num_hyps": count_hyps(stmt) if stmt else 0,
            "proof_effort": proof_effort(stmt) if stmt else 0,
            "canonical": stmt,
        })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["num_hyps", "proof_effort", "frequency", "canonical"])
        w.writeheader()
        w.writerows(rows)


def write_png(rows: list[dict], path: Path, x_metric: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [r[x_metric] for r in rows]
    ys = [r["frequency"] for r in rows]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(xs, ys, alpha=0.7, s=40)
    ax.set_xlabel(x_metric)
    ax.set_ylabel("appearance frequency")
    ax.set_title(title)
    if any(y > 0 for y in ys):
        ax.set_yscale("symlog")
    ax.grid(True, alpha=0.3)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path,
                        help="anti_unify output JSON")
    parser.add_argument("--csv", type=Path, default=None,
                        help="output CSV path (default: alongside input)")
    parser.add_argument("--png", type=Path, default=None,
                        help="output PNG path (default: alongside input)")
    parser.add_argument("--x", choices=["num_hyps", "proof_effort"],
                        default="num_hyps", help="x-axis metric")
    args = parser.parse_args(argv)

    payload = json.loads(args.input.read_text())
    rows = _rows(payload)
    rows.sort(key=lambda r: (r["num_hyps"], -r["frequency"]))

    csv_path = args.csv or args.input.with_suffix(".csv")
    png_path = args.png or args.input.with_suffix(".png")
    write_csv(rows, csv_path)
    write_png(rows, png_path, args.x, title=args.input.stem)

    print(f"wrote {csv_path}")
    print(f"wrote {png_path}")
    print(f"{len(rows)} clusters; "
          f"total frequency = {sum(r['frequency'] for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
