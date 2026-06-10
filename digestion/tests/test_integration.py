"""Integration tests for extract() on MiniCodePropsLeanSrc.

Setup required before running:
  1. cd /nas/lemma-disc/data/input/MiniCodePropsLeanSrc
     git init && git add . && git commit -m "init"
  2. export GITHUB_ACCESS_TOKEN=<your token>

The first run is expensive (lake build + Mathlib download). LeanDojo caches the
result; subsequent runs load from cache and are fast.

Snapshot workflow
-----------------
Run once to generate snapshots for every extracted declaration:

    pytest tests/test_integration.py -m integration --snapshot-update

Subsequent runs compare every declaration against its saved snapshot.
To regenerate after an intentional change, re-run with --snapshot-update.

Snapshot files are stored as:
    tests/snapshots/<source_file_stem>__<slug(decl_name)>.json
"""
import json
import re
from pathlib import Path

import pytest

REPO_PATH = Path("/nas/lemma-disc/data/input/MiniCodePropsLeanSrc")
SCHEMA_PATH = Path("/nas/lemma-disc/schemas/trace.schema.json")
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

EXPECTED_DECL_NAMES = {
    "prop_04", "prop_05", "prop_12",
    "and_iff_and_of_imp", "or_and_distrib", "entangled_reasoning",
    "prop_29", "prop_53", "prop_55", "prop_56", "prop_57", "prop_58",
    "prop_77", "prop_78", "zip'_append_of_length_eq", "prop_85",
}


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _snapshot_path(source_file: str, decl_name: str) -> Path:
    stem = Path(source_file).stem
    return SNAPSHOTS_DIR / f"{stem}__{_slug(decl_name)}.json"


# ── shared fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def traces():
    from digestion.tracer import trace_local_repo
    from digestion.extractor import extract
    traced_repo = trace_local_repo(str(REPO_PATH))
    return extract(traced_repo)


# ── property tests (logical invariants) ─────────────────────────────────────

@pytest.mark.integration
def test_schema_valid(traces):
    import jsonschema
    schema = json.loads(SCHEMA_PATH.read_text())
    for trace in traces:
        jsonschema.validate(trace.to_dict(), schema)


@pytest.mark.integration
def test_expected_declarations_present(traces):
    found = {
        decl.name.split(".")[-1]
        for trace in traces
        for decl in trace.declarations
    }
    assert EXPECTED_DECL_NAMES <= found, (
        f"Missing declarations: {EXPECTED_DECL_NAMES - found}"
    )


@pytest.mark.integration
def test_tree_invariants(traces):
    for trace in traces:
        for decl in trace.declarations:
            node_ids = {n.id for n in decl.tactic_nodes}
            roots = [n for n in decl.tactic_nodes if n.parent_id is None]

            assert len(roots) == 1, (
                f"{decl.name}: expected 1 root, got {len(roots)}"
            )
            assert roots[0].id == decl.root_tactic_id

            for node in decl.tactic_nodes:
                if node.parent_id is not None:
                    assert node.parent_id in node_ids, (
                        f"{decl.name} node {node.id}: parent_id {node.parent_id} not found"
                    )
                for cid in node.child_ids:
                    assert cid in node_ids, (
                        f"{decl.name} node {node.id}: child_id {cid} not found"
                    )


@pytest.mark.integration
def test_coindexing_invariant(traces):
    for trace in traces:
        for decl in trace.declarations:
            for node in decl.tactic_nodes:
                n_out = len(node.output_obligations)
                n_dep = len(node.summary.dependency_maps)
                n_child = len(node.child_ids)

                assert n_out == n_dep, (
                    f"{decl.name} node {node.id}: "
                    f"output_obligations({n_out}) != dependency_maps({n_dep})"
                )
                assert n_child <= n_out, (
                    f"{decl.name} node {node.id}: "
                    f"child_ids({n_child}) > output_obligations({n_out})"
                )


@pytest.mark.integration
def test_dependency_map_totality(traces):
    for trace in traces:
        for decl in trace.declarations:
            for node in decl.tactic_nodes:
                for i, (out_obl, dep_map) in enumerate(
                    zip(node.output_obligations, node.summary.dependency_maps)
                ):
                    out_names = {h.name for h in out_obl.hypotheses}
                    assert set(dep_map.keys()) == out_names, (
                        f"{decl.name} node {node.id} branch {i}: "
                        f"dep_map keys {set(dep_map.keys())} != output hyps {out_names}"
                    )


@pytest.mark.integration
def test_leaf_nodes_have_empty_arrays(traces):
    for trace in traces:
        for decl in trace.declarations:
            for node in decl.tactic_nodes:
                if not node.output_obligations:
                    assert node.child_ids == []
                    assert node.summary.dependency_maps == []


# ── snapshot tests (regression guard) ────────────────────────────────────────

@pytest.mark.integration
def test_all_snapshots(traces, request):
    """Compare every extracted declaration against a saved snapshot.

    Snapshots are keyed by source file and declaration name:
        snapshots/<file_stem>__<slug(decl_name)>.json

    New declarations (no snapshot on disk) are written automatically on the
    first run. Run with --snapshot-update to overwrite all snapshots.
    """
    update = request.config.getoption("--snapshot-update", default=False)
    written: list[Path] = []
    mismatches: list[str] = []

    for trace in traces:
        for decl in trace.declarations:
            actual = decl.to_dict()
            path = _snapshot_path(trace.source_file, decl.name)
            if update or not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(actual, indent=2, ensure_ascii=False))
                written.append(path)
                continue
            expected = json.loads(path.read_text())
            if actual != expected:
                mismatches.append(
                    f"{path.name}: output differs from snapshot; "
                    "re-run with --snapshot-update if intentional"
                )

    if written:
        pytest.skip(
            f"Wrote {len(written)} new snapshot(s) to {SNAPSHOTS_DIR}. "
            "Re-run without --snapshot-update to verify."
        )
    if mismatches:
        pytest.fail("\n".join(mismatches))
