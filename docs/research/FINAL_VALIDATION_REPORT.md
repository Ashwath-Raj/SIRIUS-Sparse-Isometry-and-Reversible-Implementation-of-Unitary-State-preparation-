# Final SIRIUS Validation Report

## Research objective and paper/artifact

Validate the local SIRIUS implementation of Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum (2026), DOI `10.22331/q-2026-09-10-2208`. The official artifact archive is pinned by MD5 `c58634ba415b4e3fb729648460f32ad7`; its SHA-256 is `4aa9ccdf5a4ae25f389e93dc8c9d7cada71f404f6a64d243038f374da81f6456`. The expected MD5 matches. The authors' package build via frozen `uv` workflow and ABI3 extension import passed.

## Source and environment

- Repository: `/home/ashwathraj/Acadimics/3.Semister3/Projects/Sparse Quantum State Preperation Reduced TOffi COst/SPeed Run`
- Branch at inspection: `cleanup/phase9-2-modernization`
- HEAD used: `e90449ea7c4751ed125aad88fef8d2f142086dc6`
- Working tree: dirty during execution; tracked source diff SHA-256: `7c8cc2506d2c3e17872c09ddc3d7bb6b6ed407172aebcaf8990c7dee2df7ae3b`
- Machine alias: `local-sirius-validation`; OS `Linux #43-Ubuntu SMP PREEMPT_DYNAMIC Fri Oct 23 13:25:25 UTC 2026`; Python `3.14.4`; CPU `AMD Ryzen 5 6600H with Radeon Graphics`; RAM `15491403776` bytes.
- GPU devices: `[]`. Software manifest is in `research/phase9_repair/runs/sirius_repair_validation_20261117/machine_manifest.json`.
- The evidence branch was absent from the local Git object database at the initial snapshot. It was subsequently fetched and audited read-only; its raw records were not copied over, modified, or pooled with this validation run.

## Algorithm implementation map

The sparse input contract is in `candidate_ai/src/sparseprep/model.py`; compact-label and batching construction in `batched_isometry.py`; the Malvetti baseline in `malvetti_baseline.py`; PUI models/tree emission in `pui.py` and `pui_tree.py`; Algorithm 3 and marker logic in `algorithm3.py`; phase synthesis in `phase_synthesis.py`; complete logical state preparation and exact CPU verification in `state_preparation.py`; CPU basis-row simulation in `simulator.py`; and optional CuPy basis-row execution in `backends/cupy_simulator.py`. Detailed status and test mapping is in `FINAL_REQUIREMENT_TRACEABILITY.md`.

## Corrections made

- Support hashing now preserves exact row order, width, framing and duplicate rejection. Versioned workload identity contains ordered support, coefficients, signs, family IDs, seed and generator/configuration metadata.
- Aggregation is stratified by input families, machine/runtime, benchmark/source configuration, artifact digest and metric; seed is the independent replication unit. Paired differences/ratios require matching input, seed, environment, configuration and artifact identity.
- CuPy runner now consumes compiled SIRIUS reversible gates, checks CPU parity, separates transfer/kernel/total timings and emits explicit unavailable/unsupported/failure states.
- Authors adapter validates artifact digest and mapping invariants; invalid underflowed `usize` counts are retained as raw data but are not published as Toffoli costs.
- Exact-statevector runner now calls the implemented API correctly, preserves exceptions, enforces the existing `2e-9` verifier tolerance and handles mathematical fidelity roundoff within [0,1]. Gate-list length is no longer mislabeled as depth. End-to-end stage resource counts are split by scope.
- Raw records use schema 1.1; historical schema 1.0 records remain readable. Summary schema 2.0 records failure states and paired comparisons.

## Tests and packaging

- Full regression suite: `173 passed, 2 skipped, 12 subtests passed in 5.81s`. Exact output is retained in `full_test_suite.log`; two CUDA execution tests were skipped because this host has no CUDA device. CPU-only unsupported-gate and wire-index checks executed.
- Syntax compilation and JSON schema parsing: PASS (`static_validation.log`).
- SIRIUS wheel build: PASS; output retained in `package_build.log`.
- Official artifact build/load: PASS using the artifact's frozen `uv` build workflow; `python -m maturin --version` is absent from the runtime interpreter, but this did not block package build or extension import.

## Matched benchmark smoke and actual results

The structured records below were generated from the same ordered support `["01101010", "10000101", "11001110"]`, identical coefficient/sign arrays and seed, on the same machine. Plan: `sirius-repair-matched-smoke-v1`, `n=8`, `s=3`, seed `17`, one measured repetition. These are smoke observations, not a statistically powered performance comparison.

