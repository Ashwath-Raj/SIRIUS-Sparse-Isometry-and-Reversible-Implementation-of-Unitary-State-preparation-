# Phase 9.1 — Cross-device benchmarking system design

## 1. Purpose

Phase 9.1 freezes the experimental design before device access. It defines how the current implementation will be measured consistently on the development laptop, an available workstation and an institutional DGX node. It does not execute a benchmark.

The benchmark has three distinct questions:

1. **Construction scalability:** how do classical isometry-finding time and memory scale with `(n,s)`?
2. **Logical resource scaling:** what Toffoli/ancilla/gate-IR resources are emitted, and how do they compare with the internal Malvetti baseline and eventually the authors' artifact?
3. **Execution/validation throughput:** how efficiently can basis-state rows be transformed and checked on CPU versus a single GPU, while preserving the same correctness contract?

These questions must not be collapsed into a single "speedup" number. GPU acceleration of a simulator does not reduce the logical Toffoli count.

## 2. System architecture

```mermaid
flowchart TD
    A[Versioned benchmark plan] --> B[Seeded workload generator]
    B --> C[Canonical problem record\n(n, s, support, coefficients, signs)]
    C --> D1[Independent batched isometry]
    C --> D2[Malvetti baseline]
    C --> D3[Authors reference adapter\nPhase 9.2 integration gate]
    D1 --> E[Correctness gate]
    D2 --> E
    D3 --> E
    E --> F1[Compiler timing + peak RSS]
    E --> F2[Logical resource accounting]
    E --> F3[CPU/CuPy basis-row execution]
    E --> F4[Small-instance exact statevector checks]
    F1 --> G[Immutable raw JSON records]
    F2 --> G
    F3 --> G
    F4 --> G
    G --> H[Schema/provenance validation]
    H --> I[Aggregation + plots + comparison report]
```

### Component contracts

| Component | Contract | Phase 9.1 status |
|---|---|---|
| Plan/config | Pinned sweep matrix, seeds, repetitions, limits | Implemented |
| Workload generator | Deterministic support/coefficient/sign input creation | Existing support generators; coefficient profiles specified for 9.2 |
| Compiler adapters | Same input contract for all algorithms | Current and Malvetti APIs identified; author adapter gated |
| Correctness gate | Distinct labels, zero residual, inverse round-trip; statevector when within cap | Implemented in current code; uniform runner wrapper is 9.2 |
| Timing/memory capture | Wall, CPU, peak RSS, timeout record | Defined; device runner in 9.2 |
| Logical resources | Paper/coherent Toffoli, emitted IR counts, logical qubits/ancillas | Existing estimates; unified record extraction in 9.2 |
| GPU row-batch lane | CuPy uint64 basis-state batch simulation | Existing optional backend; timing instrumentation in 9.2 |
| Exact statevector lane | Full complex-state fidelity and leakage for small instances | Existing CPU verifier; GPU full statevector not implemented |
| Storage/reporting | JSONL raw records, machine manifests, validated summaries | Schemas/templates in 9.1; aggregation runner in 9.2 |

## 3. Comparison methods

### A. Independent batched isometry

Primary project implementation: `sparseprep.run_batched_isometry` and `sparseprep.run_algorithm3`. For the complete state-preparation layer use `sparseprep.compile_sparse_state_preparation` and `prepare_sparse_state` only when within the exact verifier limit.

### B. Malvetti baseline

Internal comparator: `sparseprep.run_malvetti_baseline`. It must receive the exact same ordered support rows as the independent batched method. Its metric scope is the isometry, not the full dense coefficient loader. Compare like-for-like isometry metrics separately from complete state preparation.

### C. Authors' reference artifact

The published Zenodo artifact is the authoritative external implementation target. Phase 9.2 must pin the downloaded artifact hash, Python/Rust revisions and runtime command, then add a small adapter that converts generated problems into the reference API and normalizes its output. Until that adapter passes golden fixtures, do not place author-reference values in comparison plots.

## 4. Workload design

Every run is keyed by `(tier, n, s, support_family, coefficient_family, sign_profile, seed, algorithm_id)`.

| Tier | Purpose | Suggested domain |
|---|---|---|
| Smoke | Fast device acceptance and correctness | `n=8,12,16`; `s=1,2,3,4,7,8,15,16`; two seeds |
| Scaling | Main curve for construction and logical resources | `n=16,24,32,48,63`; `s=16,31,32,63,64,127,128,255,256`; five seeds |
| Stress | Find time/memory knee and failure boundary | `n=32,48,63`; `s=512,1024,2048`; two seeds |

