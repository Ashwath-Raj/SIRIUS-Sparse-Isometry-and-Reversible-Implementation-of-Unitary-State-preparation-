# Phase 4 — Malvetti isometry baseline

## Scope and source

This phase implements the **Malvetti et al. isometry-finding baseline recalled in Section 2 of Rupprecht & Wölk (2026)**. It does not implement the separate sparse-state-pivoting procedure in Section 2 of Malvetti et al. (2021).

Primary source: Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026), Section 2, especially the discussion and Figure 3 on journal PDF pages 4–5. DOI: <https://doi.org/10.22331/q-2026-09-10-2208>.

The source defines an `s`-row, `n`-column target tableau and divides each row at `ell = ceil(log2(s))` into a subspace prefix and a residual suffix. The algorithm constructs a circuit `G` and bijection `f` satisfying

\[
G|C_i\rangle = |f(i)\rangle_s |0\rangle_r.
\]

The state-preparation isometry is `G†`, the inverse of this forward compression circuit.

## Implemented algorithm

Rows are processed in their original stable row-ID order. All gates are applied to the **entire current tableau**, because a controlled operation selected for one row can change other not-yet-processed rows.

1. Split each current row into its first `ell` bits (subspace register) and remaining `n-ell` bits (residual register).
2. If the residual register is all zero, assign its existing subspace label as `f(i)` and emit no gate.
3. Otherwise choose the leftmost set residual bit `l`. Choose an unused subspace label `k`; preserve the row's current prefix when it is unused, otherwise choose the lowest free label. The paper requires an unused label but does not specify a unique free-label selection order. This deterministic fallback is an implementation choice, not a claim to reproduce the exact labels drawn in Figure 3.
4. Apply CX gates controlled on residual bit `l` to every other bit that differs from the desired state `|k>|e_l>`. This is the explicit decomposition of the paper's multi-target-CX operation. It maps the selected row to `|k>|e_l>` while leaving rows already in the subspace unchanged (their residual control bit is zero).
5. Apply an `ell`-controlled-X, controlled on address `k`, targeting residual bit `l`. The selected row becomes `|k>|0>`. The chosen label is reserved so no earlier subspace row is altered by this controlled-X.
6. Continue with the updated tableau until every row has a distinct subspace label and zero residual register.

The emitted CX and MCX gates are represented using the Phase 3 reversible gate IR. MCX remains a symbolic gate; the resource model separately applies the paper's AND-ladder cost.

## Resource model

For each zeroing `ell`-controlled-X, the baseline counts `ell-1` Toffolis and `ell-2` clean ancillas (for the nontrivial range stated in the paper). The worst-case isometry Toffoli cost is

\[
T_{\u007b\mathrm{baseline}\u007d}=s(\ell-1).
\]

The implementation reports both the actual number of zeroing MCX calls produced by the trace and the paper's worst-case bound. It also reports explicit CX count separately. Dense-state-preparation cost is excluded: this phase validates only the isometry component, matching the comparison in Section 2 and Table 1 of Rupprecht & Wölk.

Boundary handling is explicit: `s=1` uses a direct X map with no MCX, `ell=1` controlled-X operations have zero Toffoli cost, and `n=ell` has an empty residual register and requires no isometry work.

## Validation evidence

The main fixture uses the seven-row input tableau from Figure 3 of Rupprecht & Wölk (2026). It verifies that the implementation maps those rows to a valid distinct subspace labeling with zero residual suffixes. The paper's rule permits any label not already present in the subspace register, so the implementation does not require the exact particular output-label assignment illustrated in Figure 3. Tests also verify stable row-ID tracking, whole-tableau updates, inverse-circuit correctness, resource accounting, boundary cases, and seeded randomized small tableaux.

## Limitations

- The phase validates the **classical reversible basis action** and the baseline Toffoli/ancilla accounting. It does not yet synthesize the MCX macros into a physical Toffoli network.
- It does not include dense-state preparation or coefficient rotations.
- The implementation uses a deterministic label-selection policy (retain the current prefix if free, otherwise lowest free label). Because the paper does not specify a unique choice among all unused labels, the output bijection can differ from the particular one drawn in Figure 3. The policy is not claimed to optimize CX count over all possible choices.
