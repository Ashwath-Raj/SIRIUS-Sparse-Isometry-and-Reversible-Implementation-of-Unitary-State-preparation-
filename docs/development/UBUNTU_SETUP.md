# Ubuntu setup

The scripts target Ubuntu/Linux and never install system packages or NVIDIA drivers. They use Python 3.12 when available. An existing `.venv` is preserved if it uses a different Python; setup creates `.venv-ubuntu-3.12` in that case.

```bash
bash scripts/ubuntu/setup.sh
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" bash scripts/ubuntu/preflight.sh
```

The setup installs editable project, development, benchmark, and plotting requirements. It verifies a real CuPy kernel compile, not only device discovery. If an installed CuPy build lacks headers and NVRTC components, it installs that same distribution's `[ctk]` extra. If CuPy is absent, it selects `cupy-cuda13x[ctk]` or `cupy-cuda12x[ctk]` from the CUDA compatibility version reported by `nvidia-smi`. The extra supplies pip-managed toolkit components and does not modify system CUDA. That compatibility value is not the local CUDA Toolkit version; `nvcc --version` is reported independently. Unsupported or missing GPU environments retain a usable CPU setup.

`scripts/ubuntu/preflight.sh` writes a sanitized probe to `/tmp`, prints machine and software details, and emits the pilot job selection without executing workloads. Use `SIRIUS_PYTHON` to select a different local interpreter.
