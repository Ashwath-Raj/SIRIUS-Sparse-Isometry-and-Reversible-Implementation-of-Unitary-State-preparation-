# Phase 8.1 starter validation record

Packaging-environment validation:

- `python -m compileall -q candidate_ai/src/sparseprep`: passed.
- `bash scripts/run_phase8_1_tests.sh`: **12 passed**.
- `PYTHONPATH=candidate_ai/src python -m pytest -q -rs candidate_ai/tests`: **135 passed, 2 skipped in 3.83s**.
- Skips: `candidate_ai/tests/test_cupy_parity.py` tests 19 and 30; this packaging Python environment does not have the CuPy CUDA backend.
- The full-suite run includes all prior project tests plus the 12 Phase 8.1 tests.

These are packaging-environment results, not local acceptance on the user's Nitro RTX 3050. Run the included full validation script locally; the existing CUDA parity/device tests should execute there if the project's CuPy/CUDA environment remains available.
