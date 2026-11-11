#!/usr/bin/env bash
# Phase 2: reproduce and inspect the authors' official reference artifact.
# Safe by default: never edits reference source/lockfiles and never pushes to remotes.
set -u -o pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: run this script from inside the project Git repository." >&2
  exit 2
}
ARTIFACT_ROOT="$ROOT/reference/authors-artifact"
ARCHIVE="$ARTIFACT_ROOT/official-artifact.zip"
SOURCE_ROOT="$ARTIFACT_ROOT/source"
OUT="$ROOT/results/raw/phase2"
mkdir -p "$OUT" "$ROOT/research-notes"

EXPECTED_MD5="c58634ba415b4e3fb729648460f32ad7"

run_logged() {
  local name="$1"; shift
  local logfile="$OUT/${name}.log"
  echo
  echo "===== $name ====="
  printf 'COMMAND:'; printf ' %q' "$@"; echo
  "$@" >"$logfile" 2>&1
  local status=$?
  cat "$logfile"
  printf '%s\n' "$status" > "$OUT/${name}.exit_code"
  echo "EXIT CODE: $status"
  return 0
}

cat > "$OUT/phase2_environment.txt" <<ENV
captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
project_root=$ROOT
branch=$(git -C "$ROOT" branch --show-current)
ENV

run_logged git_status git -C "$ROOT" status --short --branch
run_logged git_log git -C "$ROOT" log --oneline -12
run_logged host_python python3 --version
run_logged uv_version uv --version
run_logged rustc_version rustc --version
run_logged cargo_version cargo --version

if [[ ! -f "$ARCHIVE" ]]; then
  echo "ERROR: official artifact ZIP missing: $ARCHIVE" | tee "$OUT/blocker.txt"
  exit 3
fi
if [[ ! -d "$SOURCE_ROOT" ]]; then
  echo "ERROR: official artifact has not been extracted: $SOURCE_ROOT" | tee "$OUT/blocker.txt"
  exit 3
fi

actual_md5="$(md5sum "$ARCHIVE" | awk '{print $1}')"
printf 'expected_md5=%s\nactual_md5=%s\n' "$EXPECTED_MD5" "$actual_md5" | tee "$OUT/archive_md5.txt"
if [[ "$actual_md5" != "$EXPECTED_MD5" ]]; then
  echo "ERROR: archive checksum mismatch; stop before installation." | tee "$OUT/blocker.txt"
  exit 4
fi