The committed plan encodes the full matrix. Ineligible `(n,s,family)` pairs (for example repeated-prefix construction with insufficient suffix capacity) are excluded with a reason, not silently substituted.

### Support families

- Seeded random unique support: general structural sample.
- Zero-residual-subspace support: boundary case already embedded in the compact subspace.
- Repeated prefix/distinct suffix: structured stress case; only generated when the support capacity condition is met.

### Coefficient families

- Uniform positive real coefficients.
- Random positive real magnitudes normalized to unit norm.
- Random complex coefficients normalized to unit norm.

The independent Algorithm 3 sign profile is varied separately (`all_positive` vs seeded random ±1). This avoids confusing the phase of `c_i` with the paper's separate real-sign metadata.

## 5. Required metrics

### Classical construction

- Wall time (`perf_counter_ns`) and process CPU time (`process_time_ns`).
- Peak RSS normalized to bytes, with OS/API recorded.
- Outcome: completed, failed, timeout or skipped, with elapsed time and reason.
- Compiler version, Git SHA, Python version and workload seed.

### Logical resources

- Paper-accounted Algorithm 3 Toffoli estimate.
- Fully coherent Toffoli estimate including explicit compute/uncompute.
- Explicit emitted Toffoli IR count and gate histogram.
- Symbolic MCX/CMX/PUI macro counts reported separately (not buried in a physical gate count).
- Logical data qubits, marker, clean ancillas and total logical qubits.
- Logical depth only after constructing a valid dependency DAG; never substitute operation count.
- Native gate counts and T-count only after a documented decomposition/transpilation configuration.

### Correctness

- Injective compact labels, all residual bits zero and exact inverse round trip for every run.
- Exact statevector fidelity, maximum amplitude error, outside-support probability, workspace leakage and norm for full state-preparation instances under the configured total-qubit cap.
- A resource-cap skip is `not_run_resource_cap`, not a pass.

### GPU basis-row lane

- GPU model, per-device memory, driver, CUDA runtime, CuPy version.
- Batch size, GPU synchronized wall time, kernel interval and host-device transfers (when instrumented).
- CPU/GPU output equality on the same rows.
- GPU utilisation/temperature/clocks only where reliable tools expose them.

## 6. Statistical protocol

- Each independent support instance has a deterministic seed.
- Use the configured warm-up count; exclude warm-ups from all summaries.
- Repeat timing the same deterministic input for the configured number of measured repetitions.
- Report median, IQR, minimum and maximum for timing distributions.
- Compute 95% bootstrap intervals across independent problem seeds, not by treating repeated timings of one instance as independent samples.
- Record every attempted run, including timeout/failure/skip. Do not drop slow failures from scaling plots without an explicit censored-data annotation.
- Do not compare devices unless their workload keys, code revision, compiler path and measurement boundaries match.

## 7. Hardware lanes and DGX justification

The laptop establishes the correctness/control baseline. A workstation provides an intermediate CPU/GPU point. An institutional DGX node permits a controlled high-throughput accelerator experiment and a larger batch-memory envelope.

**Important current boundary:** the existing CuPy backend vectorizes uint64 computational-basis rows and supports 1–63 data wires. The exact complex statevector verifier is CPU-side and capped; it is not a full GPU statevector simulator. The current code does not distribute one statevector across GPUs and does not pool device memory. Therefore DGX experiments initially target basis-row batch throughput, per-GPU memory behavior and independent workload concurrency. Any later multi-GPU statevector implementation is a separate engineering extension, not an assumed capability.

The classical compiler/control flow remains CPU-side. A GPU speedup claim is permitted only for the GPU-executed row-batch lane, with transfer time separated. Logical Toffoli counts are architecture-independent and must not be described as GPU-accelerated.

## 8. Phase 9.1 exit criteria

- Versioned plan and tier matrix committed.
- Metric catalog distinguishes measured, derived and not-yet-instrumented quantities.
- Run, machine and summary schemas committed.
- Plan validator and dry-run manifest generation pass.
- Dean-facing DGX access brief and reproducibility protocol committed.
- No benchmark results or device-specific claims fabricated.

Phase 9.2 is the local execution phase: device setup, machine manifests, author adapter, raw data capture, analysis and final plots.

### Final validation status correction

The adapter and runner now exist. The local repair smoke is not the full benchmark matrix. The CuPy lane executes emitted SIRIUS reversible operations over basis rows and requires a real CUDA device for GPU acceptance. See `docs/research/FINAL_VALIDATION_REPORT.md` for actual run statuses and current evidence scope.
