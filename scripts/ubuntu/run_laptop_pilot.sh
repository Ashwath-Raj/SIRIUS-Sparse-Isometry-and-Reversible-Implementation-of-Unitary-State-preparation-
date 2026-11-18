#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${SIRIUS_PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PY" ]] || { echo "Missing environment $PY; run scripts/ubuntu/setup.sh" >&2; exit 2; }
RUN_ID="${SIRIUS_RUN_ID:-pilot-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_DIR="$ROOT/results/logs/ubuntu-amd-ryzen6600h-rtx3050-laptop"
mkdir -p "$LOG_DIR"
PYTHONPATH=candidate_ai/src "$PY" scripts/run_ubuntu_campaign.py --track both --max-attempts 64 --run-id "$RUN_ID" "$@" 2>&1 | tee "$LOG_DIR/$RUN_ID.log"
