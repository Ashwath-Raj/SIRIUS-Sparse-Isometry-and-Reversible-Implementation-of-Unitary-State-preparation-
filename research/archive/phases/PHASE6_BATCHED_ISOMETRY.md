# Phase 6 — Independent batched-isometry construction

**Implementation status:** small-instance computational-basis constructor implemented and locally validated.

## 1. Objective and notation

Given an ordered support tableau of `s` distinct `n`-bit computational-basis strings, define

- `ell = ceil(log2(s))`;
- the subspace/address register as the first `ell` big-endian wires;
- the residual register as the remaining `n - ell` wires;
- `m` as the largest power of two not exceeding `n - ell` (for nontrivial residual width).

The constructor emits a reversible basis-permutation circuit `G` and an injective map `f` satisfying

\[
G\lvert C_i\rangle=\lvert f(i)\rangle_s\lvert 0\rangle_r.
\]

The sparse-state isometry is `G†`. `f[i]` is kept in the original input-row order.

## 2. Algorithm 1 implementation

The implementation follows the tableau procedure in Rupprecht & Wölk (2026), Section 2 and Appendix C, Algorithm 1.

### Batch invariant

For a batch of size `b`, the row at batch position `j` is maintained as

\[
\lvert k-b+j\rangle_s\lvert e_j\rangle_r,
\]

where `e_j` is a residual-register one-hot vector. The row IDs are stable even when a global PUI changes the bitstrings of rows outside the active batch.

### Adding a row

For the next residual wire `ell + b`, the constructor:

1. Selects a non-batch row with nonzero residual support.
2. Uses that wire directly if it is already one.
3. Otherwise swaps a later residual one into that wire.
4. If no unused residual one exists, applies the distinguishing Toffoli from Algorithm 1. One control is an already-used residual one-hot bit; the second is a bit on which the selected row differs from its matching batch partner. A negative control is used when the selected row has zero at that distinguishing bit.
5. Applies a multi-target controlled-X (`CMX`) to map the selected row to `|k>|e_b>`, updating the entire tableau.

The selected row's pre-activation state and post-activation state are retained in `BatchBuildStep` for auditability.

### Full-batch flush

When `b == m`, the constructor compiles unrestricted PUI on the interval `[k-b, k-1]`. Crucially, it applies that PUI to **every** tableau row, not just the batch rows, because unrestricted PUI can alter extra addresses through its `g` map. The `PUIBatchEvent` records that map and resource counts.

### Final partial batch

When every row outside the current batch already has zero residual, restricted PUI flushes the partial batch. Restricted PUI leaves addresses outside its interval unchanged.

After the restricted PUI, the implementation scans for any remaining one-hot residual row. Each such row is moved to a prefix that is not already occupied with an all-zero residual, using the same multi-target controlled-X plus `ell`-controlled-X repair pattern. The `correction_row_ids` and `correction_labels` identify those repairs.

**Implementation adaptation:** the pseudocode in the paper describes a single special collision at the final batch address/one-hot position. Under the explicit big-endian wire/row ordering used in this independent implementation, a valid small support can instead expose a one-hot collision at another address in the final interval (the regression case in `test_final_restricted_pui_collision_is_repaired_even_at_nonterminal_label`). The implementation generalizes the same fresh-prefix/controlled-X repair to any one-hot residual row. This is disclosed rather than silently claiming a byte-for-byte reproduction of the pseudocode. If more than one repair is ever needed, the single-collision Eq. (3) allowance is not claimed.

## 3. Circuit representation and verification

The emitted `forward_gates` use the Phase 3–5 reversible gate IR:

- `SWAP` for residual-wire relocation;
- `Toffoli` or `NegativeControlToffoli` for fallback activation;
- `CMX` for multi-target controlled-X tableau moves;
- Phase 5 shared-prefix PUI tree gates for unrestricted/restricted flushes;
- symbolic `MCX` for final collision clearing.

`inverse_gates` is the exact reverse/inverse sequence. `BatchedIsometryResult.verify()` checks:

- `f` is injective and every final residual register is zero;
- all support rows follow the emitted `G` action;
- PUI ancillas return to zero on every support row;
- `G†` recovers every original row and leaves ancillas clean.

The proof obligation is for the supplied support basis states. The gate sequence itself is a composition of reversible permutations and therefore is invertible on the full extended computational basis.

## 4. Resource accounting

The report keeps two Toffoli figures separate:

- **Paper-accounted:** PUI selector-AND computation, batch fallback Toffolis, and the final MCX ladder under the paper's measurement-based AND-adjoint accounting.
- **Fully coherent:** PUI compute **and explicit unitary uncompute**, plus fallback and correction MCX coherent-ladder Toffolis.

`forward_gates` retains the final collision MCX as a symbolic gate. Its ladder costs are reported as estimates; this Phase 6 module does not yet physically expand that final MCX into its Toffoli ladder. CMX and SWAP are also retained as IR operations rather than decomposed into a physical native gate set.

The allocated clean-ancilla pool has `ell - 1` wires. `max_clean_ancillas_used` reports the maximum actually used by a PUI tree or final MCX ladder. PUI tree operations reuse the same clean pool sequentially.

Equation (1) is reported only in its useful parameter range (`2 <= m <= 2**ell`) and when the single-collision correction allowance applies. The `m=1` and `m > 2**ell` boundary cases return no Eq. (1) estimate rather than displaying a misleading negative/out-of-domain value. Equation (3)'s extra-correction bound is reported only when at most one final collision repair is required.

Dense state preparation and Algorithm 3 sign/marker correction are excluded from Phase 6; they are separate phases.

## 5. Validation

The Phase 6 test module checks:

- the seven-row Figure 4 tableau from the paper;
- direct, SWAP and distinguishing-Toffoli batch-building paths;
- unrestricted PUI extra-address bookkeeping;
- final restricted-PUI collision cleanup;
- forward/inverse action and clean ancillas;
- separate paper-accounted and coherent Toffoli totals;
- `s=1`, zero-residual-width and `m=1` boundaries;
- seeded randomized small tableaus.

A separate deterministic fuzz campaign exercised 3,600 random supports (`n=2..8`, `s=1..min(12,2**n)`, 50 supports per `(n,s)`). All 3,600 constructed and verified. It exercised direct, SWAP and Toffoli fallback paths (12,227 / 4,169 / 465 observed steps), used at most one final collision repair per case, and had no Eq. (1) bound violations in the cases where that expression was reported. Run it with `bash scripts/run_phase6_fuzz.sh` after installing the addendum.

The container used to prepare this ZIP had no accessible CUDA device, so the two inherited CUDA tests are expected to be skipped here. They should execute on the user's RTX 3050 in the integrated project environment. The tableau compiler itself is CPU-side classical circuit construction; it does not claim a GPU speedup for the Algorithm 1 control flow.

**Reference-comparison limitation:** the source artifact was integrity-checked and its Rust/Python tests were exercised in Phase 2, but its actual Phase 6 implementation source archive was not available inside this packaging environment for a line-by-line comparison. This implementation is grounded in the paper's Algorithm 1 / Algorithm 2 and Figure 4; a direct differential run against the authors' `IsometryToSubspaceViaBatching` remains a later validation task if the local source bundle is made available to the developer environment.

## 6. Primary sources

- Felix Rupprecht and Junhyung Lee, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), especially Section 2, Section 3, Appendix A and Appendix C, Algorithm 1.
  - https://quantum-journal.org/papers/q-2026-09-10-2208/
  - https://doi.org/10.22331/q-2026-09-10-2208
- Official authors' code artifact: https://zenodo.org/records/18234600
