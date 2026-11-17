# Phase 7.2 — Algorithm 3 integration

This combined handoff contains the Phase 7.1 sign-marker reference model and Phase 7.2 Algorithm 3 implementation. It is designed to be extracted directly into the existing project root. All Phase 7 paths are additive; no Phase 3–6 source files are overwritten.

## Run

```bash
bash scripts/run_phase7_2_tests.sh
bash scripts/run_phase6_tests.sh
```

The test runner uses the project's `.venv`. The new implementation is available as:

```python
from sparseprep import SparseStateProblem, run_algorithm3

problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
result = run_algorithm3(problem, signs=(1, -1, 1, -1))
result.verify()
```

Read `research-notes/PHASE7_2_ALGORITHM3_INTEGRATION.md` for algorithm details, resource-accounting conventions, and scope boundaries. The output includes a reversible basis-permutation circuit and an exact real-sign ledger; the sign ledger is not yet synthesized into physical Z/controlled-Z gates.

**Local commit only. Never push.**
