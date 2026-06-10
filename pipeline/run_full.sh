#!/usr/bin/env bash
# Full pipeline: proof trace → lemma statements (phases 2 + 3 + 4).
# Phase 5 (Lean emission) is not yet implemented; output is lemmas.schema.json.
#
# Usage:
#   pipeline/run_full.sh <trace.json> [--timeout <ms>] [--output <file>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

TIMEOUT_ARG=()
OUTPUT=""
TRACE=""

usage() {
  echo "Usage: $(basename "$0") <trace.json> [--timeout <ms>] [--output <file>]" >&2
}

require_value() {
  local opt="$1"
  if [[ $# -lt 2 || -z "${2-}" || "$2" == -* ]]; then
    echo "Missing value for $opt" >&2
    usage
    exit 1
  fi
}

EM_DASH=$'\342\200\224'
EN_DASH=$'\342\200\223'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout|"${EM_DASH}timeout"|"${EM_DASH}-timeout"|"${EN_DASH}timeout"|"${EN_DASH}-timeout")
      require_value "$1" "${2-}"
      TIMEOUT_ARG=(--timeout "$2")
      shift 2
      ;;
    --output)
      require_value "$1" "${2-}"
      OUTPUT="$2"
      shift 2
      ;;
    -*)  echo "Unknown option: $1" >&2; exit 1 ;;
    *)
      if [[ -n "$TRACE" ]]; then
        echo "Unexpected positional argument: $1" >&2
        usage
        exit 1
      fi
      TRACE="$1"
      shift
      ;;
  esac
done

if [[ -z "$TRACE" ]]; then
  usage
  exit 1
fi

if [[ ! -f "$TRACE" ]]; then
  echo "Trace file not found: $TRACE" >&2
  exit 1
fi
TRACE_DIR="$(cd "$(dirname "$TRACE")" && pwd)"
TRACE="$TRACE_DIR/$(basename "$TRACE")"

if ! command -v sbt >/dev/null 2>&1; then
  echo "sbt was not found. Run this after: conda activate lemma" >&2
  exit 127
fi

POG=$(mktemp /tmp/lemma_pog_XXXXXX.json)
SEGMENTS=$(mktemp /tmp/lemma_segments_XXXXXX.json)
LEMMAS_TMP=$(mktemp /tmp/lemma_out_XXXXXX.json)
TRACE_FOR_POG=$(mktemp /tmp/lemma_trace_XXXXXX.json)
trap 'rm -f "$POG" "$SEGMENTS" "$LEMMAS_TMP" "$TRACE_FOR_POG"' EXIT

python3 - "$TRACE" "$TRACE_FOR_POG" <<'EOF'
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    data = json.load(f)

if isinstance(data, dict) and {"source_file", "declarations"} <= data.keys():
    with open(dst, "w") as f:
        json.dump(data, f)
elif isinstance(data, dict) and {"name", "statement", "root_tactic_id", "tactic_nodes"} <= data.keys():
    with open(dst, "w") as f:
        json.dump({"source_file": src, "declarations": [data]}, f)
else:
    print(
        "Input JSON is neither a full trace ({source_file, declarations}) "
        "nor a single declaration snapshot ({name, statement, root_tactic_id, tactic_nodes})",
        file=sys.stderr,
    )
    sys.exit(1)
EOF

# --- Phase 2: trace → POG ---
echo "[1/4] Building POG..." >&2
(cd "$ROOT/scala-core" && sbt "pog/run $TRACE_FOR_POG $POG")

# --- Phase 3: POG → segments ---
echo "[2/4] Enumerating fragments..." >&2
(cd "$ROOT/scala-core" && sbt "fragmentation/run ${TIMEOUT_ARG[*]+"${TIMEOUT_ARG[*]}"} $POG $SEGMENTS")
N_FRAGS=$(python3 -c "import json; print(len(json.load(open('$SEGMENTS'))['fragments']))")
echo "[2/4] Got $N_FRAGS fragment(s)." >&2

# --- Phase 4: support minimization ---
echo "[3/4] Running support minimization..." >&2
(cd "$ROOT/scala-core" && sbt "support/run $SEGMENTS $LEMMAS_TMP")

# --- Post-phase-4 dedup ---
echo "[4/4] Deduplicating lemmas..." >&2
python3 "$ROOT/pipeline/dedup_lemmas.py" "$LEMMAS_TMP" "$SEGMENTS"

if [[ -n "$OUTPUT" ]]; then
  cp "$LEMMAS_TMP" "$OUTPUT"
  FRAGS_OUT="${OUTPUT%.json}.fragments.json"
  cp "$SEGMENTS" "$FRAGS_OUT"
  echo "[4/4] Lemmas    written to $OUTPUT" >&2
  echo "[4/4] Fragments written to $FRAGS_OUT" >&2
fi

python3 - "$LEMMAS_TMP" <<'EOF'
import json, sys
lemmas = json.load(open(sys.argv[1]))["lemmas"]
print(f"--- {len(lemmas)} lemma statement(s) ---")
for l in lemmas:
    print(f"[{l['fragment_id']}] {l['decl_name']}: {l['statement']}")
EOF
