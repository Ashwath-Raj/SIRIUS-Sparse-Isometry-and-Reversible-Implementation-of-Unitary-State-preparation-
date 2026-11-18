#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${SIRIUS_PYTHON:-$ROOT/.venv/bin/python}"
"$PY" scripts/package_ubuntu_ready.py
