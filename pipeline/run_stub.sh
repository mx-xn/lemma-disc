#!/usr/bin/env bash
# Stub pipeline: proof trace → lemma statements (phases 2+3 stub + phase 4).
# Phase 5 (Lean emission) is not yet implemented; output is lemmas.schema.json.
#
# Usage:
#   pipeline/run_stub.sh <trace.json> [--limit N] [--seed N] [--strategy STR] [--output FILE]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

# --- Defaults ---
LIMIT=20
SEED_ARG=()
STRATEGY="random"
OUTPUT=""
TRACE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)    LIMIT="$2";             shift 2 ;;
    --seed)     SEED_ARG=(--seed "$2"); shift 2 ;;
    --strategy) STRATEGY="$2";          shift 2 ;;
    --output)   OUTPUT="$2";            shift 2 ;;
    -*)  echo "Unknown option: $1" >&2; exit 1 ;;
    *)   TRACE="$1"; shift ;;
  esac
done

if [[ -z "$TRACE" ]]; then
  echo "Usage: $(basename "$0") <trace.json> [--limit N] [--seed N] [--strategy STR] [--output FILE]" >&2
  exit 1
fi

# --- Temp files, cleaned up on exit ---
FRAGMENTS=$(mktemp /tmp/lemma_fragments_XXXXXX.json)
LEMMAS_TMP=$(mktemp /tmp/lemma_out_XXXXXX.json)
trap 'rm -f "$FRAGMENTS" "$LEMMAS_TMP"' EXIT

# --- Phase 2+3 stub: enumerate fragments ---
echo "[1/3] Enumerating fragments (limit=$LIMIT, strategy=$STRATEGY)..." >&2
python3 "$ROOT/fragmentation-stub/enumerate.py" \
  "$TRACE" \
  --limit   "$LIMIT" \
  --strategy "$STRATEGY" \
  "${SEED_ARG[@]}" \
  --output  "$FRAGMENTS"

N_FRAGS=$(python3 -c "import json; print(len(json.load(open('$FRAGMENTS'))['fragments']))")
echo "[1/3] Got $N_FRAGS fragment(s)." >&2

# --- Phase 4: support minimization (Serializer.scala) ---
echo "[2/3] Running support minimization..." >&2
(cd "$ROOT/scala-core" && sbt "support/run $FRAGMENTS $LEMMAS_TMP")

# --- Post-phase-4 dedup: collapse fragments that produced identical lemmas ---
echo "[3/3] Deduplicating lemmas..." >&2
python3 "$ROOT/pipeline/dedup_lemmas.py" "$LEMMAS_TMP" "$FRAGMENTS"

# --- Copy outputs if requested ---
# Fragments are saved alongside lemmas with a derived name:
#   data/lemmas.json → data/lemmas.fragments.json
# Match by `fragment_id` (lemma) ↔ `fragment_id` (fragment).
if [[ -n "$OUTPUT" ]]; then
  cp "$LEMMAS_TMP" "$OUTPUT"
  FRAGS_OUT="${OUTPUT%.json}.fragments.json"
  cp "$FRAGMENTS" "$FRAGS_OUT"
  echo "[3/3] Lemmas    written to $OUTPUT" >&2
  echo "[3/3] Fragments written to $FRAGS_OUT" >&2
fi

# --- Print statements ---
python3 - "$LEMMAS_TMP" <<'EOF'
import json, sys
lemmas = json.load(open(sys.argv[1]))["lemmas"]
print(f"--- {len(lemmas)} lemma statement(s) ---")
for l in lemmas:
    print(f"[{l['fragment_id']}] {l['decl_name']}: {l['statement']}")
EOF
