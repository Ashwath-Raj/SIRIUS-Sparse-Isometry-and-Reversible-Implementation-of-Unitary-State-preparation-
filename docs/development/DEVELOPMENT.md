# Developer Guide — SIRIUS

## 1. Environment Setup

### 1.1 Requirements
- Python 3.10, 3.11, 3.12, 3.13, or 3.14.
- Standard C/C++ compiler toolchain (optional, for dependencies).
- Optional: NVIDIA GPU with CUDA driver and toolkit for CuPy backend.

### 1.2 Recommended Local Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade packaging tools
python -m pip install --upgrade pip setuptools wheel

# Install in editable mode with development dependencies
python -m pip install -e ".[dev]"
```

### 1.3 Optional GPU Setup (CuPy)
CuPy is strictly optional. To enable GPU basis-row batch simulation on a system with NVIDIA hardware:
```bash
# Check CUDA driver version via nvidia-smi
nvidia-smi

# For CUDA 12.x:
pip install cupy-cuda12x

# For CUDA 13.x:
pip install cupy-cuda13x
```

---

## 2. Testing and Validation

### 2.1 Run All Tests
From the repository root:
```bash
pytest
```

### 2.2 Run Specific Test Suites
```bash
# Run candidate algorithm tests only
pytest candidate_ai/tests -v

# Run root integration tests (hardware probe, plan validation)
pytest tests -v

# Run GPU parity test explicitly (skipped automatically if CuPy is not available)
pytest candidate_ai/tests/test_cupy_parity.py -v
```

### 2.3 Run Phase 9.1 Benchmark Plan Validator
```bash
# Validate full plan (dry run)
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json

# Emit dry-run smoke tier manifest
python scripts/phase9_1_validate.py \
  --plan benchmarking/config/phase9_1_benchmark_plan.json \
  --tier smoke \
  --emit-manifest /tmp/sirius-smoke-plan.json
```

---

## 3. Benchmarking (Phase 9.2)

### 3.1 Environment Probe
Collects a sanitized hardware and software environment manifest:
```bash
python -m benchmarking.runners.environment_probe --output environment/local-environment.json
```

### 3.2 Execute Benchmark Sweeps
Execute device-local benchmarks using deterministic seeds:
```bash
# Run smoke tier on CPU comparators
python -m benchmarking.runners.run_benchmarks \
  --tier smoke \
  --methods independent_batched_isometry malvetti_baseline \
  --output results/raw

# Run with GPU basis-row batch throughput lane (if CUDA available)
python -m benchmarking.runners.run_benchmarks \
  --tier smoke \
  --methods independent_batched_isometry \
  --enable-gpu \
  --output results/raw
```

### 3.3 Validate and Aggregate Records
```bash
python -m benchmarking.analysis.aggregate \
  --input results/raw \
  --output results/summaries/smoke_summary.json
```

---

## 4. Coding Conventions & Invariants

1. **Big-Endian Wires:** Bitstrings and quantum registers use big-endian ordering. Wire 0 is the most significant bit.
2. **Immutability:** Problem instances (`SparseStateProblem`), gate representations (`Gate`), and steps are immutable frozen dataclasses.
3. **No Unbounded Statevectors:** Exact statevector simulation is strictly capped ($\le 20$ qubits) to prevent out-of-memory errors.
4. **Preserve Public API:**
   ```python
   from sparseprep import (
       SparseStateProblem,
       run_malvetti_baseline,
       run_batched_isometry,
       run_algorithm3,
       compile_sparse_state_preparation,
       prepare_sparse_state,
   )
   ```
5. **No Secret or Machine-Specific Data:** Never commit raw local hardware paths, usernames, or telemetry JSONs with private identifiers.
