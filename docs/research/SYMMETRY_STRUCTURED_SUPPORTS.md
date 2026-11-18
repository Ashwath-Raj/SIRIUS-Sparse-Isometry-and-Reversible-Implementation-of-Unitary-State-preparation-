# Symmetry-Structured Sparse Supports

## Research question and status

At fixed register width (n) and support cardinality (s), does support geometry affect construction cost, logical resources, or reversible basis-row execution? This is an exploratory extension. It is not a proven novel algorithm or novelty claim.

## Hypotheses

H1: fixed-Hamming-weight supports may have different prefix occupancy and pairwise Hamming-distance distributions from unconstrained random supports, which may correlate with SIRIUS construction work. H2: support ordering may affect deterministic tableau choices and therefore construction time or resource counts while preserving the same mathematical state when amplitudes/signs remain attached to their basis rows. These are hypotheses, not expected outcomes.

## Workloads and controls

Version 1 samples (s) distinct strings from \\(\Omega_{n,k}=\\{x\\in\\{0,1\\}^n:|x|=k\\}\\) using a recorded Python `random.Random(seed)` sample and sorts the support for the canonical base ordering. Invalid (s>\\binom{n}{k}) is rejected. Pilot values use (n\\in\\{8,10\\}), (k=\\lfloor n/2\\rfloor), (s\\in\\{3,5\\}), and seeds 101 and 211.

The random-support comparator uses the same (n,s,seed) strategy. Each has complex normalized coefficients and independent real sign metadata generated from the same seed-derived coefficient/sign vectors, assigned by canonical sorted support position. The two supports are different mathematical states; this controls workload shape and coefficient/sign generation, not exact input-state identity. For fixed-weight ordering comparisons, lexicographic and seeded-shuffled variants preserve the basis-state-to-coefficient/sign mapping exactly. Canonical mathematical-instance digests are order-independent; ordered input digests change with order.

Both the independent batched-isometry candidate and Malvetti baseline run on eligible inputs. The paper track separately includes one end-to-end exact-statevector attempt and an authors adapter attempt. Authors comparison is not applied to the extension. GPU work is only the emitted reversible circuit on uint64 basis rows with CPU parity, not construction, complex amplitudes, or device execution.

## Measurements

Paper-accounted Toffoli, coherent Toffoli, emitted operations, clean ancillas, logical resource details, one-shot construction wall/process CPU time, process peak RSS, batch/PUI statistics, correctness, support geometry, and applicable GPU stage timings are recorded separately. Operation count is never labeled depth. RSS is a process high-water mark, so within-process per-case deltas are not claimed.

Pairwise Hamming-distance count/mean/min/max, distinct prefix occupancy at each depth, prefix child branching, and sector density (s/\\binom{n}{k}) are included where defined. Unsupported/unavailable values are `null` or omitted with a scope explanation.

## Analysis limitations

The laptop pilot has only two independent seeds per most strata and one timing observation per attempt. No inferential confidence intervals, significance claims, or general speedup claims are warranted. Construction is an in-process single observation, and system thermal/background variation is monitored but not fully controlled. The support families have different mathematical supports; their comparison is across matched dimensions, seeds and amplitude/sign generation settings, not a paired statevector identity comparison.

## Reproduction

See `benchmarking/config/ubuntu_laptop_pilot_v1.json` and `docs/benchmarking/UBUNTU_RTX3050_WORKFLOW.md`. The deterministic generator is `benchmarking/extensions/symmetry_workloads.py`; raw Track B records are kept under `results/raw/<machine-id>/extensions/symmetry_structured_sparse_supports/`.
