# Phase 3 design decisions

1. The core model and CPU gate simulator use immutable Python data structures and no quantum SDK dependency.
2. Big-endian order is enforced consistently: bitstring position 0 is most significant and corresponds to gate wire 0.
3. PUI is represented as typed symbolic IR only. The simulator rejects PUI until its exact paper-defined reversible expansion is implemented in Phase 5.
4. Resource counts separate emitted primitives and macros. No analytical/decomposed Toffoli total is fabricated.
5. `SparseStateProblem` validates the mathematical support independently of whether the later batching construction supports that boundary case.
6. Structural test families are labelled as candidates; Phase 4/5 trace output must prove which algorithmic branches they exercise.
7. CuPy backend encodes at most 63 qubits in uint64; CPU simulator remains the general-width reference.
