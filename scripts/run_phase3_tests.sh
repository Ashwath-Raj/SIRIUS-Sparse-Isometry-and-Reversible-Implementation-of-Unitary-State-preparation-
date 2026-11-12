#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN=/path/to/python and rerun." >&2
  exit 2
fi
export PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON_BIN" -m pytest candidate_ai/tests -vv --durations=20
