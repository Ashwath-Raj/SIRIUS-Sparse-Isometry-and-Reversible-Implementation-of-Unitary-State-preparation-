# Phase 8.2 acceptance checklist

- [ ] Apply ZIP overlay to the existing project root.
- [ ] `bash scripts/run_phase8_2_tests.sh` passes.
- [ ] `bash scripts/run_phase8_2_validation.sh` passes.
- [ ] CUDA tests execute on local hardware if the project Python environment has CuPy/CUDA available; otherwise record the explicit skip reason.
- [ ] Verify full complex amplitudes, not only probabilities.
- [ ] Verify compact-label mapping is taken from Algorithm 3, not assumed to be support order.
- [ ] Verify coefficient phases and separate sign metadata are both applied exactly once.
- [ ] Verify marker, Algorithm-3 ancillas and Phase-8 ancillas finish in zero.
- [ ] Verify inverse round trip returns the entire register to all-zero.
- [ ] Run `git diff --check`.
- [ ] Review `git status --short` and stage only the Phase 8.2 files listed in `PHASE8_2_STARTER_VALIDATION.md`.
- [ ] Commit locally; do not push.

Phase 8 is closed after this acceptance gate. Phase 9 remains benchmarking, backend transpilation/execution and paper comparison.
