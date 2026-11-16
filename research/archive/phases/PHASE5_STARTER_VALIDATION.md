# Phase 5 Starter Validation

## Local build-environment result

The merged Phase 3 + Phase 4 + Phase 5 candidate test suite was executed in the package build environment:

```text
70 passed, 2 skipped in 0.20s
```

The two skipped tests are the CUDA-specific Phase 3 tests because this build environment has no accessible CUDA device. The user's RTX 3050 must run them locally; they are not counted as validated here.

## What this validates

- Existing Phase 3 model, gate IR, CPU simulator, tableau and generators.
- Existing Phase 4 Malvetti baseline.
- PUI restricted/unrestricted address mapping and exact `L,g` semantics.
- Figure 7 extra-address examples `[0,3]` and `[4,6]`.
- Exact MCX semantic lowering, address preservation and inverse round-trip.
- Coherent MCX ladder behaviour, negative controls and clean-ancilla restoration.
- Paper's repeated-interval PUI bounds (Equations 7 and 8).

This is starter validation, not a claim that the paper's optimized shared-prefix PUI emitter has been implemented. The semantic MCX lowering is the correctness oracle for that later compiler.

## User-machine acceptance

Run `bash scripts/run_phase5_tests.sh` in the project root. Expected collection is 72 tests; on the user's CUDA-enabled machine both CUDA tests should execute rather than skip. Preserve the actual full output before committing Phase 5.
