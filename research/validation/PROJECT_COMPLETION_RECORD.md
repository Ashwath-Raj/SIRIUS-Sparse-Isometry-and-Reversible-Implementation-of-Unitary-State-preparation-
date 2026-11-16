# Project completion record — Phase 9.1

## Completed technical milestones

1. Research workspace and official reference artifact integrity record.
2. Independent sparse-state model and reversible gate IR.
3. Malvetti isometry baseline.
4. PUI plan and optimized tree emitter.
5. Independent batched isometry and resource accounting.
6. Algorithm 3 sign/marker reference and integration.
7. Real-sign diagonal phase synthesis.
8. End-to-end logical sparse-state preparation and exact CPU statevector verification for bounded instances.
9. Benchmark system design, cross-device experiment plan, schemas, dry-run manifest validator, reproducibility contract and DGX access brief.

## Current validation evidence

The operator's local Phase 8.2 run reported:

- Phase 8.2 targeted tests: 13 passed.
- Full integrated test suite: 148 passed, 2 skipped.
- The two skips were optional CuPy/CUDA tests unavailable in that Python environment.
- Phase 8.2 local commit: `99470d1`.
- Phase 8.1 local commit: `7caa41a`.

Phase 9.1 package validation completed in the build workspace:

- Phase 9.1 design tests: 4 passed.
- Full-tier dry-run plan: 4,050 planned workload jobs; zero capacity exclusions.
- Smoke-tier dry-run: 720 planned workload jobs.
- The validator did not import or execute benchmark algorithms.
- Integrated Phase 8 regression: 148 passed, 2 skipped (optional CuPy/CUDA tests unavailable in the build environment).

These are design/validation outcomes, not benchmark measurements. The user's target-machine validation and Phase 9.1 Git commit remain the acceptance steps.

## Remaining work

Phase 9.2 only:

- device-specific environment probes and local setup;
- install/verify CuPy and CUDA independently on each machine;
- pin and integrate the authors' reference artifact adapter;
- execute the same workload matrix on laptop/workstation/DGX where available;
- collect raw timings/resources/memory/accuracy records;
- generate comparison plots, scaling analysis and final report.

## Release boundary

Phase 9.1 is intended to be committed. Phase 9.2 machine manifests, raw runs, environment-specific configuration and plots are local outputs and should remain uncommitted unless a separate research-data release is intentionally approved. No `git push` is part of this workflow.
