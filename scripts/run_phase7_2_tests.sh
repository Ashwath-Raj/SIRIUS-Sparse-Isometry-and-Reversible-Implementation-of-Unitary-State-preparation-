#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}" \
  .venv/bin/python -m pytest -q candidate_ai/tests/test_algorithm3.py candidate_ai/tests/test_phase_fixing.py
