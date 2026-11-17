# Phase 8.1 — Physical real-sign phase synthesis

## Purpose

Phase 8.1 closes the physical-circuit gap left by Phase 7's real-sign ledger. It compiles the `+1/-1` signs attached to Algorithm 3's compact output labels into an exact diagonal quantum circuit. Phase 8.2 will prepare the dense compact-register amplitudes and compose this oracle with the inverse Phase-7 isometry to make the complete sparse-state preparation circuit.

## Delivered files

- `candidate_ai/src/sparseprep/phase_synthesis.py`
  - `compile_real_sign_phase_oracle(algorithm3_result)` compiles the Phase-7 sign/compact-label mapping.
  - `PhaseOracleCircuit` stores the gate-level operation sequence, clean-ancilla count and resources.
  - Exact statevector simulator for `H`, `X`, `Z`, `CX`, `Toffoli` and global phase.
  - Independent diagonal reference operation and exhaustive basis-state verification.
- `candidate_ai/tests/test_phase_synthesis_8_1.py` — targeted integration, gate, ancilla, boundary, superposition and invalid-input tests.
- `scripts/run_phase8_1_tests.sh` — targeted Phase 8.1 test suite.
- `scripts/run_phase8_1_validation.sh` — complete project regression.
- `research-notes/PHASE8_1_REAL_SIGN_PHASE_SYNTHESIS.md` — derivation, wire convention and cost-accounting boundary.

## Mathematical operation

Let the Phase-7 basis map send input support row `i` to its unique compact label `f(i)`, with requested real sign `a_i ∈ {+1,-1}`. Define

\[
P = I - 2\sum_{i:a_i=-1}|f(i)\rangle\langle f(i)|.
\]

Then `P |f(i)> = a_i |f(i)>`. Applying this diagonal operator to the dense compact-register state before the inverse Phase-7 basis map produces the requested real signs on the original support. Phase 8.1 implements `P`; Phase 8.2 will compose it with amplitude loading and the inverse isometry.

## Gate lowering

For each negative label, the compiler emits an exact basis-state phase flip. Zero-valued controls are normalized with `X`; `H`–MCX–`H` implements the multi-controlled Z; target/control normalization is then undone. MCX is lowered to:

- `CX` for one control;
- one `Toffoli` for two controls;
- a compute / target-flip / uncompute Toffoli ladder for three or more controls.

The ladder reuses `max(0, ell-3)` clean ancillas and resets them before the next phase flip. Wire 0 is the most-significant compact-label bit. Ancillas are appended after the data wires.

Special cases are explicit: `ell=0` uses a global `-1` phase for the singleton support; `ell=1` uses `Z` or `X-Z-X`; no negative signs produce an empty identity circuit.

## Cost-accounting boundary

`PhaseOracleResources` reports the emitted phase-oracle H, X, Z, CX and Toffoli counts, clean ancillas, and operation count. These are **additional reference-circuit costs**. They are not added to or relabelled as the paper's Algorithm-3 PUI-inline sign-fixing Toffoli bound. Phase 9 benchmarking must report the two separately.

This phase handles real signs only. It does not yet synthesize arbitrary complex coefficient phases or prepare amplitude magnitudes. Those belong to Phase 8.2.

## Local acceptance

```bash
bash scripts/run_phase8_1_tests.sh
bash scripts/run_phase8_1_validation.sh
git diff --check
```

The full suite should pass. Existing CUDA tests run when CuPy and a working CUDA device are available; the CPU statevector oracle is authoritative for this phase's diagonal unitary.
