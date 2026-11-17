# Validation Scorecard

## Scale

Each dimension is scored from 0 to 5: 0 = no implementation/evidence; 1 = design or structural code only; 2 = implementation with narrow tests; 3 = implementation with relevant regression evidence; 4 = broad invariant and differential evidence; 5 = independently reproduced at intended scale with complete provenance. Scores assess evidence, not research merit. A score is not a release gate by itself.

The before column is an inspection-based score for the initial clean checkout at `e90449e`, not a re-run of earlier claims. Historical audit-level references were 6.5/10 prototype and 3/10 reproduction; the supplied independent audit file was not present locally. After scores are limited to artifacts listed in the final report.

| Category | Before /5 | After /5 | Supporting evidence and deductions |
|---|---:|---:|---|
| Paper algorithm fidelity | 2 | 2 | [Traceability](FINAL_REQUIREMENT_TRACEABILITY.md), core algorithm tests, and [discrepancy record](PAPER_INTERPRETATION_AND_DISCREPANCIES.md). No independent paper-scale circuit comparison; Equation (3) remains unresolved. |
| Reversible correctness | 3 | 3 | Algorithm tests cover injectivity, forward/inverse, marker and ancilla cleanup. Current full regression suite ran; broader randomized exhaustive cross-check still needed. |
| Complex-state preparation | 2 | 3 | `test_state_preparation_8_2.py`, runner exact-statevector regression and matched complex metrics. Small exact cases only; no hardware. |
| Resource-accounting fidelity | 2 | 2 | PUI resource tests and separated paper/coherent/emitted/end-to-end fields. Official counter has observed underflow; Equation (3) ambiguity and two finite fixture divergences prevent higher credit. |
| Reference agreement | 1 | 3 | Verified artifact and extension, five ordered fixtures with total/injective mapping checks, matched smoke. Distinct pivot choices yield some Toffoli-count divergences; no broad gate-by-gate differential API. |
| Benchmark input integrity | 1 | 4 | Order-sensitive support hash tests, complete versioned workload identity, matched smoke JSONL. Full planned sweep not run. |
| Statistical validity | 1 | 3 | Workload/machine/source stratification, per-seed aggregation, paired summaries, status counts, tests. Only one seed in smoke; no statistical conclusions. |
| GPU execution validity | 1 | 2 | Runner executes compiled gate sequences and checks CPU parity; CPU-only unsupported/wire tests pass. No CUDA device, so actual GPU acceptance remains unverified. |
| Reproducibility | 2 | 3 | Artifact digest, machine manifest, commit/dirty/diff provenance and immutable JSONL. No lockfile for SIRIUS and the full campaign is absent. The older evidence branch was fetched and audited separately; its records are not treated as current-run artifacts. |
| Documentation integrity | 2 | 3 | New traceability, discrepancy, scorecard, and report; updates retain blocked/not-run labels and the report distinguishes historical Windows/CUDA evidence from the current Linux/no-GPU run. Full historical documentation/source alignment remains incomplete. |

**Totals:** initial inspection 17/50; after local repair evidence 28/50. The original audit's 6.5/10 and 3/10 are retained only as historical overall ratings and are not mathematically rescaled into this rubric. No evidence supports a release-ready claim.
