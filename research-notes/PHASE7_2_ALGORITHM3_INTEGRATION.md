# Phase 7.2 — Algorithm 3 integration

## Scope

This phase implements the paper's Algorithm 3 for real-valued sparse states with input signs in {+1,-1}. It integrates the Phase 7.1 sign ledger with the Phase 5 restricted-PUI tree emitter and the Phase 6 reversible gate IR.

Primary API:

```python
from sparseprep import SparseStateProblem, run_algorithm3

problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
result = run_algorithm3(problem, signs=(1, -1, 1, -1))
result.verify()
```

## Algorithm 3 flow implemented

1. Append the marker wire D, initialized to 1 for every support row.
2. Build batches using the same direct activation, SWAP, and distinguishing-Toffoli cases as the batched isometry.
3. Flush every full or final batch with a **restricted** PUI. Its target map includes the batch row's one-hot residual wire and the marker wire. Apply each batch row's sign in the phase ledger.
4. If no unbatched row has residual support, select an unbatched row with marker 1. For every still-marked batch row, emit the counter-effect CX from its one-hot residual wire to the next residual wire. Then emit the marker-controlled CX (marker as control, next residual wire as target), followed by the batch CMX.
5. Continue until k=s. The result must have zero residual registers, zero markers, an injective compact-label map, and exact requested sign metadata.

The counter-effect CX direction is important: the one-hot residual wire controls the **next residual wire**. It does not target the compact-prefix register. The marker controls the same next residual wire in the following CX. This matches Algorithm 3 on page 21 of Rupprecht & Wölk (2026).

## Circuit and phase representation

- `forward_gates` is a reversible **basis-permutation** IR over n data wires, one marker wire, and the clean PUI ancilla pool.
- `inverse_gates` is the exact reversed basis-permutation circuit.
- `phases[i]` records the real sign multiplier for input row i. The simulator's classical basis-state IR does not simulate quantum phase; the independent phase ledger checks the sign action separately. **The sign ledger is not itself a synthesized Z/controlled-Z gate sequence.**
- The final state-preparation isometry is the inverse circuit G†, consistent with the paper's convention G|C_i> = a_i|f(i)>|0>.

## Resource accounting

- `paper_accounted_toffolis`: paper-accounted PUI selector-AND Toffolis plus batch fallback Toffolis.
- `coherent_toffolis`: explicit coherent PUI compute/uncompute Toffolis plus batch fallback Toffolis; this is checked against the emitted gate IR.
- CX, CMX, SWAP, X, marker, and sign-ledger operations are not mislabeled as Toffolis.
- `max_pui_ancillas` reports the maximum PUI-tree clean ancilla pool actually touched.

## Boundaries

- This implements Algorithm 3's tableau construction, restricted-PUI scheduling, marker/counter-effect control flow, reversible basis action, and exact real-sign ledger for ±1 inputs.
- The emitted gate sequence covers the basis permutation and marker ancilla. The sign ledger is not yet lowered to physical Z/controlled-Z operations; that is a distinct quantum-phase synthesis task.
- It does **not** implement the dense-state preparation stage, arbitrary complex phase synthesis, or the complete end-to-end sparse-state preparation Bloq.
- The sign ledger is separate from the basis permutation simulator by design; a classical basis simulator cannot represent relative quantum phase.

## Validation

- 10 Phase 7.2 tests, including a seeded randomized sweep of at least 300 cases.
- Phase 7.1 sign/marker reference tests run alongside Phase 7.2.
- Forward and inverse circuits are checked on every input support row.
- Every result asserts zero residual bits, zero marker bits, injective compact labels, exact signs, and consistency between coherent Toffoli count and emitted gate IR.
