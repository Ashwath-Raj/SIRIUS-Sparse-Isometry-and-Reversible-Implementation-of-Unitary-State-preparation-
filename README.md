# Independent Sparse Quantum State Preparation

**Research implementation and reproducibility study**  
**Paper:** Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026). [DOI: 10.22331/q-2026-09-10-2208](https://doi.org/10.22331/q-2026-09-10-2208)

## Project objective

Independently implement the paper's sparse-state preparation construction, verify the reversible mapping and full logical state-preparation behavior, then benchmark its resource scaling and classical/GPU execution characteristics against a Malvetti-style baseline and the authors' reference artifact.

Given unique computational-basis states `x_i` and normalized coefficients `c_i`, the target is

\[
|\psi\rangle=\sum_{i=0}^{s-1} a_i c_i|x_i\rangle,
\qquad a_i\in\{+1,-1\}.
\]

## Implementation status

| Milestone | Scope | Status |
|---|---|---|
| Phase 1–2 | Workspace, source integrity, reference audit | Completed |
| Phase 3 | Sparse-state model, gate IR, CPU/CuPy basis-row simulators | Completed |
| Phase 4 | Malvetti isometry baseline | Completed |
| Phase 5 | Restricted/unrestricted PUI tree emitter | Completed |
| Phase 6 | Batched isometry construction | Completed |
| Phase 7 | Algorithm 3 sign/marker handling | Completed |
| Phase 8 | Phase synthesis and end-to-end logical state preparation | Completed |
| Phase 9.1 | Benchmark architecture, experimental plan, data schemas, reproducibility and DGX access brief | Completed in this release |
| Phase 9.2 | Device-local benchmark runs and result collection | Not started; intentionally local/uncommitted |

## Current implementation

- `candidate_ai/src/sparseprep/model.py` — validated problem model.
- `candidate_ai/src/sparseprep/malvetti_baseline.py` — isometry baseline.
- `candidate_ai/src/sparseprep/batched_isometry.py` — independent batched construction.
- `candidate_ai/src/sparseprep/pui_tree.py` — PUI tree emitter.
- `candidate_ai/src/sparseprep/algorithm3.py` — signed/marker-aware construction.
- `candidate_ai/src/sparseprep/phase_synthesis.py` — real-sign diagonal phase oracle.
- `candidate_ai/src/sparseprep/state_preparation.py` — complete logical sparse-state preparation.

Public entrypoints:

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

## Validation

Use the project's existing virtual environment:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest candidate_ai/tests -q
```

Latest operator-reported Phase 8.2 regression: **148 passed, 2 skipped**. The two skips were optional CUDA tests unavailable in that Python environment. This is a correctness-test result, not a benchmark result.

## Benchmark design (Phase 9.1)

Dean-facing access brief: [`docs/PHASE9_1_DGX_ACCESS_BRIEF.pdf`](docs/PHASE9_1_DGX_ACCESS_BRIEF.pdf) (print-ready) and [`docs/PHASE9_1_DGX_ACCESS_BRIEF.md`](docs/PHASE9_1_DGX_ACCESS_BRIEF.md).

The committed `benchmarking/` directory defines a reproducible plan, metrics catalog, run/machine/summary schemas and templates. It separates:

1. CPU construction time and peak memory;
2. logical Toffoli/ancilla/gate resources;
3. correctness and bounded exact statevector validation;
4. optional GPU throughput for batches of computational-basis rows.

Validate and enumerate the proposed workloads without executing any algorithm:

```bash
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json --tier smoke --emit-manifest /tmp/sparseprep-smoke-plan.json
```

## GPU boundary — read before making claims

The current CuPy backend is a uint64 **basis-state row batch** simulator for 1–63 data wires. It is not a complex-amplitude statevector simulator. Phase 8's exact complex statevector verifier is CPU-side and capped. The current implementation does not pool GPU memory or distribute one statevector across multiple GPUs. Classical isometry construction remains CPU-side. GPU speedup claims are allowed only for the GPU-executed basis-row batch lane, with transfer time separated.

## Phase 9.2

Phase 9.2 is the device-local execution stage: hardware probes, environment setup, authors' artifact adapter, controlled runs on each available machine, raw JSON records, summary plots and comparison analysis. Keep machine manifests, raw results, temporary virtual environments and device-specific configuration local/uncommitted. Do not commit benchmark results until provenance and review are complete.

## Research sources

- Paper: https://quantum-journal.org/papers/q-2026-09-10-2208/
- DOI: https://doi.org/10.22331/q-2026-09-10-2208
- Authors' code and assets: https://zenodo.org/records/18234600
- Expected authors' artifact MD5: `c58634ba415b4e3fb729648460f32ad7`
