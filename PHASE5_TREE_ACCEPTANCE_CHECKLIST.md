# Phase 5 — Shared-prefix PUI tree emitter acceptance

- [x] Restricted and unrestricted recursive branch logic implemented from Algorithm 2.
- [x] Unrestricted left-only branch omits the split-bit selector and preserves exact `L,g` effects.
- [x] Shared prefix selectors are computed once per visited tree node and depth ancillas are reused.
- [x] Figure 7 left and right extra-address examples reproduced.
- [x] Optimized tree basis action matches direct MCX semantic oracle for every interval through address width 4.
- [x] Address register preserved and clean ancillas returned to zero.
- [x] Inverse circuit round-trips all tested basis states.
- [x] Full unary iteration count is `2^w - 2` paper-accounted Toffolis, with at most `w-1` clean ancillas.
- [x] Aligned repeated-interval per-block costs and aggregate Equations 7/8 are tested.
- [x] Coherent compute/uncompute count is clearly separated from paper measurement-based AND-adjoint accounting.
- [ ] Operator validation on the user's RTX 3050 (PUI itself is CPU gate-emission logic; Phase 3 CUDA tests remain part of the integrated suite).
- [ ] Local Git commit after operator test output is reviewed.
