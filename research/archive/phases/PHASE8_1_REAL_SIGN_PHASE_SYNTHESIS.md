# Phase 8.1 technical note — compiling Algorithm-3 real signs

## 1. Interface contract

Input is the `Algorithm3Result` returned by `run_algorithm3`. Phase 8.1 consumes only:

- `ell`: compact-register width;
- `compact_labels`: unique compact basis labels in original support-row order;
- `signs`: aligned exact integer values in `{+1,-1}`.

It rejects mismatched lengths, duplicate labels, non-integer signs (including booleans), negative/out-of-range labels and invalid widths. It does not mutate the Phase-7 result.

## 2. Unitary to synthesize

For each compact label `f(i)` with sign `-1`, apply one diagonal basis-state phase flip. Distinct labels are orthogonal, so these phase flips commute. Their product is

\[
P=I-2\sum_{i:a_i=-1}|f(i)\rangle\langle f(i)|.
\]

For every support row, `P|f(i)> = a_i|f(i)>`. Unoccupied compact labels retain phase `+1`.

## 3. Reversible lowering

Let the selected compact label be `b_0...b_(ell-1)`, using big-endian logical wires. Select the final wire as the MCZ target and the preceding `ell-1` wires as controls.

1. Apply `X` to every zero-valued control, and to the target when its selected value is zero.
2. Apply `H` to the target.
3. Apply an all-positive-control MCX.
4. Apply `H` to the target.
5. Undo target and control normalization in reverse order.

The target conjugation makes the phase conditional on the selected target value. The control normalization makes it conditional on the selected prefix. Thus exactly one computational-basis label receives phase `-1`.

MCX is lowered with a clean v-chain. For `k` controls:

- `k=1`: CX;
- `k=2`: Toffoli;
- `k>=3`: compute the successive prefix conjunctions into `k-2` clean ancillas, flip the target with the final Toffoli, and reverse the conjunction chain.

For an `ell`-bit phase flip, `k=ell-1`; hence the maximum reusable clean ancilla count is `max(0, ell-3)`. Each phase-flip block returns all ancillas to zero before the next block begins.

## 4. Simulator and invariants

The reference simulator uses complex statevectors with big-endian indexing: logical wire 0 is the most-significant basis-index bit. The `PhaseOracleCircuit.apply` adapter appends zeroed work wires, applies the operation sequence, verifies zero probability in every nonzero work-ancilla sector, and returns the compact-register vector.

`PhaseOracleCircuit.verify` checks every computational-basis input and compares its output against the independent diagonal specification. Tests additionally compare normalized complex superpositions against a separately written direct sign multiplier. This detects incorrect phases that a probability-only test would miss.

## 5. Resource interpretation

Counts are emitted reference-circuit operations, not the paper's optimized Algorithm-3 PUI-inline resource count. The sign oracle is intentionally separated so Phase 9 can compare:

1. Algorithm-3 PUI/batch resources from Phase 7;
2. this explicit phase-oracle overhead;
3. Phase-8.2 dense-loader resources.

No paper asymptotic bound is claimed for this explicit reference decomposition.

## 6. Phase boundary

Phase 8.1 completes the exact real-sign diagonal unitary. It does not prepare probability magnitudes, arbitrary complex coefficient phases, or the full sparse state from `|0...0>`. Phase 8.2 must prepare the compact-label vector, apply this oracle, execute the inverse Phase-7 isometry and marker cleanup, and verify the resulting full complex sparse statevector.
