# Benchmarking system

## What exists in Phase 9.1

- A versioned cross-device benchmark plan at `config/phase9_1_benchmark_plan.json`.
- Metric definitions and availability at `metric_catalog.json`.
- JSON Schemas for machine manifests, raw run records and aggregated summaries.
- Templates with explicit placeholder values, never represented as measurements.
- A standard-library validator and dry-run work-manifest generator: `scripts/phase9_1_validate.py`.

Phase 9.1 does **not** execute benchmark workloads, capture hardware telemetry, invoke CUDA, or produce result values. Those actions are reserved for Phase 9.2 and remain local/uncommitted.

## Three measurement lanes

1. **Classical construction:** CPU time, wall time and peak RSS for `run_malvetti_baseline`, `run_batched_isometry`, `run_algorithm3` and `compile_sparse_state_preparation`. Construction timing excludes generator and plot time.
2. **Logical resources:** paper-accounted and coherent Toffoli estimates, explicitly emitted IR gate histogram, logical qubits, clean ancillas and symbolic macro counts. A Toffoli estimate must never be mislabeled as a physically decomposed native-gate count.
3. **Execution/validation:** mandatory basis-tableau invariants; exact statevector fidelity and workspace leakage only when the complete logical circuit fits the configured cap; optional CuPy execution of the compiled reversible basis-row workload when CUDA is available.

## Important current backend boundary

The CuPy backend is a `uint64` **batch of computational-basis rows** simulator and supports 1–63 wires. The runner feeds it actual emitted reversible SIRIUS gates and compares outputs against the CPU simulator. It is not a complex-amplitude statevector simulator. Exact complex-statevector validation is CPU-side and capped. The circuit construction remains CPU-side. If CUDA is unavailable, the GPU lane records `unavailable`; it is not a pass or a measurement.

## Comparators

- `independent_batched_isometry`: project implementation, primary candidate.
- `malvetti_baseline`: internal isometry baseline, run on identical support rows.
- `authors_reference_artifact`: official Rust adapter, with artifact digest and row-mapping invariant checks. The adapter's mapping and resource outputs have distinct comparison limits; resource equality is not inferred from a different pivot choice or algorithm mode.

## Generate a dry-run manifest

From the repository root:

```bash
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json
python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json --tier smoke --emit-manifest /tmp/sparseprep-smoke-plan.json
```

This only validates and enumerates planned jobs. It does not import or call any benchmark algorithm.

## Phase 9.2 device run contract

1. Start from a clean, recorded Git revision (or an explicit dirty-tree marker for private experiments).
2. Capture a sanitized machine manifest and exact Python/CUDA/CuPy/software versions.
3. Verify the authors' artifact checksum before the reference comparator is used.
4. Generate the same support/coefficient/sign inputs from the recorded seed.
5. Run correctness gates before collecting publishable performance numbers.
6. Separate cold-start, warm-up and measured repetitions.
7. Synchronize CUDA around timed regions and separate transfers from kernel time.
8. Emit one immutable raw record per attempted workload, including failures/timeouts/skips.
9. Validate records against the schema before aggregation.

See `docs/benchmarking/PHASE9_1_BENCHMARK_SYSTEM_DESIGN.md` and `docs/benchmarking/PHASE9_1_REPRODUCIBILITY_PROTOCOL.md`.

Final schema additions and current scope are documented in `docs/benchmarking/PHASE9_2_BENCHMARK_PROTOCOL.md`. A full planned scaling/stress campaign has not been run; see `docs/research/FINAL_VALIDATION_REPORT.md` for current local evidence and blockers.
