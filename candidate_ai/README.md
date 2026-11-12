# Phase 3 — Independent model, gate IR and validation harness

This package is an independent implementation workspace. It does not import or copy implementation code from the authors' reference package.

## Conventions

- Support strings use big-endian order: the leftmost character is the most-significant bit.
- Gate wire `0` is the leftmost/most-significant bit.
- Original support rows, current transformed rows, stable row IDs and phase signs remain separate in the tableau.
- Coefficients are optional and must be normalized when provided.
- `s=1` is explicit; the non-trivial batching width is intentionally undefined for that special case.
- The resource histogram reports emitted gate categories. `decomposed_toffoli=None` means no decomposition has been supplied; it does not mean zero.
- Restricted/unrestricted PUI are represented as symbolic macros with interval and `(L,g)` metadata. They are not simulated in Phase 3; their paper-specific expansion belongs to Phase 5.
- Candidate support patterns are structural witnesses. They are not claimed to trigger a specific algorithm branch until Phase 4/5 trace instrumentation confirms it.

## Run tests from the project root

Use the project's existing Python environment. NumPy and CuPy are optional for the Phase 3 CPU package; CuPy parity tests run when CUDA is available.

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest candidate_ai/tests -vv
```

If the project's root environment uses a different path, substitute its Python executable. Do not install anything into `reference/authors-artifact/` and do not regenerate the authors' lockfiles.

## Phase 3 boundaries

This phase creates the data contract, basis-state gate simulator, tableau, resource histogram, deterministic support generators and optional CuPy parity backend. It does not implement Malvetti, PUI expansion, the batching algorithm or Algorithm 3. Those belong to later phases and must be derived from the paper before coding.
