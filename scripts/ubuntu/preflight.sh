#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${SIRIUS_PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PY" ]] || { echo "Missing environment $PY; run scripts/ubuntu/setup.sh" >&2; exit 2; }
echo "=== OS/kernel ==="; cat /etc/os-release; uname -a
echo "=== Python/packages ==="; "$PY" --version; "$PY" -m pip list --format=columns
echo "=== CPU/RAM ==="; lscpu | sed -n '1,24p'; free -h
echo "=== NVIDIA/CUDA ==="; if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi; else echo "nvidia-smi unavailable"; fi
if command -v nvcc >/dev/null 2>&1; then echo "=== CUDA Toolkit (nvcc) ==="; nvcc --version; else echo "CUDA Toolkit nvcc: unavailable (separate from driver compatibility)"; fi
PYTHONPATH=candidate_ai/src "$PY" -m benchmarking.runners.environment_probe --machine-id ubuntu-amd-ryzen6600h-rtx3050-laptop --output /tmp/sirius-ubuntu-preflight-manifest.json
PYTHONPATH=candidate_ai/src "$PY" scripts/run_ubuntu_campaign.py --dry-run
