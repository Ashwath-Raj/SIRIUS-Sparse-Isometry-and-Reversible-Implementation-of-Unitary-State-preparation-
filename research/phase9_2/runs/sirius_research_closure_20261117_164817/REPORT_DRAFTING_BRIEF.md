# Report drafting brief — Phase 9.2

This file is a structure for the later research report, not a claim about results.

1. **Abstract** — objective, algorithms compared, workload design, principal measured findings, and limitations.
2. **Research question and contribution** — independent implementation of sparse quantum state preparation and comparison against the Malvetti-style baseline and independent batched isometry construction.
3. **Methods** — support families, coefficient families, sign profiles, parameter sizes, random seeds, warmups/repetitions, timed construction versus verification, and statistical aggregation.
4. **Correctness** — exact statevector fidelity, maximum amplitude error, workspace leakage, probability outside support, norm, and inverse round-trip. Report observed values from raw records only.
5. **CPU scaling and logical resources** — construction time, verification time, peak RSS, gate/resource histograms, logical width and logical IR depth. Define every metric precisely.
6. **GPU basis-row experiment** — H2D, device compute, D2H, total latency, CPU baseline, throughput, and parity. State explicitly that this is not full statevector acceleration.
7. **Authors-reference comparison** — currently blocked in the captured run because the Maturin executable was not located. Do not invent or estimate this comparison.
8. **Reproducibility** — source and hardware manifests, supports/coefficient vectors/sign vectors or hashes, seeds, environment, raw result paths, and analysis scripts.
9. **Threats to validity and limitations** — bounded workload matrix, simulator-versus-hardware distinction, blocked reference extension, and any failed/skipped cases.
10. **Conclusion** — only conclusions supported by aggregate data and confidence intervals.

Before drafting, reconcile the per-case JSONL records with the CSVs and ``closure_status.json``. Report failures and skips explicitly. Aggregate over seeds as specified by the run's methodology; do not treat repeated measurements of one seed as independent samples.
