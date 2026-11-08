#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 PHASE_NUMBER [OUTPUT_DIR]" >&2
  exit 2
fi
phase="$1"
if ! [[ "$phase" =~ ^[0-9]{1,2}$ ]]; then
  echo "Phase number must be numeric (for example 1 or 03)." >&2
  exit 2
fi
repo_root="$(git rev-parse --show-toplevel)"
output_dir="${2:-$(dirname "$repo_root")/$(basename "$repo_root")-handoff-phase-${phase}}"
mkdir -p "$output_dir"

bundle="$output_dir/phase-${phase}.bundle"
source_tar="$output_dir/phase-${phase}-source.tar.gz"
log="$output_dir/phase-${phase}-commit-log.txt"

# Capture all local refs; this does not contact or alter any remote.
git -C "$repo_root" bundle create "$bundle" --all
git -C "$repo_root" bundle verify "$bundle"
git -C "$repo_root" log --oneline --decorate --all > "$log"

# Portable source snapshot, excluding Git metadata, environments, caches and raw machine telemetry.
tar -czf "$source_tar" \
  --exclude='.git' --exclude='.venv' --exclude='venv' --exclude='__pycache__' \
  --exclude='.pytest_cache' --exclude='target' --exclude='build' --exclude='dist' \
  --exclude='*.pyc' --exclude='*.bundle' \
  -C "$(dirname "$repo_root")" "$(basename "$repo_root")"

sha256sum "$bundle" "$source_tar" > "$output_dir/SHA256SUMS"
cat > "$output_dir/HANDOFF.txt" <<EOF
Phase ${phase} handoff

Clone with history:
  git clone "$(basename "$bundle")" "$(basename "$repo_root")-phase-${phase}"

Inspect:
  git log --oneline --decorate -15
  git status --short --branch

The bundle contains local Git history and refs. No push was performed.
EOF

echo "Handoff created: $output_dir"
echo "Bundle: $bundle"
echo "Source archive: $source_tar"
