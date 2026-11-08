#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p results/raw environment
LOG="results/raw/phase-01-local-validation-$(date -u +%Y%m%dT%H%M%SZ).log"
{
  echo "Phase 1 local validation"
  echo "UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Host: $(hostname)"
  echo
  echo '=== Python tests ==='
  python3 -m unittest discover -s tests -v
  echo
  echo '=== Source SHA-256 manifest ==='
  python3 scripts/verify_sources.py
  echo
  echo '=== Hardware probe (CUDA required) ==='
  python3 scripts/hardware_probe.py --require-cuda --output environment/laptop-hardware.json
} 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}
echo "Log: $LOG"
exit "$status"
