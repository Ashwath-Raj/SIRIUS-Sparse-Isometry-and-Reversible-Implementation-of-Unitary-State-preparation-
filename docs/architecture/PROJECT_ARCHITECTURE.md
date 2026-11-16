# SIRIUS Project Architecture

**SIRIUS: Sparse Isometry and Reversible Implementation of Unitary State Preparation**

---

## 1. System Overview

SIRIUS implements an independent, research-grade pipeline for sparse quantum state preparation based on the algorithm of Rupprecht & Wölk (Quantum 10, 2208, 2026). The software synthesizes reversible quantum circuits that prepare an arbitrary $s$-sparse quantum state on $n$ qubits:

\[
|\psi\rangle = \sum_{i=0}^{s-1} a_i c_i |x_i\rangle
\]

where:
- $x_i \in \{0, 1\}^n$ are distinct computational basis states.
- $c_i \in \mathbb{C}$ are normalized complex coefficients ($\sum |c_i|^2 = 1$).
- $a_i \in \{+1, -1\}$ are optional real-sign metadata.
- $\ell = \lceil \log_2(s) \rceil$ is the subspace register width.
- $n - \ell$ is the residual register width.

---

## 2. Layered Module Architecture

```text
SIRIUS Architecture Pipeline
┌─────────────────────────────────────────────────────────────────────────────┐
│ Problem Specification & Support Generators                                  │
│   sparseprep.model (SparseStateProblem, validation, bitstring conversion)   │
│   sparseprep.support_generators (deterministic seeded random/prefix sweeps) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Classical Synthesis & Reversible Compilation                                │
│                                                                             │
│  [Comparator Baseline]           [Primary Isometry Pipeline]                │
│  sparseprep.malvetti_baseline     sparseprep.batched_isometry                │
│  (Sequential ell-controlled X)    (Independent Batched Isometry)            │
│                                      ├── sparseprep.pui (PUI plan & bounds) │
│                                      └── sparseprep.pui_tree (Tree emitter) │
│                                                                             │
│  [Algorithm 3 Sign/Marker Path]                                             │
│  sparseprep.algorithm3                                                      │
│  └── sparseprep.algorithms.phase_fixing (Signed tableau phase fixing)       │
│                                                                             │
│  [Real-Sign Phase Synthesis]                                                │
│  sparseprep.phase_synthesis (Clean-ancilla ladder phase oracle)             │
│                                                                             │
│  [End-to-End Logical State Preparation]                                     │
│  sparseprep.state_preparation (Dense loader + Phase synthesis + Inverse iso) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Simulation, Verification & Parity Verification                              │
│   sparseprep.simulator (Exact CPU reversible basis-row simulation)          │
│   sparseprep.state_preparation (Exact statevector verifier, qubit cap <=20)│
│   sparseprep.backends.cupy_simulator (Vectorized uint64 batch row parity)   │
│   sparseprep.resources (Emitted IR vs paper-accounted Toffoli metrics)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Benchmarking Infrastructure (Phase 9.1 & 9.2)                               │
│   benchmarking.config (phase9_1_benchmark_plan.json)                        │
│   benchmarking.schemas (machine-manifest, run-record, summary JSON schemas) │
│   benchmarking.runners.environment_probe (Sanitized multi-platform probe)   │
│   benchmarking.runners.run_benchmarks (Automated isolated runner)           │
│   benchmarking.analysis.aggregate (Statistical aggregation & bootstrap CI)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow & Compilation Pipeline

1. **Input Problem Ingestion:**
   `SparseStateProblem` receives $n$, support bitstrings $\{x_i\}$, coefficients $c_i$, and signs $a_i$. It validates distinctness, normalization, and big-endian bitstring formatting.

2. **Batched Isometry Construction (`batched_isometry.py`):**
   - Partitions target support into batches of size at most $2^{n-\ell}$.
   - Evaluates Partial Unary Iteration (PUI) intervals using `pui.py` and emits circuits via `pui_tree.py`.
   - Generates forward circuit $G$ mapping $|x_i\rangle \to |f(i)\rangle|0^{n-\ell}\rangle$.
   - Computes $G^\dagger$ as the preparation isometry.

3. **Algorithm 3 Sign/Marker Path (`algorithm3.py`):**
   - Tracks marker wires separating positive from negative sign classes.
   - Applies sign-aware permutation logic to reduce phase fixing overhead.

4. **Phase Synthesis (`phase_synthesis.py`):**
   - Synthesizes a diagonal real-sign phase oracle applying $(-1)$ phases to required compact address labels.
   - Utilizes a clean-ancilla ladder for multi-controlled phase operations with exact uncomputation.

5. **End-to-End State Preparation (`state_preparation.py`):**
   - **Stage 1 (Dense Loading):** Prepares $s$ compact state amplitudes on the $\ell$-qubit subspace register using Givens rotations / multi-controlled $R_y$ gates.
   - **Stage 2 (Phase Synthesis):** Applies diagonal phase corrections for real signs ($a_i$) and complex argument angles ($\arg(c_i)$).
   - **Stage 3 (Isometry Expansion):** Inverts the batched isometry $G^\dagger$, mapping compact subspace basis states $|f(i)\rangle|0^{n-\ell}\rangle$ to physical target states $|x_i\rangle$.
   - **Stage 4 (Uncomputation):** Cleans all workspace and marker ancillas.

---

## 4. Execution Boundaries & Hardware Responsibilities

### CPU Responsibilities
- Deterministic workload generation and rejection sampling.
- Reversible circuit compilation, PUI tree emission, and gate list manipulation.
- Exact computational-basis tableau tracking and verification.
- Exact complex-amplitude statevector verification (capped at $\le 20$ qubits to prevent exponential memory consumption).
- Timing (`time.perf_counter_ns`, `time.process_time_ns`), process isolation, and schema validation.

### GPU Responsibilities (Optional CuPy Backend)
- Vectorized computational-basis transformation of large row batches represented as `uint64` integers.
- Supported for data-wire width $1 \le n \le 63$.
- Synchronized CUDA execution timing with host-to-device and device-to-host transfer times explicitly separated.
- **Explicit Boundary:** The GPU lane is NOT a statevector simulator. It does NOT construct circuits, pool VRAM across devices, or simulate complex-amplitude quantum statevectors.

---

## 5. Logical Resource Accounting Boundaries

Resource metrics are kept strictly categorized:

| Resource Class | Definition & Accounting Rule |
|---|---|
| **Paper-Accounted Toffoli** | Theoretical cost based on Rupprecht & Wölk (2026) cost models (e.g. $s(\ell-1)$ for Malvetti; PUI tree Equations 7 and 8). |
| **Coherent Toffoli** | Count of explicit 3-qubit Toffoli gates required when decomposing multi-controlled operations with clean ancillas. |
| **Emitted IR Toffoli** | Exact count of primitive `Toffoli` and `NegativeControlToffoli` instances present in the emitted gate sequence. |
| **Logical Qubits** | Total active wires ($n$ data wires + clean ancilla pool + marker wires). |
| **Clean Ancillas** | Ancilla qubits initialized to $|0\rangle$ and returned to $|0\rangle$ at circuit termination. |
| **Native Gate Count** | *Not reported* until transpiled to a concrete physical hardware basis (e.g. Clifford+T). |