mapfile -t pyprojects < <(find "$SOURCE_ROOT" -mindepth 2 -maxdepth 4 -type f -name pyproject.toml -print)
if [[ ${#pyprojects[@]} -ne 1 ]]; then
  printf 'ERROR: expected exactly one artifact pyproject.toml, found %s\n' "${#pyprojects[@]}" | tee "$OUT/blocker.txt"
  printf '%s\n' "${pyprojects[@]}" >> "$OUT/blocker.txt"
  exit 5
fi
REF="$(dirname "${pyprojects[0]}")"
printf 'reference_project=%s\n' "$REF" | tee "$OUT/reference_project.txt"

if [[ ! -f "$REF/uv.lock" || ! -f "$REF/Cargo.lock" ]]; then
  echo "ERROR: expected uv.lock and Cargo.lock not both present." | tee "$OUT/blocker.txt"
  exit 6
fi
sha256sum "$REF/uv.lock" "$REF/Cargo.lock" > "$OUT/lockfiles.before.sha256"

# The Zenodo record warns about nbconvert <= 7.16.6 and explains it was removed
# from the uploaded uv.lock. Refuse to install if such a vulnerable package is locked.
lock_check="$(python3 - "$REF/uv.lock" <<'PY'
import sys, tomllib
from pathlib import Path
p = Path(sys.argv[1])
data = tomllib.loads(p.read_text())
found = []
for item in data.get('package', []):
    if item.get('name', '').lower() == 'nbconvert':
        found.append(str(item.get('version', 'unknown')))
print(','.join(found))
PY
)"
printf 'locked_nbconvert_versions=%s\n' "${lock_check:-none}" | tee "$OUT/nbconvert_lock_check.txt"
if [[ -n "$lock_check" ]]; then
  echo "STOP: nbconvert appears in uv.lock. Review the exact locked version and security advisory before installing. Do not modify or regenerate the lockfile." | tee "$OUT/blocker.txt"
  exit 7
fi

run_logged artifact_file_inventory find "$REF" -maxdepth 5 -type f -printf '%P\t%s bytes\n'
run_logged artifact_readme sed -n '1,240p' "$REF/README.md"
run_logged artifact_pyproject sed -n '1,240p' "$REF/pyproject.toml"
run_logged rust_manifest sed -n '1,200p' "$REF/Cargo.toml"
run_logged rust_source_inventory find "$REF/src/isometry_algorithms" -maxdepth 2 -type f -printf '%P\t%s bytes\n'
run_logged python_source_inventory find "$REF/src/sparse_state_preparation" -maxdepth 2 -type f -printf '%P\t%s bytes\n'

# Validate expected modules before attempting dependency installation.
for f in \
  "$REF/src/isometry_algorithms/column.rs" \
  "$REF/src/isometry_algorithms/gates.rs" \
  "$REF/src/isometry_algorithms/problem.rs" \
  "$REF/src/isometry_algorithms/tableau.rs" \
  "$REF/src/lib.rs" \
  "$REF/src/sparse_state_preparation/isometry.py" \
  "$REF/src/sparse_state_preparation/partial_unary_iteration.py" \
  "$REF/src/sparse_state_preparation/dense_state_preparation.py" \
  "$REF/examples.ipynb"; do
  if [[ ! -f "$f" ]]; then
    echo "MISSING: ${f#"$REF"/}" >> "$OUT/missing_expected_files.txt"
  fi
done

# `--frozen` consumes the supplied lockfile without updating it.
run_logged uv_sync_frozen bash -lc "cd '$REF' && uv sync --frozen"
uv_sync_status="$(cat "$OUT/uv_sync_frozen.exit_code")"
if [[ "$uv_sync_status" == "0" ]]; then
  run_logged python_pytest bash -lc "cd '$REF' && uv run --frozen pytest -q"
else
  echo "SKIPPED: Python tests because uv sync --frozen failed." > "$OUT/python_pytest.log"
  echo 125 > "$OUT/python_pytest.exit_code"
fi

run_logged rust_cargo_test bash -lc "cd '$REF' && cargo test --locked"

sha256sum "$REF/uv.lock" "$REF/Cargo.lock" > "$OUT/lockfiles.after.sha256"
if diff -u "$OUT/lockfiles.before.sha256" "$OUT/lockfiles.after.sha256" > "$OUT/lockfiles.diff"; then
  echo "PASS: uv.lock and Cargo.lock unchanged" | tee "$OUT/lockfile_integrity.txt"
else
  echo "FAIL: a reference lockfile changed; investigate and restore only from a verified original." | tee "$OUT/lockfile_integrity.txt"
fi

# Build a human-readable code map from the actual reference tree.
cat > "$ROOT/research-notes/REFERENCE_CODE_MAP.md" <<MAP
# Official Reference Artifact — Code Map

Generated by scripts/phase2_reference_audit.sh from the extracted Zenodo artifact.

- Project root: $REF
- Archive MD5: $actual_md5
- Python implementation: src/sparse_state_preparation/
- Rust isometry implementation: src/isometry_algorithms/
- Python/Rust wrapper: src/lib.rs
- Introductory notebook: examples.ipynb
- Figure-generation sources: figures/

## Key source files

| File | Role (based on filename and artifact inventory) |
|---|---|
| src/isometry_algorithms/column.rs | Rust column/tableau-column operations |
| src/isometry_algorithms/gates.rs | Rust gate representations/operations |
| src/isometry_algorithms/problem.rs | Rust isometry problem and construction logic |
| src/isometry_algorithms/tableau.rs | Rust tableau representation/updates |
| src/lib.rs | Python wrapper for Rust code |
| src/sparse_state_preparation/isometry.py | Qualtran isometry Bloqs |
| src/sparse_state_preparation/partial_unary_iteration.py | PUI Bloqs |
| src/sparse_state_preparation/dense_state_preparation.py | Dense-state preparation Bloqs |

This map is an initial structural map. Algorithm-to-function mappings must be confirmed by reading the definitions and tests, not inferred solely from filenames.

## Test commands

- Python: uv sync --frozen && uv run --frozen pytest -q
- Rust: cargo test --locked

See results/raw/phase2/ for logs and exit-code files.
MAP

cat > "$OUT/PHASE2_SUMMARY.txt" <<SUMMARY
Phase 2 reference audit completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)
Reference project: $REF
Archive MD5: $actual_md5
Python uv sync exit: $(cat "$OUT/uv_sync_frozen.exit_code" 2>/dev/null || echo not-run)
Python pytest exit: $(cat "$OUT/python_pytest.exit_code" 2>/dev/null || echo not-run)
Rust cargo test exit: $(cat "$OUT/rust_cargo_test.exit_code" 2>/dev/null || echo not-run)
Lockfile integrity: $(cat "$OUT/lockfile_integrity.txt" 2>/dev/null || echo not-checked)

IMPORTANT: inspect every log. A non-zero exit code is a failure/blocker, not a pass.
The reference source and lockfiles must remain unchanged.
No Git commit or remote operation was performed by this script.
SUMMARY

cat "$OUT/PHASE2_SUMMARY.txt"
echo
echo "Phase 2 audit logs: $OUT"
echo "Initial code map: $ROOT/research-notes/REFERENCE_CODE_MAP.md"
echo "Next: inspect logs, then commit only reviewed logs/code-map. Do not push."
