# SIRIUS — Sparse Isometry and Reversible Implementation of Unitary State Preparation

[![Tests & Regression Gates](https://github.com/placeholder/sirius/actions/workflows/tests.yml/badge.svg)](https://github.com/placeholder/sirius/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![DOI: 10.22331/q-2026-09-10-2208](https://img.shields.io/badge/DOI-10.22331%2Fq--2026--09--10--2208-blue.svg)](https://doi.org/10.22331/q-2026-09-10-2208)

---

## 1. What SIRIUS Is

**SIRIUS** (*Sparse Isometry and Reversible Implementation of Unitary State Preparation*) is an independent, reproducible Python research implementation and benchmarking system for sparse quantum state preparation.

It provides an independent implementation and experimental evaluation of sparse-state preparation methods. The theoretical resource improvements originate in the referenced paper; the repository documents which implementation and benchmark results have actually been reproduced.

---

## 2. Theoretical Paper Reference

SIRIUS implements and validates the quantum algorithm introduced in:

> **Felix Rupprecht and Sabine Wölk (2026)**  
> *Sparse quantum state preparation with improved Toffoli cost*  
> **Quantum 10, 2208 (2026)**  
> **DOI:** [10.22331/q-2026-09-10-2208](https://doi.org/10.22331/q-2026-09-10-2208)  
> **Paper URL:** [https://quantum-journal.org/papers/q-2026-09-10-2208/](https://quantum-journal.org/papers/q-2026-09-10-2208/)  
> **Official Authors' Artifact:** Zenodo Record [18234600](https://zenodo.org/records/18234600) (Expected Archive MD5: `c58634ba415b4e3fb729648460f32ad7`)

---

## 3. What Problem It Solves

Given an arbitrary $s$-sparse quantum state on $n$ qubits:

\[
|\psi\rangle = \sum_{i=0}^{s-1} a_i c_i |x_i\rangle
\]

where:
- $\mathcal{S} = \{x_0, \dots, x_{s-1}\} \subset \{0, 1\}^n$ are distinct computational basis states.
- $c_i \in \mathbb{C}$ are arbitrary normalized coefficients ($\sum |c_i|^2 = 1$).
- $a_i \in \{+1, -1\}$ are independent real-sign metadata.
- $\ell = \lceil \log_2(s) \rceil$ is the subspace register width.
- $r = n - \ell$ is the residual register width.

Conventional techniques (e.g. Malvetti et al.) require $s(\ell - 1)$ Toffoli gates to compress non-subspace residual wires. Rupprecht & Wölk's batched isometry groups residual bit flips into batches of size at most $2^r$ using Partial Unary Iteration (PUI) trees, achieving substantially lower asymptotic and concrete Toffoli gate costs.

---

## 4. What Is Independently Implemented

The `sparseprep` package (`candidate_ai/src/sparseprep/`) contains a 100% clean-room, independent implementation of:
1. **Validated Problem Model (`model.py`):** Immutable problem representation with strict distinctness, big-endian bitstrings, and coefficient validation.
2. **Reversible Gate IR & Simulator (`gates.py`, `simulator.py`, `tableau.py`):** Explicit reversible gate models, tableaux, and exact basis-state simulation without materializing full Hilbert spaces.
3. **Malvetti Comparator Baseline (`malvetti_baseline.py`):** Sequential isometry baseline for comparative evaluation.
4. **PUI Interval Plans & Tree Emitter (`pui.py`, `pui_tree.py`):** Reversible restricted and unrestricted PUI tree circuit emitters with clean-ancilla uncomputation.
5. **Batched Isometry Construction (`batched_isometry.py`):** Independent batched isometry algorithm with forward and inverse mapping verification.
6. **Algorithm 3 Sign/Marker Model (`algorithm3.py`, `algorithms/phase_fixing.py`):** Sign- and marker-aware construction integrating real sign fixing.
7. **Phase Synthesis (`phase_synthesis.py`):** Clean-ancilla ladder diagonal real-sign phase oracle.
8. **End-to-End State Preparation (`state_preparation.py`):** Dense compact register loader, diagonal phase injection, inverse isometry, and marker uncomputation, verified by an exact statevector verifier (bounded by a qubit cap).
9. **GPU Basis-Batch Simulator (`backends/cupy_simulator.py`):** Vectorized CuPy simulator transforming batches of computational basis rows encoded as `uint64`.

---

## 5. Development Phases & Current Status

| Phase | Milestone Scope | Status | Evidence |
|---|---|---|---|
| **Phase 1–2** | Source integrity, hardware probe, reference audit | Completed | `research/validation/PHASE1_VALIDATION.md`, `research/maintenance/` |
| **Phase 3** | Problem model, gate IR, CPU simulator | Completed | `candidate_ai/src/sparseprep/model.py`, `gates.py`, `simulator.py` |
| **Phase 4** | Malvetti isometry baseline | Completed | `candidate_ai/src/sparseprep/malvetti_baseline.py` |
| **Phase 5** | PUI tree circuit emitter | Completed | `candidate_ai/src/sparseprep/pui.py`, `pui_tree.py` |
| **Phase 6** | Batched isometry construction | Completed | `candidate_ai/src/sparseprep/batched_isometry.py` |
| **Phase 7** | Algorithm 3 sign- and marker-aware construction | Completed | `candidate_ai/src/sparseprep/algorithm3.py` |
| **Phase 8** | Phase synthesis and end-to-end state preparation | Completed | `candidate_ai/src/sparseprep/state_preparation.py`, `phase_synthesis.py` |
| **Phase 9.1** | Benchmark architecture, schemas, and plan design | Completed | `benchmarking/config/`, `benchmarking/schemas/` |
| **Phase 9.2** | Device-local benchmark execution & research validation | **Bounded campaign completed; paper reproduction partial** | `docs/research/PUBLIC_BENCHMARK_RESULTS.md`; campaign release |

---

## 6. What Phase 9.2 Does

Phase 9.2 turns the Phase 9.1 benchmark architecture into an executable, reproducible system:
- **Environment Probe:** Detects sanitized hardware and runtime details (CPU, RAM, GPU, driver, CUDA, CuPy).
- **Benchmark Runner:** Executes parameterized workloads across comparison methods with high-resolution wall-clock (`perf_counter_ns`) and CPU (`process_time_ns`) timers, peak RSS tracking, and process isolation.
- **Statistical Aggregation:** Aggregates immutable raw JSONL records, calculating median, IQR, min, max, and 95% bootstrap confidence intervals over independent seeds.
- **GPU Basis-Row Lane:** Applies emitted SIRIUS reversible operations to basis rows on CUDA when available and checks parity against the CPU simulator. This is not complex-amplitude simulation. The Ubuntu RTX 3050 campaign is separately recorded under `results/raw/<machine-id>/`; the earlier Phase 9.2 validation report remains a historical no-GPU run.

---

## 7. Repository Layout

```text
SIRIUS/
├── README.md               # Authoritative research project entrypoint
├── LICENSE                 # Apache License Version 2.0
├── CITATION.cff            # Citation metadata for paper and code
├── pyproject.toml          # PEP 621 packaging and pytest configuration
├── .gitignore              # Git hygiene excluding caches, venvs, local telemetry
├── .python-version         # Pinned Python version (3.12)
│
├── candidate_ai/           # Independent implementation
│   ├── src/sparseprep/     # Core quantum package
│   │   ├── __init__.py     # Public API exports
│   │   ├── model.py        # Validated sparse problem model
│   │   ├── gates.py        # Reversible gate IR
│   │   ├── simulator.py    # CPU basis simulator
│   │   ├── tableau.py      # Tableau tracking
│   │   ├── resources.py    # Resource accounting
│   │   ├── pui.py          # PUI interval cost models
│   │   ├── pui_tree.py     # Reversible PUI tree circuit emitter
│   │   ├── malvetti_baseline.py # Malvetti baseline
│   │   ├── batched_isometry.py  # Independent batched isometry
│   │   ├── algorithm3.py   # Algorithm 3 sign/marker handling
│   │   ├── phase_synthesis.py   # Real-sign phase oracle
│   │   ├── state_preparation.py # End-to-end logical state preparation
│   │   ├── support_generators.py # Deterministic workload generators
│   │   ├── algorithms/     # Phase fixing and signed tableaux
│   │   └── backends/       # CuPy uint64 batch simulator
│   └── tests/              # Algorithm and invariant regression tests
│
├── benchmarking/           # Benchmark infrastructure
│   ├── config/             # Phase 9.1 benchmark plan (JSON)
│   ├── schemas/            # JSON Schemas for records, manifests, summaries
│   ├── templates/          # Record templates
│   ├── runners/            # Phase 9.2 runners and environment probe
│   ├── analysis/           # Statistical aggregation and plotting
│   └── results/            # Benchmark outputs (uncommitted)
│
├── docs/                   # Structured technical documentation
│   ├── architecture/       # Architecture and overview
│   ├── methodology/        # Mathematical implementation guide
│   ├── benchmarking/       # Phase 9.1 design & Phase 9.2 protocol
│   └── development/        # Developer setup and instructions
│
├── reference/              # Reference material
│   ├── authors-artifact/   # Verified Zenodo ZIP and extracted source
│   └── sources/            # Original paper PDF and guides
│
├── research/               # Research records & archive
│   ├── decisions/          # Architectural decisions log
│   ├── maintenance/        # Audit reports and source manifests
│   ├── validation/         # Historical milestone validation records
│   └── archive/phases/     # Historical phase sprint checklists & readmes
│
├── scripts/                # Helper utilities and plan validators
└── tests/                  # Root integration and probe tests
```

---

## 8. Installation

### Quick Start (Editable Install)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

### Optional GPU Installation
For GPU basis-row batch throughput testing (requires NVIDIA GPU with CUDA driver):
```bash
# Prefer the runtime-aware Ubuntu setup, which checks driver compatibility and kernel-header availability.
bash scripts/ubuntu/setup.sh
```

### Ubuntu reproducibility workflow

On Ubuntu, use the idempotent scripts. They do not install system packages or drivers and preserve an existing `.venv` that uses another Python version.

```bash
bash scripts/ubuntu/setup.sh
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" bash scripts/ubuntu/preflight.sh
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" bash scripts/ubuntu/run_laptop_pilot.sh
```

The bounded combined pilot writes separate raw result tracks for original random-support paper reproduction and the exploratory **Symmetry-Structured Sparse Supports** extension. The CuPy lane executes emitted reversible gates on `uint64` computational-basis rows with CPU parity. It does not perform GPU construction or complex-amplitude statevector simulation. See [Ubuntu setup](docs/development/UBUNTU_SETUP.md), [the RTX 3050 workflow](docs/benchmarking/UBUNTU_RTX3050_WORKFLOW.md), and [result layout](docs/benchmarking/RESULTS_LAYOUT.md).

---

## 9. Running Tests

Run the complete regression suite:
```bash
pytest
```

Run candidate algorithm tests specifically:
```bash
pytest candidate_ai/tests -v
```

All tests run on CPU by default. Optional CuPy tests automatically detect CUDA availability and run only when hardware/libraries are present.

---

## 10. Running Benchmarks

### 10.1 Validate Benchmark Plan (Dry Run)
```bash
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json
```

### 10.2 Run Phase 9.2 Smoke Benchmark
```bash
# CPU comparators on smoke tier
python -m benchmarking.runners.run_benchmarks \
  --tier smoke \
  --methods independent_batched_isometry malvetti_baseline \
  --output results/raw

# Aggregate raw results
python -m benchmarking.analysis.aggregate \
  --input results/raw \
  --output results/summaries/smoke_summary.json
```

---

## 11. GPU Backend Boundaries

The CuPy backend (`sparseprep.backends.cupy_simulator`) executes supported reversible gates over batches of computational-basis rows represented as `uint64` integers ($1 \le n \le 63$).
- **What it is:** A classical basis-row executor that can check CPU parity for emitted reversible gate sequences when CUDA is available.
- **What it is NOT:** It is NOT a complex-amplitude statevector simulator. It does NOT implement circuit compilation on GPU. It does NOT distribute a statevector across multiple GPUs.
- GPU lane results distinguish transfer, kernel and total lane time. Any performance observation belongs to its machine-specific run; basis-row throughput is not a statevector speedup or a construction acceleration claim.

---

## 12. What Is Not Yet Implemented

1. **Hardware-Native Transpilation:** Circuit outputs are logical reversible gate IR (`CMX`, `CX`, `MCX`, `Toffoli`). Physical hardware gate counts (e.g. Clifford+T, native 2-qubit gates, physical depth) require transpilation to a concrete hardware basis.
2. **Reproduction coverage:** The published RTX 3050 campaign is a partial Figure 10 reproduction. The `10^7` points did not complete, `10^6` is incomplete, matched SIRIUS–Malvetti scaling is limited, and the symmetry extension remains exploratory.

---

## 13. Reproducibility & Public API Contract

The public import API is guaranteed:

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

### Example Usage:
```python
from sparseprep import SparseStateProblem, prepare_sparse_state

# 4-qubit, 3-sparse target state
problem = SparseStateProblem(
    n=4,
    support=("0001", "0110", "1011"),
    coefficients=(1 / 3**0.5, 1j / 3**0.5, -1 / 3**0.5),
    signs=(1, -1, 1),
)

circuit, metrics = prepare_sparse_state(problem)
print("Fidelity:", metrics.fidelity)
print("Resources:", circuit.resources)
```

---

<!-- SIRIUS_PUBLIC_BENCHMARK_EVIDENCE_BEGIN -->

## 14. Reproduced benchmark evidence (Ubuntu RTX 3050)

The completed campaign and data-quality closure are published as immutable assets in the [SIRIUS Ubuntu RTX 3050 benchmark release](https://github.com/Ashwath-Raj/SIRIUS-Sparse-Isometry-and-Reversible-Implementation-of-Unitary-State-preparation-/releases/tag/sirius-ubuntu-rtx3050-campaign-20261117). Detailed tables, plots, attempt accounting and limitations are in [PUBLIC_BENCHMARK_RESULTS.md](docs/research/PUBLIC_BENCHMARK_RESULTS.md).

| Track | Attempts | Completed | Failed | Timed out | Resource-capped |
|---|---:|---:|---:|---:|---:|
| Authors' Figure 10 reproduction | 469 | 316 | 51 | 14 | 88 |
| Symmetry extension | 216 | 204 | 0 | 12 | 0 |

Figure 10 coverage: both variants completed 19/19 selected widths for each of \(10^2\)–\(10^5\); 15/19 at \(10^6\); no completed measurements at \(10^7\). This is a partial reproduction.

At \(n=9,s=100\), the five-seed matched SIRIUS–Malvetti experiment recorded median runtimes of 289.889 ms and 100.483 ms, respectively. These are implementation-level timings with distinct timing scopes, not an authors' Figure 10 speedup comparison. The symmetry extension has three independent seeds per stratum and is exploratory.

The GPU lane is CuPy `uint64` basis-row simulation, not complex-amplitude statevector simulation. The report and release archive preserve failures, timeouts, resource caps, duplicate-attempt audits, raw JSONL records and checksums. Do not interpret timer repetitions or duplicate job attempts as independent seeds.

<!-- SIRIUS_PUBLIC_BENCHMARK_EVIDENCE_END -->

## 15. Citation

If you use this software, please cite both the paper and this implementation:

```bibtex
@article{rupprecht2026sparse,
  author    = {Rupprecht, Felix and W{\"o}lk, Sabine},
  title     = {Sparse quantum state preparation with improved Toffoli cost},
  journal   = {Quantum},
  volume    = {10},
  pages     = {2208},
  year      = {2026},
  doi       = {10.22331/q-2026-09-10-2208},
  url       = {https://quantum-journal.org/papers/q-2026-09-10-2208/}
}
```
