# Request for supervised DGX access

## Project

**Independent implementation and reproducibility study of sparse quantum state preparation with improved Toffoli cost**

## Request

Request a supervised, time-bounded allocation on the institutional DGX system for the benchmark and validation stage (Phase 9.2). The initial request is for a short pilot allocation on one GPU, with additional devices only if the pilot shows a measurable need and the system administrator approves it.

## Research question

Can an independent implementation of the sparse-state isometry construction reproduce the expected logical-resource behavior and maintain correct transformations at larger support sizes, and what throughput benefit is available when batches of computational-basis rows are validated on GPU hardware?

The study is based on Rupprecht and Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), DOI 10.22331/q-2026-09-10-2208.

## Completed groundwork

The project has an independent implementation of the sparse-state model, reversible gate IR, Malvetti baseline, PUI tree emitter, batched isometry, Algorithm 3 sign-marker path, real-sign phase synthesis and end-to-end logical state-preparation composition. The latest local Phase 8.2 acceptance run reported 148 passing tests, with two optional CUDA tests skipped because CuPy/CUDA was not available in that Python environment. This is software test evidence, not a performance result.

Phase 9.1 has now frozen the benchmark design, metric catalog, run schemas, reproducibility rules and dry-run workload manifest. No performance values have been generated or fabricated.

## Why a DGX allocation is relevant

The first GPU experiment uses the existing CuPy backend to transform batches of computational-basis rows with uint64 gate operations. The backend supports 1–63 data wires when the CuPy/CUDA runtime is available. A DGX allocation would let us measure batch-throughput, per-device memory behavior and repeatability at workloads beyond the development laptop, while preserving CPU results as the correctness/control baseline.

The current CuPy backend is not a complex-amplitude statevector simulator, and the current project does not pool VRAM or distribute one statevector across multiple GPUs. The initial request is therefore deliberately limited to a single-GPU pilot; multi-GPU experiments would require a separate validated workload and approval.

## Proposed controlled pilot

1. Confirm the DGX model, GPU type, per-device memory, driver/CUDA versions and scheduler limits.
2. Run a small smoke matrix with fixed seeds and identical workload files.
3. Validate CPU/GPU basis-row outputs before collecting performance numbers.
4. Measure kernel and transfer times separately with CUDA synchronization.
5. Record GPU model, clocks/temperature where available, memory use and software versions.
6. Compare only matched workload keys with the same source revision and inputs.
7. Export sanitized machine manifests and raw JSON result records; no private data or credentials are used.

## Deliverables to the department

- Machine manifest and reproducibility record for the approved node.
- Raw per-run records and validated summary tables.
- CPU-versus-GPU basis-row throughput plots with transfer costs disclosed.
- Scaling plots for compiler runtime, memory and logical Toffoli/ancilla resources.
- A limitations section distinguishing logical resources, classical construction time and GPU simulation throughput.
- A final research report with the official paper/artifact pinned as the external reference.

## Resource and operational safeguards

- Use only the approved account, queue and time allocation.
- Start with one GPU; do not reserve all GPUs or assume device memory is shared.
- Apply time and memory caps from the approved experiment plan.
- Do not run unbounded sweeps; stop on thermal throttling, node contention or resource-limit violations.
- Store only sanitized hardware metadata and generated synthetic support data.
- Do not install or alter system packages; use a project-local environment and administrator-approved CUDA modules.
- No changes to the shared node, drivers, firmware or global environment.

## Requested outcome

Approval for a supervised pilot slot on one DGX GPU, plus access to the node's hardware/software documentation and permitted job-submission procedure. The pilot will determine whether longer allocation or additional GPUs are scientifically justified.
