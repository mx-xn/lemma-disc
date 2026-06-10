# Digestion (Phase 1)

Extracts obligation-annotated proof trees from a Lean 4 repository and emits
one JSON file per source file, conforming to `../schemas/trace.schema.json`.

## Setup

```bash
# 1. Initialise the Lean input repo (required by LeanDojo)
cd /nas/lemma-disc/data/input/MiniCodePropsLeanSrc
git init && git add . && git commit -m "init"

# 2. Export a GitHub token (required by LeanDojo even for local repos)
export GITHUB_ACCESS_TOKEN=<your token>

# 3. Install the package (from the repo root)
cd /nas/lemma-disc/digestion
pip install -e .
```

## Running the extractor

```bash
# Local repo → writes JSON to data/traces/MiniCodePropsLeanSrc/
python -m digestion.extractor --local /nas/lemma-disc/data/input/MiniCodePropsLeanSrc
```

The first run is slow (lake build + Mathlib download). LeanDojo caches the
result; subsequent runs are fast.

## Integration tests

```bash
cd /nas/lemma-disc/digestion
pytest tests/test_integration.py -m integration
```

### Snapshot workflow

Snapshots are stored in `tests/snapshots/` as
`<source_file_stem>__<decl_name>.json` — one file per extracted declaration.

**First run / new declarations** — snapshots that don't exist yet are written
automatically, then the test skips with a summary. Re-run without the flag to
verify:

```bash
pytest tests/test_integration.py -m integration
```

**Regenerate all snapshots** after an intentional change to the extractor:

```bash
pytest tests/test_integration.py -m integration --snapshot-update
```

Any theorem added to the Lean source is picked up automatically on the next
run — no changes to the test file are needed.
