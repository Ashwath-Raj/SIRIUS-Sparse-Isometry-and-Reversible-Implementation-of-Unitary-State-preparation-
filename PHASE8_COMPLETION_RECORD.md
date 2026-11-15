# Phase 8 implementation closeout

Phase 8 has two parts:

- **8.1 — Real-sign phase synthesis:** implemented in `phase_synthesis.py`, accepted locally in commit `7caa41a` (subject to the project test log supplied in the conversation).
- **8.2 — End-to-end sparse state preparation:** this package composes the dense compact loader, arbitrary complex coefficient phases, Phase-8.1 sign oracle, inverse Algorithm-3 isometry and marker cleanup.

The build environment reports 13 targeted Phase 8.2 tests passed and 148 project tests passed with two CUDA-specific skips because that environment does not expose CuPy/CUDA. Phase 8.2 is ready for local acceptance; it is not locally accepted until the user runs the scripts, reviews the diff and commits it.

When local acceptance passes, Phase 8 is complete as an algorithmic/logical-circuit implementation. The next and only planned project milestone is Phase 9: benchmarking, transpilation, resource comparison against the authors' artifact and Malvetti baseline, and reproducibility reporting.

**Important scope:** Phase 8 emits an exact logical circuit and verifies it with a full complex statevector oracle. It does not claim hardware-native transpilation, routing, noise simulation or device execution.
