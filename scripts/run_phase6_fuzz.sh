#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: expected project environment at $PYTHON" >&2
  exit 2
fi
export PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
"$PYTHON" "$ROOT/scripts/phase6_fuzz.py"
