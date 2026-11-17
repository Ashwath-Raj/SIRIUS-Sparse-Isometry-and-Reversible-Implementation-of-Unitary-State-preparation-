# Phase 9.2 Benchmark Protocol & Methodology — SIRIUS

## 1. Experimental Objectives

Phase 9.2 executes reproducible, device-local benchmarks across comparison methods, hardware lanes, and problem parameter sweeps defined in the Phase 9.1 benchmark plan (`benchmarking/config/phase9_1_benchmark_plan.json`).

The benchmark protocol quantifies:
1. Classical compilation and circuit synthesis execution time ($t_{wall}, t_{cpu}$).
2. Peak resident memory usage ($RSS_{peak}$).
3. Logical quantum resource scaling (Toffoli count, clean ancillas, emitted IR gate counts, logical depth).
4. Correctness, tableau invariants, and bounded exact statevector fidelity.
5. GPU execution of emitted reversible basis-row operations, with transfer and kernel timings separated when CUDA is available.

---

## 2. Comparison Methods

| Method ID | Role | Entrypoint | Automation Status |
|---|---|---|---|
| `independent_batched_isometry` | Primary Candidate | `sparseprep.run_batched_isometry` | Automated in 9.2 |
| `malvetti_baseline` | Internal Baseline | `sparseprep.run_malvetti_baseline` | Automated in 9.2 |
| `end_to_end_state_preparation` | Full Pipeline | `sparseprep.compile_sparse_state_preparation` | Automated in 9.2 |
| `authors_reference_artifact` | External Differential Reference | Isolated adapter | Artifact build/load and matched smoke available; broad resource agreement not established |

---

## 3. Workload Families & Parameter Sweeps

### 3.1 Support Families
1. `seeded_random`: Rejection-sampled distinct computational basis states. Canonical scaling family.
2. `zero_residual_subspace`: States where all residual bits are zero ($x_{i, \ell \dots n-1} = 0$). Edge family testing zero-residual fast paths.
3. `repeated_prefix`: States sharing an identical subspace prefix but differing in residual suffix. Stress family testing batch capacity.

### 3.2 Tiers
- **Smoke Tier:** Fast execution across $n \in \{4, 8, 12, 16\}$, small $s$, 3 seeds. Total planned jobs: 720. Used for preflight verification and fast CI/local validation.
- **Scaling Tier:** Sweeps $n \in [4, 32]$ and $s \in [2, 128]$. Total planned jobs: 2,700.
- **Stress Tier:** Large-scale tests evaluating memory limits and deep PUI trees. Total planned jobs: 630.

---

## 4. Measurement Methodology & Timing Policies

### 4.1 Timing Sources
- **Wall-clock timing:** High-resolution `time.perf_counter_ns()`.
- **CPU timing:** `time.process_time_ns()`.
- Timers record exclusively the compilation/synthesis phase; input generation, plot rendering, and record serialization are excluded.

### 4.2 Warm-up & Repetition Policy
- **Warm-up iterations:** Executed before measurements to prime JIT caches and OS page faults. Warm-up timing is recorded separately and excluded from measured samples.
- **Measured repetitions:** Configured per tier (e.g. 5 repetitions per instance).

### 4.3 Memory Measurement
- Peak Resident Set Size (RSS) measured via `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` (converted to bytes) or `psutil`.
- Memory measurements reflect the host process peak RSS.

### 4.4 GPU Synchronization & Lane Separation
When evaluating CuPy basis-row batch throughput:
- `cupy.cuda.Stream.null.synchronize()` is called before starting the timer and after completion.
- Host-to-device memory allocation/transfer, GPU kernel execution, and device-to-host transfer times are measured and reported separately.
- GPU results are tagged as `gpu_basis_batch`, never mislabeled as statevector simulation.

---

## 5. Correctness Gates & Failure Handling

Every benchmark attempt must pass correctness gates before metrics are considered valid:
1. **Tableau Invariant:** Forward circuit must map every input support row into the subspace register ($x_{i, \ell \dots n-1} = 0$).
2. **Injectivity:** All mapped subspace labels must be distinct.
3. **Round-Trip Invariant:** $G^\dagger G |x_i\rangle = |x_i\rangle$.
4. **Exact statevector invariants (if total logical qubits fit the cap):** the implementation verifier checks fidelity, maximum amplitude error, support leakage, workspace leakage, output norm and inverse round-trip error with its declared `2e-9` absolute tolerance.

### Allowed Job Statuses
- `completed`: Succeeded and passed all correctness checks.
- `failed`: Algorithmic or verification error.
- `timed_out`: Exceeded configured timeout duration.
- `skipped`: Hardware/dependency unavailable (e.g. CUDA on CPU-only runner).
- `invalid`: Violates problem contract.

All failed and timed-out attempts remain in the raw immutable JSONL records.

---

## 6. Immutable Record Format & Statistical Aggregation

### 6.1 Raw Records (JSONL)
Each execution attempt writes one JSON line validating against `benchmarking/schemas/run-record.schema.json`.
Required fields include:
- `record_version`: "1.1.0" for current runs; historical "1.0.0" records remain readable.
- `run_id`, `plan_id`, `tier`, `algorithm_id`, `status`
- `problem` ($n, s, \ell$, support family, SHA-256 hash of support)
- `seed`, `environment`, `timings`, `logical_resources`, `correctness`, `provenance`

### 6.2 Statistical Aggregation
For completed runs:
- Non-parametric statistics: **Median**, **Minimum**, **Maximum**, **Interquartile Range (IQR)**.
- Independent seeds serve as the statistical sampling unit.
- 95% bootstrap confidence intervals computed over independent seeds when sample size $N \ge 5$.

Records failing schema validation are excluded from numerical buckets and listed in `record_validation_errors`. Their raw lines remain untouched. GPU lane outcomes are reported separately from top-level CPU compilation status. A `completed` CPU construction with an unavailable GPU sub-lane is not a GPU pass.

## Final repair notes (schema 1.1 and summary 2.0)

Support identity is order-sensitive. Each raw record contains the ordered input and a complete input digest; raw files are append-only per unique run ID. A tracked working-tree diff digest accompanies the HEAD SHA when the run is dirty. Historical schema 1.0 records remain readable; absent identity fields are never reconstructed or relabeled as known.

The GPU lane compiles the SIRIUS batched isometry and applies its emitted reversible gate sequence to computational-basis rows. It checks each returned row against the CPU basis-row simulator and reports host-to-device, synchronized kernel, device-to-host, and end-to-end lane time separately. The computation is a basis-row permutation check, never a complex-amplitude statevector simulation. Unsupported gates and unavailable CUDA are explicit lane statuses. A transfer/XOR operation is not an algorithm benchmark.

The aggregator keeps machine, workload, source, configuration, reference artifact and metric units separate. Its replication unit is the independent seed; repeated executions for a seed are collapsed within that seed. Paired differences/ratios are emitted only for matching input, seed, environment, configuration and artifact provenance. Failure, skip, timeout and GPU availability counts remain visible. A one-seed smoke run supports no inferential performance claim.

Resource records keep paper-accounted and coherent Toffoli counts, emitted Toffoli operations, total emitted operations, end-to-end stage Toffolis, ancillas and logical qubits distinct. Gate-list length is not called circuit depth. Depth is null until a scheduling model is implemented.
