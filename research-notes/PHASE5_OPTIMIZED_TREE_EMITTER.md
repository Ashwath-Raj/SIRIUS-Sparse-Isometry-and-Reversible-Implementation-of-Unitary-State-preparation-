# Phase 5 addendum — shared-prefix balanced-tree PUI emitter

## Source contract

Primary source: Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), Section 3, Algorithm 2, Figures 6–7, and Appendix A.

The emitter lowers the recursive interval traversal into a reusable prefix-selector circuit. It preserves the paper's two modes:

- **Restricted:** every address outside the requested interval receives identity.
- **Unrestricted:** when only the left half of a node intersects the interval, the split bit is dropped and the parent selector is reused. That bit becomes free; the corresponding extra-address map `L,g` remains exactly the one recorded by `PUIPlan`.

## Emitter algorithm

`compile_pui_tree(plan)` accepts the existing `PUIPlan` semantic oracle and emits primitive reversible gates.

1. The root selector is implicit. The first address bit directly selects the left/right root branch, so it needs no AND ancilla.
2. When a selected node has both child intervals intersecting the requested interval, compute the left-child selector into the ancilla assigned to that tree depth using `AND(parent_selector, NOT(next_address_bit))`.
3. Visit the left subtree. XOR the parent selector into the child ancilla to convert it from the left-child selector into the right-child selector, then visit the right subtree.
4. Restore the left-child value and coherently reverse the AND computation. The same ancilla wire is reused by other nodes at that depth.
5. If only the right child intersects, compute `AND(parent_selector, next_address_bit)`, recurse, and uncompute.
6. If only the left child intersects, restricted PUI computes the zero-bit selector. Unrestricted PUI drops that split bit, records it as free, and recurses with the parent selector unchanged.
7. At a leaf, apply the address-specific target X operation under the current selector (or unconditionally if every path bit was free).

Negative controls are represented with explicit `NegativeControlToffoli` or X-conjugated CX sequences. Address wires are restored after each negative-control operation.

## Correctness oracle and tests

`PUIPlan.gates` remains the direct MCX-per-address semantic oracle. The new `PUITreeCircuit.gates` is the shared-prefix tree implementation. The new test suite compares both implementations on every interval for address widths 1–4, all address values, and all basis patterns of the target register. It also checks:

- both Figure 7 extra-address maps;
- exact address preservation;
- clean ancillas after the forward circuit;
- inverse round-trips;
- non-contiguous wire assignments;
- at most `w-1` distinct depth-reused ancilla wires;
- no per-address MCX macros in the optimized emitted sequence.

## Resource accounting — do not conflate two models

The code's coherent primitive sequence computes and explicitly reverses each AND selector. Therefore:

- `paper_accounted_toffolis` counts each AND compute once, matching the paper's Appendix A measurement-based AND-adjoint accounting (zero additional Toffoli cost for the adjoint).
- `coherent_toffolis` counts both compute and explicit coherent uncompute; it is twice the compute count for this emitter.

The simulator does **not** claim to implement the measurement/feed-forward details of Appendix A. The coherent sequence is the exact reversible correctness implementation; the paper-accounted figure is a separate resource model.

For full unary iteration on `w` address bits, the emitter's AND-compute count is `2^w - 2` and it reserves at most `w-1` clean ancillas.

For successive aligned intervals of size `m=2^p`, with prefix width `k=w-p`, it reproduces the paper's per-interval decomposition:

- Restricted: `m + k - 2` Toffolis per interval.
- Unrestricted prefix `q=0`: `m - 2`.
- Unrestricted prefix `q>0`: `m - 1 + max(popcount(q)-1, 0)`.

Summing over the full address space reproduces Equations (7) and (8). The implementation tests these per-interval and aggregate identities directly.

## Scope boundary

This completes the optimized PUI tree emitter and its resource accounting. It does not yet implement the complete batched isometry, Algorithm 3 sign-fix integration, or a hardware-specific measurement-based AND-adjoint backend. Those remain later phases.
