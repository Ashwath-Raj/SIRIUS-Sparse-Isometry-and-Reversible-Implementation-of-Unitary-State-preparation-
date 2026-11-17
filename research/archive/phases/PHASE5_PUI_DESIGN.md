# Phase 5 — Partial Unary Iteration (PUI)

## Source-derived contract

Primary source: Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), Section 3, especially Algorithm 2 and Appendix A.

The paper defines PUI for an inclusive interval `[l, r]` in a `w`-qubit big-endian address register. At address `i`, the target operation is `U_i`. A restricted PUI acts trivially outside `[l,r]`. An unrestricted PUI may also apply a target operation to selected addresses strictly greater than `r`; those effects are specified by `L` and `g:L -> [l,r]`. Addresses below `l` remain untouched.

Algorithm 2 recursively traverses the balanced binary address tree:

- both half-intervals intersect the target interval: recurse into both halves;
- only the left half intersects: unrestricted PUI ignores that split bit and records it as free;
- only the right half intersects: recurse into the right half with the current prefix selector;
- at a leaf, enumerate every non-empty assignment to the free positions while keeping all fixed positions equal to the leaf. Those addresses form `L`, and `g` maps each to that leaf.

The paper states that either PUI type uses at most `w-1` ancillas. Appendix A describes the AND primitive and a measurement-based adjoint which has zero additional Toffoli cost under the paper's resource accounting.

## Implemented in this phase

`candidate_ai/src/sparseprep/pui.py` provides:

1. `build_pui_plan`: validates inclusive intervals, constructs the exact recursive tree trace, computes the unrestricted extra-address map `g`, and records the resulting address-to-unitary map.
2. An exact semantic lowering to address-equality-controlled `MCX` gates. This is a deliberately transparent truth-table/correctness oracle: it implements each requested `U_i` and each extra `U_{g(j)}` exactly, but it does **not** share prefix computations. It must not be advertised as the Toffoli-optimized physical tree circuit.
3. `mcx_ladder_cost`: separates the paper's measurement-based AND-adjoint accounting from a fully coherent unitary cleanup count.
4. `compile_mcx_coherent`: constructs a true reversible Toffoli ladder using clean ancillas, including negative controls by X conjugation, and returns all ancillas to zero.

## Deliberate boundary

The semantic MCX lowering is the exact oracle against which the later shared-prefix PUI tree emitter must be checked. It is not the optimized PUI circuit of Figure 6/7. In particular, its MCX-per-address decomposition generally costs more than the paper's repeated-interval PUI Toffoli bounds. The recursive trace and `L,g` map capture the paper's Algorithm 2 control semantics; a subsequent optimized emitter can lower its AND/CX/X branch primitives while preserving this oracle's basis action.

The current target-unitary interface supports X operations on one or more target wires, matching the isometry's one-hot residual-zeroing use case in Section 2. General arbitrary `U_i` target blocks are out of scope for this phase.

## Validation obligations

- Figure 7 left interval `[0,3]` on a 3-bit address register: unrestricted extras are `4->0, 5->1, 6->2, 7->3`.
- Figure 7 right interval `[4,6]`: unrestricted extra is `7->6`; restricted PUI has no extra addresses.
- Address bits are preserved.
- Every basis state receives exactly the target X operation selected by its address or by `g`.
- The compiled exact semantic circuit is self-inverse and round-trips the full basis space.
- Coherent MCX ladders compute the correct control conjunction and clean all ancillas; paper-accounted and coherent Toffoli costs are reported separately.

## Reproducibility note

The PUI planner and its semantic expansion do not use CUDA. This is expected: the gate sequence and address-map construction are small classical control-flow tasks. The CUDA backend remains relevant for later bulk basis-state and benchmark workloads.

## Analytical repeated-interval bounds

`repeated_pui_cost_bound` implements the paper's Section 3 repeated-interval upper bounds under the stated domain `2^(w-1) < s <= 2^w`, with `m=2^p <= 2^w`:

- unrestricted PUI (Eq. 7): `ceil(s/m) * (m + log2(S/m)/2 - 2)`;
- restricted PUI (Eq. 8): `ceil(s/m) * (m + log2(S/m) - 2)`;
- `S=2^w`, and the PUI workspace bound is at most `w-1` ancillas.

These equations are aggregate bounds for successive power-of-two intervals. They must not be confused with the per-circuit count of the direct MCX semantic oracle.
