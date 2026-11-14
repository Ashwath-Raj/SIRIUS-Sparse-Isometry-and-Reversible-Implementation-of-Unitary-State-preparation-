#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: expected project environment at $PYTHON" >&2
  echo "Run this from the existing project workspace after Phase 3–6 setup." >&2
  exit 2
fi

if ! "$PYTHON" -c 'import pytest' >/dev/null 2>&1; then
  echo "ERROR: pytest is missing from the project .venv." >&2
  echo "Install it with: uv pip install --python \"$PYTHON\" pytest" >&2
  exit 2
fi

export PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
"$PYTHON" -m pytest -vv --tb=short "$ROOT/candidate_ai/tests/test_phase_fixing.py"
