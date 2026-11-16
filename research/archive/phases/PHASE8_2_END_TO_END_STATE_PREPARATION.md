# Phase 8.2 — End-to-end sparse quantum-state preparation

## 1. Objective and interface

Phase 8.2 closes the state-preparation composition gap left by Phases 7 and 8.1. Its input is a `SparseStateProblem` with:

- an ordered, duplicate-free `support` of `s` computational-basis strings of width `n`;
- normalized complex `coefficients=(c_0,...,c_(s-1))` aligned with that support order;
- optional independent `signs=(a_0,...,a_(s-1))`, where each `a_i` is exactly `+1` or `-1`.

The requested output is

\[
|\psi_{\rm target}\rangle=\sum_{i=0}^{s-1} a_i c_i |x_i\rangle.
\]

The sign metadata is intentionally independent of the complex coefficient values, following the `SparseStateProblem` contract. Missing coefficients are rejected: support-only inputs describe a valid structural problem but do not specify a unique target state.

## 2. Composition order

Let `U_A` be the reversible basis permutation emitted by Phase 7. Its verified mapping is

\[
U_A\bigl(|x_i\rangle|1\rangle_m|0\rangle_w\bigr)
 = |f(i)\rangle|0^{n-\ell}\rangle|0\rangle_m|0\rangle_w,
\qquad \ell=\lceil\log_2 s\rceil.
\]

Phase 8.2 prepares the compact vector, applies the Phase-8.1 sign oracle `P`, and executes the inverse map:

\[
|0^\ell\rangle|0^{n-\ell}\rangle|0\rangle_m|0\rangle_w
\xrightarrow{D}
\sum_i c_i|f(i)\rangle|0^{n-\ell}\rangle|0\rangle_m|0\rangle_w
\xrightarrow{P}
\sum_i a_i c_i|f(i)\rangle|0^{n-\ell}\rangle|0\rangle_m|0\rangle_w
\xrightarrow{U_A^\dagger}
\sum_i a_i c_i|x_i\rangle|1\rangle_m|0\rangle_w.
\]

A final `X` on the marker `m` returns it to `|0>`. Phase-oracle work wires are allocated separately from Algorithm-3 isometry ancillas; they are reused only within blocks that explicitly uncompute them.

## 3. Dense compact-register loader

The dense loader writes magnitudes first and coefficient arguments second.

For each binary prefix `p` of length `d`, define its two child-subtree norms

\[
r_{p0}=\sqrt{\sum_{j\text{ begins with }p0}|c_j|^2},\qquad
r_{p1}=\sqrt{\sum_{j\text{ begins with }p1}|c_j|^2}.
\]

The loader emits a prefix-controlled rotation on compact wire `d` with

\[
\theta_p=2\operatorname{atan2}(r_{p1},r_{p0}).
\]

This creates the correct nonnegative magnitude at every compact label, including padded labels with zero amplitude and cases where the support-to-label map is not in support order. Subtree norms are accumulated bottom-up once, so parameter construction is `O(2^ell)` rather than rescanning each suffix at every depth.

Each coefficient argument `\phi_i=\arg(c_i)` is then applied only to its compact label `f(i)`. The controlled-rotation and basis-selective phase blocks are lowered to RY/PHASE, CX and clean-ancilla Toffoli operations. Multi-control conjunctions are computed and uncomputed immediately. Target-zero and negative-control patterns are handled by reversible X conjugation.

## 4. Statevector and inverse verification

`SparseStatePreparationCircuit.verify()` checks the full complex output, not measurement probabilities alone. It reports:

- state fidelity against the explicitly constructed target vector;
- maximum per-amplitude error;
- probability outside the declared support;
- probability in any nonzero marker or work-ancilla sector;
- output norm error;
- inverse round-trip error after applying the exact reversed circuit.

The inverse check returns the full register to `|0...0>`. This covers the data register, marker, Algorithm-3 ancillas and Phase-8 work ancillas.

## 5. Resource accounting

The result reports per-stage gate counts for:

1. dense magnitude and complex-phase loader;
2. Phase-8.1 real-sign oracle;
3. inverse Algorithm-3 isometry;
4. marker cleanup.

It also preserves Algorithm-3's paper-accounted and coherent Toffoli numbers as separate fields. The explicit dense-loader and sign-oracle overhead is not silently folded into the paper's Algorithm-3 bound.

## 6. Logical-circuit boundary

The emitted circuit is an exact logical reference circuit using `H`, `X`, `Z`, `RY`, `PHASE`, `CX`, `Toffoli` and `SWAP`. It is **not** a backend-transpiled hardware-native circuit. In particular, Toffoli decomposition into a selected hardware basis, coupling-map routing, scheduling, noise modelling and device execution belong to Phase 9 benchmarking. This boundary is explicit in the resource report.

## 7. Public API

```python
from sparseprep import SparseStateProblem, prepare_sparse_state

problem = SparseStateProblem(
    n=4,
    support=("0001", "0110", "1011"),
    coefficients=(1 / 3**0.5, 1j / 3**0.5, -1 / 3**0.5),
    signs=(1, -1, 1),
)

circuit, metrics = prepare_sparse_state(problem)
print(metrics.fidelity, metrics.workspace_leakage_probability)
print(circuit.resources)
```

For a circuit too large for exact statevector simulation, use `compile_sparse_state_preparation(problem)` to obtain the logical circuit and resource counts, then validate it through Phase 9's scalable/backend route.

## 8. Phase 8 exit condition

Phase 8 is considered implemented when the Phase 8.1 and Phase 8.2 suites pass on the user's project, the complete regression suite passes, and the local Git tree is clean after commit. The package-environment run is evidence for the implementation but does not replace the user's local run. After local Phase 8 acceptance, the remaining planned milestone is Phase 9 benchmarking and paper comparison.
