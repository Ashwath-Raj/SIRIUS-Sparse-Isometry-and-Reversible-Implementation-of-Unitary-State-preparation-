#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: expected project environment at $PYTHON" >&2
  exit 2
fi

if ! "$PYTHON" -c 'import pytest' >/dev/null 2>&1; then
  echo "ERROR: pytest is missing from the project .venv." >&2
  echo "Install it with: uv pip install --python \"$PYTHON\" pytest==9.0.2" >&2
  exit 2
fi

export PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
"$PYTHON" -m pytest -vv --tb=short --durations=20 "$ROOT/candidate_ai/tests"
