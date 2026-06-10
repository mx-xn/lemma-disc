#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

LIMIT="${LIMIT:-200}"
SEED="${SEED:-42}"
OUT_DIR="${OUT_DIR:-$ROOT/data/lemma_counts}"

PROPS=("$@")
if [[ ${#PROPS[@]} -eq 0 ]]; then
  PROPS=(30 35 36 37 47 53 55 56 57 58 77 78 85)
fi

mkdir -p "$OUT_DIR"

if ! command -v sbt >/dev/null 2>&1; then
  echo "sbt was not found. Run this after: conda activate lemma" >&2
  exit 127
fi

printf 'prop,lemmas,output,log\n'
for prop in "${PROPS[@]}"; do
  trace="$ROOT/digestion/tests/snapshots/Examples__prop_${prop}.json"
  output="$OUT_DIR/prop_${prop}_lemmas.json"
  log="$OUT_DIR/prop_${prop}.log"

  if [[ ! -f "$trace" ]]; then
    printf 'prop_%s,MISSING_TRACE,%s,\n' "$prop" "$trace" >&2
    continue
  fi

  if ! "$ROOT/pipeline/run_stub.sh" "$trace" \
    --limit "$LIMIT" \
    --seed "$SEED" \
    --output "$output" >"$log" 2>&1; then
    printf 'prop_%s,FAILED,%s,%s\n' "$prop" "$output" "$log"
    continue
  fi

  count="$(python3 - "$output" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    print(len(json.load(f).get("lemmas", [])))
PY
)"

  printf 'prop_%s,%s,%s,%s\n' "$prop" "$count" "$output" "$log"
done
