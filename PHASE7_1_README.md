# Phase 7.1 — Algorithm 3 sign/marker reference model

This is the first of two small Phase 7 deliveries. It adds an independent classical reference model for real-state sign and marker bookkeeping. It does not alter the Phase 3–6 implementation.

## Merge

Extract this ZIP into the existing project root, preserving directory structure. All paths are additive and use Phase 7.1-specific filenames; the package does not overwrite the root `README.md` or prior phase modules.

## Run

```bash
bash scripts/run_phase7_1_tests.sh
bash scripts/run_phase6_tests.sh
```

The first command tests the new reference model using the existing `.venv`. The second command runs the existing full test suite in the local project.

## Import

```python
from sparseprep.algorithms.phase_fixing import PhaseFixingTableau

support = ["000", "011", "101", "110"]
signs = [1, -1, 1, -1]
tableau = PhaseFixingTableau(support, signs)
```

Read `research-notes/PHASE7_1_SIGN_MARKER_MODEL.md` before treating the model as a circuit implementation. The exact Phase 7.1/7.2 boundary is documented there.

**No push.** Commit locally only after both acceptance commands pass.
