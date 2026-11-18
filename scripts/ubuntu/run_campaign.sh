#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${SIRIUS_PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PY" ]] || { echo "Missing environment $PY; run scripts/ubuntu/setup.sh" >&2; exit 2; }
if [[ $# -lt 1 ]]; then echo "Usage: $0 paper_reproduction|symmetry_structured_sparse_supports [runner args...]" >&2; exit 2; fi
TRACK="$1"; shift
RUN_ID="${SIRIUS_RUN_ID:-campaign-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_DIR="$ROOT/results/logs/ubuntu-amd-ryzen6600h-rtx3050-laptop"
mkdir -p "$LOG_DIR"
PYTHONPATH=candidate_ai/src "$PY" scripts/run_ubuntu_campaign.py --track "$TRACK" --run-id "$RUN_ID" "$@" 2>&1 | tee "$LOG_DIR/$RUN_ID.log"
