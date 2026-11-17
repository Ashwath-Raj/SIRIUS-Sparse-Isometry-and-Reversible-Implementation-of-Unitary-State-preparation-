# Phase 8.2 — End-to-end sparse state preparation

This is the final implementation handoff for Phase 8. It overlays the current Phase 7.2 + Phase 8.1 project; it does not replace earlier modules.

## Delivered

- Exact recursive dense compact-register amplitude preparation for arbitrary normalized complex coefficients.
- Correct association of coefficient entries with Algorithm-3 `compact_labels`, including non-identity label order.
- Complex coefficient argument synthesis using basis-selective phase blocks.
- Composition with the Phase-8.1 independent `+1/-1` sign oracle.
- Lowering of the Phase-7 inverse basis map, followed by marker cleanup.
- Separate clean ancilla pools for Algorithm-3 and Phase-8 state preparation.
- Full complex statevector verification, support-leakage checks, workspace-cleanliness checks and full inverse round trip.
- Per-stage gate/resource accounting with Algorithm-3 paper and coherent Toffoli metrics kept separate.

## Install

Extract the ZIP into the existing project root. It is an overlay and includes only the Phase 8.2 additions and the two existing source files that require updates.

## Validate

```bash
bash scripts/run_phase8_2_tests.sh
bash scripts/run_phase8_2_validation.sh
```

The targeted suite verifies dense loading and all end-to-end stages. The full validation script executes the entire project test suite, including Phase 3–8 regression and CUDA tests when the local environment supports them.

## API

```python
from sparseprep import SparseStateProblem, prepare_sparse_state

problem = SparseStateProblem(
    4,
    ("0001", "0110", "1011"),
    coefficients=(1 / 3**0.5, 1j / 3**0.5, -1 / 3**0.5),
    signs=(1, -1, 1),
)
circuit, metrics = prepare_sparse_state(problem)
```

`metrics` includes fidelity, maximum complex-amplitude error, outside-support probability, workspace leakage, output norm and inverse round-trip error. `circuit.resources` reports dense-loader, sign-oracle, inverse-isometry and marker-cleanup gate counts.

## Scope boundary

The circuit is an exact logical reference circuit. It is not yet transpiled to a hardware-native gate basis or routed/scheduled on a backend. That is Phase 9 work, along with performance and paper comparisons. Phase 8 is the end-to-end algorithmic implementation milestone, not the device-benchmark milestone.

**Never push. Commit locally only after the user's local acceptance run.**
