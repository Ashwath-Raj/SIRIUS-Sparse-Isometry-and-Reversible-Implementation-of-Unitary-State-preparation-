# Phase 4 starter validation record

This validation was run in the build environment against the merged Phase 3 + Phase 4 candidate tree.

## Automated tests

Command:

```bash
PYTHONPATH=src python -m pytest tests -vv --durations=20
```

Result:

```text
47 passed, 2 skipped in 0.16s
```

The two skips are the Phase 3 CuPy parity/device tests because this build environment has no accessible CUDA device. The user's Phase 3 run already demonstrated both tests passing on the RTX 3050, but the Phase 4 merged suite must be run again in that environment before Phase 4 acceptance.

## Additional randomized validation

A separate deterministic property check ran 2,400 random sparse supports across `n=1..9`, checking every result's `verify()` invariants, distinct subspace labels, zero residual suffixes, and inverse mapping. All 2,400 instances passed.

## Figure 3 interpretation

The seven input rows from Figure 3 of Rupprecht & Wölk (2026) are included as a regression fixture. The paper requires selecting an unused subspace label but does not define a unique free-label selection order. Therefore, a different valid output bijection is accepted; the test verifies the isometry invariants and the `s(ell-1)` worst-case accounting rather than hardcoding the illustrated output labels.

## Scope boundary

This phase implements the sequential isometry-finding baseline only. It models each multi-controlled-X symbolically and reports its AND-ladder Toffoli/ancilla accounting. It does not yet decompose those macros into a physical Toffoli network, and it excludes dense-state preparation.
