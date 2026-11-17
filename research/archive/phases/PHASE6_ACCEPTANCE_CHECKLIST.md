# Phase 6 acceptance checklist

- [ ] `sha256sum -c SHA256SUMS` succeeds before copying files.
- [ ] Existing Phase 3–5 source and tests remain present.
- [ ] `bash scripts/run_phase6_tests.sh` completes successfully.
- [ ] Phase 6 Figure 4, batch fallback, unrestricted PUI, final-collision and boundary tests pass.
- [ ] Both inherited CUDA parity tests execute on the RTX 3050 (not skipped) in the integrated local environment.
- [ ] `bash scripts/run_phase6_fuzz.sh` reports 3,600 verified cases and zero Eq. (1) bound violations for cases where the bound is reported.
- [ ] Review `research-notes/PHASE6_BATCHED_ISOMETRY.md`, especially the generalized final-collision repair and symbolic-MCX limitations.
- [ ] Review `git diff --check` and `git status`.
- [ ] Commit Phase 6 locally only after review; do not push.
