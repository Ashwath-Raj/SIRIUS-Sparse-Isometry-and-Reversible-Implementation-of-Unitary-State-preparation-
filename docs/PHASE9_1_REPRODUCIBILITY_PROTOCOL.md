# Phase 9.1 — Reproducibility and data-integrity protocol

## 1. Immutable run identity

A run is identified by a deterministic key containing plan ID, tier, algorithm ID, `n`, `s`, support family, coefficient family, sign profile and seed. A UUID may be used as the storage ID, but must not replace the deterministic key.

Every run record includes:

- Git commit SHA and whether the working tree was dirty;
- paper DOI and authors' artifact MD5;
- generator/runner version;
- input support SHA-256 and all input-generation parameters;
- sanitized machine identity and software versions;
- UTC start/end timestamps and outcome status.

## 2. Same-input comparison rule

Comparative methods must consume the same ordered support and, where applicable, the same coefficient and sign arrays. Generate inputs once, serialize them or hash them, then pass those exact inputs to each implementation adapter. Do not independently regenerate a nominally equivalent random support inside each comparator.

The support order is part of the input because the project preserves support row IDs and compact-label mappings. Save the ordered support or an immutable input file in local Phase 9.2 run storage; a hash alone is not enough to reproduce a run if the generator version changes.

## 3. Timing boundaries

Separate the following intervals:

1. Problem generation (reported separately, excluded from compiler timing).
2. Compiler invocation (wall + CPU time).
3. Correctness verification (reported separately from construction).
4. Host-to-device transfer.
5. GPU kernel execution (synchronize before and after timing).
6. Device-to-host transfer.
7. Summary/plot generation (excluded from all algorithm timing).

Record cold-start and warm-up behavior separately. Do not silently remove compilation/import overhead: report both first-call and steady-state timing if they differ materially.

## 4. Machine manifest and privacy

Record CPU model, core counts, RAM, OS/kernel, Python implementation/version, NumPy/CuPy, NVIDIA driver, CUDA runtime/toolkit and each GPU model/memory. Use aliases rather than personal account names, local home directories, serial numbers or private hostnames. Per-GPU memory is reported independently; no unified-memory assumption is allowed.

## 5. Failure and missingness

Allowed statuses: `completed`, `failed`, `timed_out`, `skipped`, `invalid`. Every non-completed result includes a reason. Null values must have an explicit not-measured or not-applicable reason. A statevector validation skipped due to the qubit/memory cap is not a correctness pass.

Timeouts and memory failures remain in the raw dataset. Report them as censored/failed observations and show the configured limits. Never substitute a smaller problem after a timeout without creating a new workload key.

## 6. Aggregation and comparison

- Raw per-run JSON records are immutable.
- Summaries are generated from validated records and include source-record SHA-256 values.
- Report median and IQR for run-time/resource distributions.
- For stochastic support families, report the number of independent seeds and a 95% bootstrap interval over those seeds.
- Compare only matching workload keys and record when a backend or metric is unavailable.

## 7. Artifact integrity

Before invoking the authors' reference artifact, verify its expected MD5 `c58634ba415b4e3fb729648460f32ad7` and record the actual local digest. The artifact is a pinned external comparator, not an editable dependency of this project. Do not modify its lockfile during Phase 9.2.
