#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${SIRIUS_PYTHON:-$ROOT/.venv/bin/python}"
if [[ $# -ne 1 ]]; then echo "Usage: $0 RUN_ID" >&2; exit 2; fi
"$PY" scripts/package_ubuntu_results.py --run-id "$1"
