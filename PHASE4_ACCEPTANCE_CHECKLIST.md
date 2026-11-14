# Phase 4 acceptance checklist — Malvetti baseline

- [ ] The baseline is specifically the Section 2 isometry algorithm recalled by Rupprecht & Wölk (2026), not the separate CNOT sparse-state-pivoting method in Malvetti et al. (2021).
- [ ] The implementation preserves stable row IDs while applying each gate to the whole current tableau.
- [ ] Each output row has zero residual bits.
- [ ] `f` is injective and every label lies in `[0, 2^ell)`.
- [ ] The forward circuit maps every input row to `|f(i)>|0>`.
- [ ] The inverse circuit maps every compacted row back to its original row.
- [ ] The seven-row input tableau from Figure 3 is a fixture; output is checked for a valid injective subspace labeling with zero residual suffix (the free-label choice need not match the figure exactly).
- [ ] Actual Toffoli count equals `zeroing_mcx_count * max(ell-1, 0)` under the paper's AND-ladder accounting.
- [ ] Actual Toffoli count does not exceed the worst-case `s(ell-1)` bound.
- [ ] CX count is reported separately; dense-state-preparation cost is excluded.
