# Phase 8.1 acceptance checklist

- [x] Consume Phase-7 `ell`, `compact_labels` and aligned `signs` without mutating the result.
- [x] Reject malformed widths, duplicate/out-of-range labels and invalid signs.
- [x] Compile each negative label into an exact basis-state phase flip.
- [x] Lower multi-controlled phase flips into H/X/Z/CX/Toffoli operations.
- [x] Compute and uncompute clean ancillas for larger MCX controls.
- [x] Cover zero-qubit, one-qubit, all-positive and multi-control boundaries.
- [x] Verify every compact-register basis state against the direct diagonal oracle.
- [x] Compare complex superpositions, not only output probabilities.
- [x] Keep phase-oracle resources separate from paper-accounted Algorithm-3 resources.
- [ ] Run `bash scripts/run_phase8_1_validation.sh` in the user's local project environment.
- [ ] Commit after local acceptance; do not push.

## Acceptance commands

```bash
bash scripts/run_phase8_1_tests.sh
bash scripts/run_phase8_1_validation.sh
git diff --check
```

Phase 8.1 is locally accepted only when the complete project suite passes on the user's machine. The two CUDA tests should execute, not skip, when the local CuPy/CUDA environment is available.
