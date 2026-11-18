#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${SIRIUS_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3.12)"
  else PYTHON_BIN="$(command -v python3)"; fi
fi
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .venv
elif [[ "$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "$PY_MINOR" ]]; then
  echo "Existing .venv uses another Python; preserving it. Creating .venv-ubuntu-$PY_MINOR" >&2
  VENV_DIR=".venv-ubuntu-$PY_MINOR"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then "$PYTHON_BIN" -m venv "$VENV_DIR"; fi
else
  VENV_DIR=".venv"
fi
VENV_DIR="${VENV_DIR:-.venv}"
PY="$ROOT/$VENV_DIR/bin/python"
"$PY" -m pip install --upgrade pip setuptools wheel
"$PY" -m pip install -e '.[dev,benchmarks]'
if command -v nvidia-smi >/dev/null 2>&1; then
  if "$PY" -c 'import cupy as cp; cp.cuda.runtime.getDeviceCount(); cp.asarray([0], dtype=cp.uint64).copy(); cp.cuda.Stream.null.synchronize()' >/dev/null 2>&1; then
    echo "Working CuPy/CUDA installation found; preserving installed distribution."
  else
    EXISTING_CUPY="$("$PY" - <<'PY'
from importlib.metadata import distributions
names = sorted({d.metadata.get("Name", "").lower() for d in distributions() if d.metadata.get("Name", "").lower() in {"cupy", "cupy-cuda12x", "cupy-cuda13x"}})
print(" ".join(names))
PY
)"
    if [[ "$EXISTING_CUPY" == "cupy-cuda12x" || "$EXISTING_CUPY" == "cupy-cuda13x" ]]; then
      CUPY_PACKAGE="$EXISTING_CUPY[ctk]"
    elif [[ -n "$EXISTING_CUPY" ]]; then
      echo "Found unsupported generic/multiple CuPy distributions ($EXISTING_CUPY); refusing to install a second CuPy distribution." >&2
      echo "CPU dependencies are installed; resolve the CuPy distribution choice manually." >&2
      exit 2
    else
      CUDA_COMPAT="$(nvidia-smi | sed -n 's/.*CUDA Version: *\([0-9][0-9.]*\).*/\1/p' | head -n1)"
      case "$CUDA_COMPAT" in
        13.*) CUPY_PACKAGE="cupy-cuda13x[ctk]" ;;
        12.*) CUPY_PACKAGE="cupy-cuda12x[ctk]" ;;
        *) echo "No supported CUDA compatibility family detected ($CUDA_COMPAT); leaving CPU setup ready." >&2; exit 0 ;;
      esac
    fi
    "$PY" -m pip install "$CUPY_PACKAGE"
    if ! "$PY" -c 'import cupy; cupy.cuda.runtime.getDeviceCount()' >/dev/null 2>&1; then
      echo "CuPy install did not produce a usable CUDA runtime; CPU setup remains installed." >&2
      exit 2
    fi
  fi
else
  echo "nvidia-smi unavailable; CPU setup is ready, GPU lane will report unavailable."
fi
echo "Setup complete. Environment: $VENV_DIR"