| Algorithm | Compile wall ms | Compile CPU ms | Paper-accounted Toffoli | Resource scope | Statevector status | Fidelity | GPU lane |
| --- | --- | --- | --- | --- | --- | --- | --- |
| authors_reference_artifact | 39.746616 | 415.410954 | 2 | isometry_only | not_applicable | — | not_requested |
| end_to_end_state_preparation | 0.734271 | 0.730905 | 2 | end_to_end; paper-accounted count is isometry component only | passed | 1.0 | not_requested |
| independent_batched_isometry | 0.48898 | 0.485637 | 2 | isometry_only | not_applicable | — | not_requested |
| malvetti_baseline | 0.259228 | 0.255527 | 3 | isometry_only | not_applicable | — | not_requested |

Matched record count: 4; distinct full input identities: 1; paired summary groups: 36. The one-seed sample does not justify confidence intervals or general performance conclusions. Summary is regenerated from raw records at `matched_smoke_summary.json`.

Separate GPU request: `unavailable`. Device detail: CUDA device probe failed: CUDARuntimeError: cudaErrorNoDevice: no CUDA-capable device is detected. No GPU algorithm execution, GPU parity, throughput, or statevector claim is made.

## Reference validation

Artifact integrity: PASS. Extension build/import: PASS. Mapping fixture invariants: PASS on tested supported inputs. One matched smoke reference workload completed. Reference API returns a mapping and resource upper bound, not a directly executable primitive gate sequence; therefore the report does not claim reference gate-by-gate parity. The official `BatchZeroingData::num_toffolis()` has an observed unsigned underflow path (`changing_size - 2` at size 1); raw wrapped values are marked `suspected_usize_underflow`. Resource agreement is not established across all tested fixtures.

## Audit of the immutable earlier evidence branch

The previously pushed evidence branch was fetched read-only after the initial repository snapshot. Its immutable commit is `3e6ff6142e2449f2877a7345666c324a9030bc2f`. Per-case JSONL audit shows CPU 300/300 correctness passes; however, 100/300 rows have a zero CPU median timer (the wall-time medians range from 0.0148 to 5501.8563 ms), so CPU medians from that run are not reliable. End-to-end statevector checks passed 90/90, but all 90 CPU timer medians were zero. Historical GPU basis-row execution had exact CPU/GPU parity for 90/90 rows with scope `CuPy uint64 basis-row simulation only; not complex statevector or full amplitude preparation`. This is historical evidence from a different checkout and RTX 5060 Ti/CUDA environment; it does not validate the repaired runner in this Linux/no-GPU checkout. The historical authors lane has {'blocked': 150} across 150 rows and closure status `BLOCKED` because Maturin executable discovery blocked extension build. These cases are not pooled with this run.

## All attempts, failures and omissions

Across all preserved iterations in `raw/`, there are 41 attempted records: 40 top-level completed, 1 failed, 0 timed out, 0 skipped, 0 invalid. The aggregator identifies 1 schema-invalid raw record(s) and excludes them from numerical groups; the original lines remain unchanged. The failed record is the exploratory official-reference request for a valid `s=1` case outside the authors kernel's documented implementation domain; its reason remains in the raw JSONL. Earlier partial runs are retained and separated by source diff/configuration in `all_attempts_summary.json`.

The full planned smoke/scaling/stress matrix was **NOT_RUN**. GPU parity was **NOT_RUN** due no device. No quantum hardware was used. Equation (3)'s two-Toffoli inconsistency remains **UNRESOLVED**; Figure 9's caption inversion is supported by surrounding prose, algorithm description and the authors' Figure 9 source. Details are in `PAPER_INTERPRETATION_AND_DISCREPANCIES.md`.

## Reproduction commands

From repository root:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest -o addopts= -q
PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.runners.environment_probe --machine-id local-sirius-validation --output /tmp/sirius-machine.json
for method in independent_batched_isometry malvetti_baseline end_to_end_state_preparation authors_reference_artifact; do
  PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.runners.run_benchmarks --plan research/phase9_repair/runs/sirius_repair_validation_20261117/matched_smoke_plan.json --tier smoke --methods "$method" --output /tmp/sirius-repro-raw --max-jobs 1
done
PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.analysis.aggregate --input /tmp/sirius-repro-raw --output /tmp/sirius-repro-summary.json
```

The separate GPU attempt adds `--enable-gpu` to the candidate command. Reproduction creates a new run ID and raw records; it does not overwrite existing evidence.

## Release-readiness decision

**RESEARCH_VALIDATION_PARTIALLY_READY.** The order-identity, aggregation, reference counter handling, statevector runner and GPU-lane defects have meaningful repairs and tests. A full benchmark campaign, CUDA execution/parity, broad resource agreement and resolution of the paper's Equation (3) discrepancy remain outstanding. This is not release-ready.
