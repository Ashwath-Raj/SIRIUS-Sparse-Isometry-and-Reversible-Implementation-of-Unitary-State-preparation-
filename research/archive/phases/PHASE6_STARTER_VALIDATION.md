# Phase 6 starter validation record

Prepared in the ChatGPT build environment on 2026-11-14.

- Integrated Python suite: **94 passed, 2 skipped**.
- The two skips are inherited CUDA tests because this packaging environment has no accessible GPU/CuPy runtime. The user's Phase 3–5 runs already demonstrated both tests on the RTX 3050; the Phase 6 integrated run must execute them again.
- Additional seeded fuzz campaign: **3,600 / 3,600 supports verified**, with direct/SWAP/Toffoli fallback paths exercised and no Eq. (1) violations in the parameter cases where the formula is reported.
- `python -m py_compile` passed for the new batched-isometry module and updated package initializer.
- No user repository, remote, or authors' reference source was modified by preparing this ZIP.

This is a starter validation record, not a claim that the user's local Phase 6 run has passed. The user's run and local Git commit are still required.
