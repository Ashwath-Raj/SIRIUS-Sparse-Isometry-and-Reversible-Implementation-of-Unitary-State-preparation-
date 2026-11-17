# Phase 9.1 acceptance checklist

- [x] Project README consolidated to describe Phases 1–9.1 and remaining Phase 9.2 work.
- [x] Architecture map documents the implemented candidate modules and execution boundaries.
- [x] Benchmark design separates classical construction, logical resources, correctness and GPU basis-row throughput.
- [x] Workload plan defines smoke, scaling and stress tiers with deterministic seeds and per-cell time limits.
- [x] Isometry-only comparison cases are separated from full state-preparation coefficient/sign cases.
- [x] Internal Malvetti baseline is named as an automated comparator.
- [x] Authors' reference artifact is documented as an external comparator requiring a version-pinned adapter in Phase 9.2.
- [x] Metric catalog distinguishes current metrics from items requiring future instrumentation.
- [x] Run-record, machine-manifest and summary JSON Schemas are included.
- [x] Placeholder templates are explicitly labelled and contain no claimed measurements.
- [x] Reproducibility protocol covers seeds, exact input identity, timing boundaries, statistics, timeouts and provenance.
- [x] DGX request brief includes a single-GPU pilot, limitations and operational safeguards.
- [x] Phase 9.2 local outputs are ignored by `benchmarking/.gitignore`.
- [x] Phase 9.1 validator passes and emits a dry-run workload manifest.
- [x] Four design tests pass.
- [x] Full Phase 8 regression was re-run in the packaging workspace: 148 passed, 2 skipped (CuPy/CUDA unavailable in that environment).
- [x] No benchmark workload was executed and no performance values were fabricated.

## Exit decision

Phase 9.1 is ready to commit when the user's local validation passes and the Git working tree contains only the intended Phase 9.1 files. Phase 9.2 is deliberately not included as a committed benchmark implementation or results release.
