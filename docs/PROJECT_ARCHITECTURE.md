# Project architecture and module map

```text
SparseStateProblem
  ├── model.py                  validated ordered support, coefficients, signs
  ├── support_generators.py     deterministic structural workload families
  ├── malvetti_baseline.py      sequential isometry comparator
  ├── batched_isometry.py       independent batched isometry construction
  │    ├── pui.py               PUI interval plans and cost models
  │    └── pui_tree.py          reversible restricted/unrestricted PUI tree
  ├── algorithm3.py             marker/sign-aware batched isometry
  │    └── algorithms/phase_fixing.py  signed tableau model
  ├── phase_synthesis.py        real-sign diagonal phase oracle
  ├── state_preparation.py      dense compact loader + complex phase + inverse map
  ├── simulator.py              exact CPU computational-basis simulator
  ├── backends/cupy_simulator.py optional GPU uint64 basis-row batch simulator
  └── resources.py               emitted primitive/symbolic gate histogram

Phase 9.1
  ├── benchmarking/config/       pinned experiment plan
  ├── benchmarking/metric_catalog.json
  ├── benchmarking/schemas/      run, summary and machine data contracts
  ├── benchmarking/templates/    placeholder-only record templates
  └── scripts/phase9_1_validate.py  plan validator + dry-run manifest generator

Phase 9.2 (local only, uncommitted)
  ├── device-specific environment setup and machine manifests
  ├── version-pinned authors' artifact adapter
  ├── runner/timing/telemetry instrumentation
  ├── raw JSONL observations, summaries and plots
  └── per-device result packages
```

## Execution boundaries

- Classical circuit construction and algorithm selection run on CPU in the current implementation.
- CuPy vectorizes computational-basis row transformations in uint64 batches; `n` is limited to 63 for this backend.
- Full complex statevector verification currently uses the CPU logical-operation simulator and is deliberately capped to avoid exponential memory allocations.
- Logical Toffoli counts are resource estimates independent of the machine on which construction is performed.
- Native-gate depth and T-count need a fixed decomposition and backend target before they can be reported.
