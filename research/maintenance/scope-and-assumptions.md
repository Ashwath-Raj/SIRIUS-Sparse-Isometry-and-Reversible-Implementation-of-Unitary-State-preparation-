# Scope and assumptions

## Phase 1 scope

- Verify the supplied sources and record provenance.
- Initialize an isolated workspace.
- Implement portable environment/hardware detection tooling.
- Provide an integrity-checked fetch helper for the official Zenodo artifact.
- Run only lightweight Phase 1 tests.

No sparse-isometry, PUI, Algorithm 1 or Algorithm 3 implementation is included in Phase 1.

## Hardware roles from the user's roadmap

1. Acer Nitro V, NVIDIA RTX 3050 Laptop GPU, 6 GB VRAM, 16 GB system RAM: primary local CUDA development/validation target.
2. CPU: correctness oracle and portable fallback.
3. Kaggle: online GPU execution, accelerator must be detected at runtime.
4. RTX 5060 Ti workstation with 64 GB RAM: optional short comparison runs.
5. SRM AP DGX-1: optional institutional resource; the facility description supplied by the user states eight Tesla V100 GPUs in a hybrid cube-mesh NVLink topology and up to 300 GB/s aggregate bidirectional bandwidth per GPU. Treat this as a facility-stated peak specification, not measured application throughput.

The agent runtime used to prepare this package is not the user's laptop. Hardware results from this agent runtime must not be substituted for the RTX 3050 probe.

## Scientific conventions to carry forward

- Big-endian bit ordering: leftmost bit is most significant; for three address bits, `|100>` represents integer 4.
- `G |C_i> = |f(i)>_subspace |0>_residual` is the to-subspace direction found by the classical circuit-construction algorithm.
- Sparse-state preparation uses the inverse `G†`.
- Keep emitted gate counts, analytical upper bounds, classical preprocessing time, and hardware runtime separate.
- Never count CX/CMX as Toffoli gates.
