# Phase 7.1 — Algorithm 3 signed-tableau reference model

**Status:** implemented and locally tested in the packaging environment. This is a deliberately bounded first half of Phase 7, not a claim that the complete Algorithm 3 is already implemented.

## 1. Scope boundary

Phase 7 is split into two independent handoffs:

- **Phase 7.1 (this package):** signed-tableau data model, marker-qubit state, restricted-PUI visit/sign ledger, reversible basis-permutation reference primitives, trace events, and exact small-instance postcondition checks.
- **Phase 7.2 (not included):** derive the affected-row sets from the actual restricted PUI interval/tree; implement Algorithm 3's complete batch-control flow including the residual swap/Toffoli branches and counter-CX corrections; emit the gate-level circuit using the existing Phase 5/6 IR; integrate inverse/resource accounting and end-to-end tests.

No files from Phase 3–6 are overwritten. The new package is additive.

## 2. Paper contract

Rupprecht & Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), Algorithm 3 on PDF page 21, states the signed basis action

\[
G\lvert C_i\rangle = a_i\lvert f(i)\rangle_s\lvert 0\rangle_r,
\qquad a_i\in\{+1,-1\}.
\]

Algorithm 3 extends the tableau by a marker column initialized to `1`, uses restricted PUI, and during a visit performs the per-row sign fix while setting the marker to `0`. The prose on PDF page 13 explains that the marker prevents states already in the subspace from being silently skipped. The pseudocode on page 21 also contains the counter-CX corrections for previously batched rows before the next marker-controlled CX and CMX.

Primary source: https://quantum-journal.org/papers/q-2026-09-10-2208/ (PDF page 21; Section 4 discussion on PDF page 13). Official artifact: https://zenodo.org/records/18234600.

## 3. Data model

`PhaseFixingTableau` keeps each row's stable `row_id`, original and current `n`-bit data words, input sign `a_i`, accumulated global phase, marker bit, and restricted-PUI visit count. The marker is kept outside the `n`-bit string because it is an extra `(n+1)`-th tableau column, not an original data qubit.

The module uses the project's big-endian convention: character index zero is the leftmost/most-significant wire.

## 4. Implemented operations

The reference model supports reversible basis permutations over the full current tableau: X, CX, SWAP, Toffoli, CMX, and CX controlled by the extra marker. It also has a guarded `apply_counter_effect_cx` helper matching Algorithm 3's correction precondition: the selected earlier batch row must still have marker `1` and value `1` on the chosen residual control wire. The CX is then applied globally to every tableau row whose control bit is `1`, as a circuit gate must be. Such data operations do not change input signs, accumulated global phases, or marker values.

`record_restricted_pui_visit` records a restricted-PUI event over an explicitly enumerated set of affected rows. For each affected row, it:

1. validates that the marker is still `1` and that the row has not already been visited;
2. installs the caller-supplied post-PUI data word;
3. multiplies the row's global phase by its prescribed `a_i` sign;
4. changes the marker from `1` to `0` and records exactly one visit.

The caller must provide `affected_row_ids` separately from the `updates` map. The sets must match exactly. This is intentional: Phase 7.2 must compute every row affected by a PUI interval, including non-batch rows sharing an address, instead of assuming only active batch rows are touched. Updates are transactional: invalid or colliding post-states do not partially mutate the tableau.

## 5. Verification

`verify_completed` checks, row by row:

- each row was visited exactly once;
- every marker is zero;
- the final bitstring equals the supplied injective output mapping;
- the accumulated global phase equals the input sign `a_i`.

This verifies the signed basis-action contract at the reference-model level. It does **not** prove that the restricted-PUI circuit or complete Algorithm 3 has been synthesized; that is Phase 7.2's obligation.

## 6. Deliberate exclusions

- No arbitrary complex phase is accepted. This path is for real-state signs only.
- No quantum statevector simulation or GPU acceleration is claimed. Phase 7.1 is a small classical control/reference model.
- No restricted-PUI tree is emitted here.
- No batch schedule or Algorithm 3 row-selection/counter-CX loop is inferred here.
- No Toffoli resource count is reported here.

## 7. Acceptance rationale

Tests cover sign-domain validation, marker initialization and transition, reversible basis-gate actions, marker-controlled CX, exact phase multiplication, explicit PUI-affected-row coverage, transactional collision rejection, duplicate-visit rejection, total/injective output verification, all-positive/all-negative/alternating signs, seeded random signs, and JSON trace output.

The Phase 7.1 exit gate is therefore a verified model for the sign/marker semantics that Phase 7.2 can use as an oracle. It is not the final real-state implementation.
