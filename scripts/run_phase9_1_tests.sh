#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m unittest discover -s tests -p 'test_phase9_1_design.py' -v
python3 scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json
python3 scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json --tier smoke --emit-manifest /tmp/sparseprep-phase9-1-smoke-dry-run.json
