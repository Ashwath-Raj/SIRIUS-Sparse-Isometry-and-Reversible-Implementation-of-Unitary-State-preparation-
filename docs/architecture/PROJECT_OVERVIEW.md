# Research project overview

## Title

**Independent implementation and reproducibility study of sparse quantum state preparation with improved Toffoli cost**

## Research objective

Independently implement and validate the sparse-state preparation construction described by Felix Rupprecht and Sabine Wölk, then quantify its logical resource scaling and classical construction behavior against a Malvetti-style isometry baseline and, after adapter integration, the authors' published reference artifact.

The target problem is an `s`-sparse state on `n` qubits,

\[
|\psi\rangle=\sum_{i=0}^{s-1} a_i c_i |x_i\rangle,
\]

where the basis support strings `x_i` are unique, `c_i` are normalized complex coefficients, and optional `a_i \in \{+1,-1\}` represent independent real-sign metadata.

## What has been implemented

- Immutable sparse-state problem model and deterministic support generators.
- Primitive reversible gate IR, basis-state simulator and optional CuPy `uint64` batch simulator.
- Malvetti isometry baseline.
- Optimized restricted/unrestricted PUI tree emitter.
- Independent batched-isometry constructor with forward/inverse verification.
- Algorithm 3 sign-marker model and integrated real-sign fixing path.
- Exact logical real-sign phase synthesis.
- End-to-end logical sparse-state preparation with dense compact-register amplitudes, complex coefficient phases, inverse isometry and marker cleanup.
- End-to-end exact CPU statevector verification for instances within the configured cap.

## Validation status at Phase 9.1 planning

The latest local Phase 8.2 run reported 148 passed and 2 CUDA tests skipped because CuPy/CUDA was unavailable in that Python environment. Phase 8.2 was committed locally as `99470d1`; Phase 8.1 was amended to `7caa41a`. Earlier Phase 6 logs reported successful CuPy execution on the development RTX 3050. These are local development/test observations, not benchmark results and not device performance claims.

## What is not yet claimed

- No cross-device performance results exist in Phase 9.1.
- The authors' reference artifact has not yet been integrated into a common automated benchmark adapter.
- There is no full GPU complex-statevector simulator in the current project.
- The CuPy backend does not distribute one statevector across multiple GPUs or pool VRAM.
- The logical IR is not yet a backend-native transpiled circuit; physical gate depth, T-count and device execution require an explicit backend/decomposition choice.

## Project completion boundary

Phase 9.1 completes the project architecture, evidence package, benchmark contract and institutional access case. Phase 9.2 is local, device-specific execution and result collection; its device manifests, raw measurements and temporary environment files are intentionally uncommitted.
