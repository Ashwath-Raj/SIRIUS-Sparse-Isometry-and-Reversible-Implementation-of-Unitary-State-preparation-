#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHONPATH="$ROOT/candidate_ai/src${PYTHONPATH:+:$PYTHONPATH}" \
  python -m pytest -q candidate_ai/tests/test_phase_synthesis_8_1.py
