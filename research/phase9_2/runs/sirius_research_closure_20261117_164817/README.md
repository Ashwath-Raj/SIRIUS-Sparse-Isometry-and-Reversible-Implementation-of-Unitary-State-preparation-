# SIRIUS Phase 9.2 — Benchmark Evidence

**Run:** `sirius_research_closure_20261117_164817`  
**Repository:** `Ashwath-Raj/SIRIUS-Sparse-Isometry-and-Reversible-Implementation-of-Unitary-State-preparation-`  
**Local source:** `benchmarking/local-runs/sirius_research_closure_20261117_164817`

## Included evidence

- The closure report (see `raw/`).
- `closure_status.json` and all whitelisted raw JSON, JSONL, CSV, log, and report files found in the selected run directory.
- A SHA-256 inventory in `PUBLISH_MANIFEST.json`.
- The original result ZIP and its checksum (when present) are included.

## Execution facts from the captured console transcript

- The runner reached dispatch positions **300/300 CPU**, **90/90 end-to-end statevector**, and **90/90 GPU basis-row**.
- Full Python test suite: **PASS**.
- GPU environment detection: **PASS**; CuPy parity tests: **PASS**.
- Authors' reference differential: **BLOCKED** because the Maturin executable could not be located. Therefore no authors-extension differential result is claimed here.
- Closure handoff reported **Release ready: False** and **Local release: NOT_CREATED**. This evidence publication is not a release-validation claim.

The dispatch counts above describe work items reached by the runner. Use the raw result records and `closure_status.json` to determine per-case success, failures, skips, and metric values; do not infer those from progress counters alone.

## Report status

This directory preserves the run evidence for a subsequent paper-quality report. It is not itself the final scientific report. The report should be written only after analysing the raw records, seed-level summaries, CPU/GPU CSVs, E2E fidelity/leakage results, and all closure gates.

## Important interpretation limits

- The GPU implementation measured here is a computational-basis row simulator, not a full GPU statevector simulator.
- Logical depth/resource figures must retain the definitions used by the benchmark implementation; do not present logical IR depth as hardware-transpiled depth.
- The authors' Rust extension comparison did not run in this execution.
