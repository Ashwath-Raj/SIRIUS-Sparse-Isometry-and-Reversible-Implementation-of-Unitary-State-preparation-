# Candidate implementation package

This directory contains an independent Python implementation of the sparse quantum state-preparation algorithms and logical circuit model.

## Environment

The Phase 3–8 core is CPU-first. CuPy is optional and used only for vectorized `uint64` batches of computational-basis rows (`1 <= n <= 63`). It is not used by the current exact complex-statevector preparation verifier.

## Usage

Run from repository root:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -c 'from sparseprep import SparseStateProblem, prepare_sparse_state; p = SparseStateProblem(n=4, support=("0001", "0110", "1011"), coefficients=(1/3**0.5, 1j/3**0.5, -1/3**0.5), signs=(1,-1,1)); c, m = prepare_sparse_state(p); print(m); print(c.resources)'
```

For construction without an exponential statevector allocation, use `compile_sparse_state_preparation`. Exact verification has a configurable total-qubit cap.

## Comparators

- `run_malvetti_baseline(problem)` — sequential isometry baseline.
- `run_batched_isometry(problem)` — independent batched isometry constructor.
- `run_algorithm3(problem, signs=...)` — sign-marker Algorithm 3 path.
- `compile_sparse_state_preparation(problem)` — complete logical circuit compilation.

The external authors' artifact is maintained separately and is not imported by this package.
