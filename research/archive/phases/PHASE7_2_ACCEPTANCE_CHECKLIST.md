# Phase 7.2 acceptance checklist

- [ ] Extract the combined Phase 7.1 + 7.2 ZIP into the project root.
- [ ] Run `bash scripts/run_phase7_2_tests.sh`.
- [ ] Run `bash scripts/run_phase6_tests.sh`.
- [ ] Confirm the working tree contains only intended Phase 7.1/7.2 additions.
- [ ] Review `research-notes/PHASE7_2_ALGORITHM3_INTEGRATION.md` and the sign/phase representation boundary.
- [ ] Commit locally after both test commands pass.
- [ ] Do not push.

Acceptance invariants enforced by `Algorithm3Result.verify()`:

1. Compact labels are injective and in range.
2. Every residual register is zero.
3. Every marker is zero.
4. Accumulated signs equal the requested ±1 signs.
5. Forward and inverse circuits round-trip every support row and clean PUI ancilla.
6. Coherent Toffoli accounting equals the Toffoli-family gates in the emitted IR.
