# SIRIUS — Phase 9.2 Research Closure Report

Generated: 2026-11-17T11:56:17.797500Z
Repository branch: `cleanup/phase9-2-modernization`
Source commit: `e90449ea7c4751ed125aad88fef8d2f142086dc6`

## Executive assessment

**RESEARCH CLOSURE INCOMPLETE.** The execution completed, but one or more gates remain blocked or failed. Do not tag this as a research-validated release.

## Run coverage

- CPU compilation/resource cases: 300/300 completed.
- Authors' Rust differential cases: 0/150 completed; exact Toffoli-cost matches: 0/150.
- GPU basis-row cases: 90/90 completed with per-case exact parity.
- End-to-end state-preparation cases: 90/90 completed; exact statevector passes: 90/90.
- Full test suite: PASS
- GPU CuPy parity suite: PASS

## Experimental design

- Isometry scaling: five selected parameter pairs spanning n=16..63 and s=16..256: `[(16, 16), (24, 64), (32, 128), (48, 255), (63, 256)]`, support families `['seeded_random', 'zero_residual_subspace', 'repeated_prefix']`, seeds `[101, 211, 307, 401, 503]`.
- This is a representative five-point path through the Phase 9.1 scaling domain, not the full Cartesian product of all listed n/s values. The exact executed matrix is saved in the raw input ledger.
- CPU methods: independent batched isometry, Malvetti baseline, Algorithm 3 for both sign profiles.
- End-to-end exact statevector: size `(8, 8)`, all three support families, all coefficient families, both sign profiles, five seeds.
- GPU: sizes `[(24, 64), (32, 128)]`, all support families and five seeds; independent isometry, Malvetti and Algorithm 3 random-sign paths.
- Each compilation benchmark uses two warm-ups and five measured repetitions; each exact statevector is independently verified.
- Per-case process timeout: 180s CPU/authors and 240s GPU. All failures and timeouts are retained.

## Hardware manifest

- OS: Windows-11-10.0.26200-SP0
- CPU: AMD64 Family 25 Model 97 Stepping 2, AuthenticAMD (16 logical CPUs)
- RAM: 67837333504 bytes
- GPU: NVIDIA GeForce RTX 5060 Ti, 16311, 610.60
- Python: 3.12.13

## Authors' reference differential

- Rust unit tests: PASS
- Extension build: BLOCKED
- Official artifact MD5: c58634ba415b4e3fb729648460f32ad7
- Cost matches: 0/150.
- Reference and candidate compact-label mappings need not be identical: valid bijections may differ. Both mappings are checked for complete row coverage and injectivity.
- Toffoli equality is measured independently; discrepancies are retained and block the release gate.

## Resource accounting

The CSV ledger records paper-accounted Toffoli, coherent Toffoli, emitted IR histogram, clean ancillas, logical width, peak RSS and logical IR depth where the source implementation exposes them.
Logical IR depth uses an ASAP wire-conflict schedule over symbolic operations. It is not a native hardware depth or a transpiled schedule. Multi-controlled and PUI macros remain symbolic where the implementation emits them symbolically.
The end-to-end circuit separates Algorithm 3 paper/coherent Toffoli accounting from dense-loader, sign-oracle and inverse-isometry gate totals.

## GPU scope boundary

GPU benchmarks measure CuPy `uint64` reversible computational-basis row transformations. They do not measure GPU circuit synthesis, complex amplitudes, a full statevector, or quantum hardware execution. H2D, device execution and D2H are reported separately; total latency includes all three.

## End-to-end correctness

For every end-to-end workload, the report captures fidelity, maximum amplitude error, outside-support probability, workspace leakage, output norm and inverse round-trip error. Only cases whose complete circuit width is at or below the configured 20-qubit cap are statevector-verified. A cap skip is not counted as a pass.

## Gate results


## CPU construction wall-time scaling (ms)

| Method / workload | Seeds | Median | IQR | 95% bootstrap CI |
|---|---:|---:|---:|---|
| algorithm3 / 16 / 16 / repeated_prefix / all_positive | 5 | 3.8657 | 0.0168 | [3.7133, 3.8815] |
| algorithm3 / 16 / 16 / repeated_prefix / random_pm_one | 5 | 3.8524 | 0.0585 | [3.7272, 3.9923] |
| algorithm3 / 16 / 16 / seeded_random / all_positive | 5 | 3.7204 | 0.0573 | [3.6751, 3.8017] |
| algorithm3 / 16 / 16 / seeded_random / random_pm_one | 5 | 3.7405 | 0.0604 | [3.6814, 3.7920] |
| algorithm3 / 16 / 16 / zero_residual_subspace / all_positive | 5 | 3.3923 | 0.0381 | [3.3121, 3.4639] |
| algorithm3 / 16 / 16 / zero_residual_subspace / random_pm_one | 5 | 3.4240 | 0.0909 | [3.4007, 3.5672] |
| algorithm3 / 24 / 64 / repeated_prefix / all_positive | 5 | 66.3764 | 2.6337 | [64.7325, 68.7825] |
| algorithm3 / 24 / 64 / repeated_prefix / random_pm_one | 5 | 66.9251 | 0.3947 | [66.1614, 67.9509] |
| algorithm3 / 24 / 64 / seeded_random / all_positive | 5 | 66.0306 | 1.6072 | [65.1309, 68.4942] |
| algorithm3 / 24 / 64 / seeded_random / random_pm_one | 5 | 65.5617 | 2.2103 | [63.0052, 66.3159] |
| algorithm3 / 24 / 64 / zero_residual_subspace / all_positive | 5 | 56.7432 | 0.3400 | [54.5271, 58.4057] |
| algorithm3 / 24 / 64 / zero_residual_subspace / random_pm_one | 5 | 56.6392 | 0.9496 | [54.3263, 57.5236] |
| algorithm3 / 32 / 128 / repeated_prefix / all_positive | 5 | 298.9214 | 11.0342 | [290.1936, 304.4358] |
| algorithm3 / 32 / 128 / repeated_prefix / random_pm_one | 5 | 299.3236 | 1.4606 | [288.8779, 300.1191] |
| algorithm3 / 32 / 128 / seeded_random / all_positive | 5 | 298.2038 | 10.0587 | [287.2177, 300.6956] |
| algorithm3 / 32 / 128 / seeded_random / random_pm_one | 5 | 296.2260 | 3.5060 | [292.0684, 307.0593] |
| algorithm3 / 32 / 128 / zero_residual_subspace / all_positive | 5 | 245.1731 | 9.7071 | [242.6846, 254.0367] |
| algorithm3 / 32 / 128 / zero_residual_subspace / random_pm_one | 5 | 244.5577 | 2.0870 | [241.4100, 257.6923] |
| algorithm3 / 48 / 255 / repeated_prefix / all_positive | 5 | 1417.4345 | 17.3557 | [1379.7380, 1471.9880] |
| algorithm3 / 48 / 255 / repeated_prefix / random_pm_one | 5 | 1436.3207 | 67.2309 | [1378.1940, 1486.4849] |
| algorithm3 / 48 / 255 / seeded_random / all_positive | 5 | 1427.1032 | 37.9813 | [1383.9523, 1504.3081] |
| algorithm3 / 48 / 255 / seeded_random / random_pm_one | 5 | 1403.0907 | 27.4578 | [1387.0567, 1430.3455] |
| algorithm3 / 48 / 255 / zero_residual_subspace / all_positive | 5 | 1195.9679 | 44.3188 | [1153.7539, 1260.1288] |
| algorithm3 / 48 / 255 / zero_residual_subspace / random_pm_one | 5 | 1215.4536 | 64.3140 | [1175.3136, 1264.3746] |
| algorithm3 / 63 / 256 / repeated_prefix / all_positive | 5 | 1735.4627 | 67.4398 | [1698.6474, 1787.4382] |
| algorithm3 / 63 / 256 / repeated_prefix / random_pm_one | 5 | 1727.6370 | 30.0697 | [1681.4850, 3494.2046] |
| algorithm3 / 63 / 256 / seeded_random / all_positive | 5 | 1710.5164 | 37.8560 | [1670.8235, 1757.0958] |
| algorithm3 / 63 / 256 / seeded_random / random_pm_one | 5 | 1713.1317 | 19.9927 | [1705.0246, 1789.2660] |
| algorithm3 / 63 / 256 / zero_residual_subspace / all_positive | 5 | 1387.6450 | 21.6014 | [1353.9899, 1408.6522] |
| algorithm3 / 63 / 256 / zero_residual_subspace / random_pm_one | 5 | 1381.0987 | 28.4570 | [1356.3111, 1413.8138] |
| independent_batched_isometry / 16 / 16 / repeated_prefix | 5 | 3.2885 | 0.0391 | [3.1812, 3.3646] |
| independent_batched_isometry / 16 / 16 / seeded_random | 5 | 3.1314 | 0.1105 | [3.1051, 3.2752] |
| independent_batched_isometry / 16 / 16 / zero_residual_subspace | 5 | 0.0151 | 0.0005 | [0.0148, 0.0170] |
| independent_batched_isometry / 24 / 64 / repeated_prefix | 5 | 57.1141 | 0.7087 | [55.5520, 62.3865] |
| independent_batched_isometry / 24 / 64 / seeded_random | 5 | 56.2342 | 0.3688 | [55.3601, 56.7080] |
| independent_batched_isometry / 24 / 64 / zero_residual_subspace | 5 | 0.0297 | 0.0002 | [0.0292, 0.0331] |
| independent_batched_isometry / 32 / 128 / repeated_prefix | 5 | 246.8503 | 3.2658 | [240.9215, 248.8494] |
| independent_batched_isometry / 32 / 128 / seeded_random | 5 | 250.3903 | 4.4400 | [241.7756, 257.3544] |
| independent_batched_isometry / 32 / 128 / zero_residual_subspace | 5 | 0.0478 | 0.0002 | [0.0467, 0.0480] |
| independent_batched_isometry / 48 / 255 / repeated_prefix | 5 | 1206.1633 | 40.9103 | [1169.8865, 1237.2949] |
| independent_batched_isometry / 48 / 255 / seeded_random | 5 | 1231.2436 | 46.2125 | [1155.1648, 1250.2655] |
| independent_batched_isometry / 48 / 255 / zero_residual_subspace | 5 | 0.0846 | 0.0011 | [0.0842, 0.0855] |
| independent_batched_isometry / 63 / 256 / repeated_prefix | 5 | 1438.7626 | 8.2452 | [1422.0422, 1466.3438] |
| independent_batched_isometry / 63 / 256 / seeded_random | 5 | 1427.1169 | 10.8282 | [1414.6702, 1447.3284] |
| independent_batched_isometry / 63 / 256 / zero_residual_subspace | 5 | 0.0865 | 0.0015 | [0.0854, 0.0922] |
| malvetti_baseline / 16 / 16 / repeated_prefix | 5 | 2.5767 | 0.3736 | [2.2553, 3.1069] |
| malvetti_baseline / 16 / 16 / seeded_random | 5 | 2.7368 | 0.2314 | [2.6283, 2.9408] |
| malvetti_baseline / 16 / 16 / zero_residual_subspace | 5 | 0.0303 | 0.0002 | [0.0300, 0.0316] |
| malvetti_baseline / 24 / 64 / repeated_prefix | 5 | 68.2359 | 2.1700 | [62.3063, 69.0036] |
| malvetti_baseline / 24 / 64 / seeded_random | 5 | 71.7076 | 1.8456 | [66.2921, 78.3434] |
| malvetti_baseline / 24 / 64 / zero_residual_subspace | 5 | 0.1428 | 0.0031 | [0.1398, 0.1509] |
| malvetti_baseline / 32 / 128 / repeated_prefix | 5 | 427.8920 | 6.6434 | [402.3453, 437.5940] |
| malvetti_baseline / 32 / 128 / seeded_random | 5 | 447.7079 | 11.5486 | [425.9033, 453.8999] |
| malvetti_baseline / 32 / 128 / zero_residual_subspace | 5 | 0.3900 | 0.0036 | [0.3842, 0.3958] |
| malvetti_baseline / 48 / 255 / repeated_prefix | 5 | 3179.9643 | 55.0329 | [3093.7302, 3248.9406] |
| malvetti_baseline / 48 / 255 / seeded_random | 5 | 3347.9531 | 111.7691 | [3212.6904, 3794.3954] |
| malvetti_baseline / 48 / 255 / zero_residual_subspace | 5 | 1.1626 | 0.0140 | [1.1417, 1.1760] |
| malvetti_baseline / 63 / 256 / repeated_prefix | 5 | 5147.7177 | 131.4654 | [5044.3421, 5320.7468] |
| malvetti_baseline / 63 / 256 / seeded_random | 5 | 5382.8696 | 58.9806 | [5295.8685, 5501.8563] |
| malvetti_baseline / 63 / 256 / zero_residual_subspace | 5 | 1.1660 | 0.0275 | [1.1467, 1.2125] |

## GPU basis-row total latency (ms)

| Method / workload | Seeds | Median | IQR | 95% bootstrap CI |
|---|---:|---:|---:|---|
| algorithm3 / 24 / 64 / repeated_prefix / random_pm_one | 5 | 39.8633 | 0.3796 | [39.6078, 41.5423] |
| algorithm3 / 24 / 64 / seeded_random / random_pm_one | 5 | 40.8329 | 1.0837 | [39.7437, 41.5423] |
| algorithm3 / 24 / 64 / zero_residual_subspace / random_pm_one | 5 | 25.8673 | 0.1293 | [25.4435, 26.0698] |
| algorithm3 / 32 / 128 / repeated_prefix / random_pm_one | 5 | 87.5043 | 0.6271 | [85.9120, 87.9866] |
| algorithm3 / 32 / 128 / seeded_random / random_pm_one | 5 | 92.0083 | 1.0762 | [90.2794, 92.9904] |
| algorithm3 / 32 / 128 / zero_residual_subspace / random_pm_one | 5 | 51.4963 | 0.2329 | [51.1348, 51.6272] |
| independent_batched_isometry / 24 / 64 / repeated_prefix / none | 5 | 36.4894 | 0.6746 | [35.5236, 37.1043] |
| independent_batched_isometry / 24 / 64 / seeded_random / none | 5 | 37.1821 | 1.1041 | [36.0371, 38.2566] |
| independent_batched_isometry / 24 / 64 / zero_residual_subspace / none | 5 | 0.1875 | 0.0003 | [0.1847, 0.1897] |
| independent_batched_isometry / 32 / 128 / repeated_prefix / none | 5 | 77.6594 | 1.2897 | [76.4300, 78.2054] |
| independent_batched_isometry / 32 / 128 / seeded_random / none | 5 | 83.8730 | 1.5865 | [82.2655, 84.7263] |
| independent_batched_isometry / 32 / 128 / zero_residual_subspace / none | 5 | 0.1997 | 0.0028 | [0.1938, 0.2098] |
| malvetti_baseline / 24 / 64 / repeated_prefix / none | 5 | 38.5745 | 0.6304 | [36.6034, 38.6815] |
| malvetti_baseline / 24 / 64 / seeded_random / none | 5 | 39.8251 | 2.1280 | [38.8091, 42.9443] |
| malvetti_baseline / 24 / 64 / zero_residual_subspace / none | 5 | 0.1880 | 0.0044 | [0.1847, 0.1894] |
| malvetti_baseline / 32 / 128 / repeated_prefix / none | 5 | 101.4435 | 2.0160 | [100.8335, 103.2229] |
| malvetti_baseline / 32 / 128 / seeded_random / none | 5 | 105.7944 | 0.6213 | [103.6015, 106.3738] |
| malvetti_baseline / 32 / 128 / zero_residual_subspace / none | 5 | 0.1976 | 0.0166 | [0.1964, 0.2138] |

## GPU basis-row speedup versus CPU (x)

| Method / workload | Seeds | Median | IQR | 95% bootstrap CI |
|---|---:|---:|---:|---|
| algorithm3 / 24 / 64 / repeated_prefix / random_pm_one | 5 | 1.5657 | 0.0256 | [1.5225, 1.5849] |
| algorithm3 / 24 / 64 / seeded_random / random_pm_one | 5 | 1.5070 | 0.0281 | [1.4685, 1.5322] |
| algorithm3 / 24 / 64 / zero_residual_subspace / random_pm_one | 5 | 1.9944 | 0.0317 | [1.9567, 2.0228] |
| algorithm3 / 32 / 128 / repeated_prefix / random_pm_one | 5 | 3.2811 | 0.0114 | [3.2410, 3.3320] |
| algorithm3 / 32 / 128 / seeded_random / random_pm_one | 5 | 3.1427 | 0.0544 | [3.0319, 3.1585] |
| algorithm3 / 32 / 128 / zero_residual_subspace / random_pm_one | 5 | 4.5305 | 0.0602 | [4.4467, 4.5434] |
| independent_batched_isometry / 24 / 64 / repeated_prefix / none | 5 | 1.4985 | 0.0439 | [1.4578, 1.5267] |
| independent_batched_isometry / 24 / 64 / seeded_random / none | 5 | 1.4382 | 0.0467 | [1.3991, 1.4810] |
| independent_batched_isometry / 24 / 64 / zero_residual_subspace / none | 5 | 0.0267 | 0.0004 | [0.0264, 0.0283] |
| independent_batched_isometry / 32 / 128 / repeated_prefix / none | 5 | 3.1103 | 0.0135 | [3.1088, 3.1325] |
| independent_batched_isometry / 32 / 128 / seeded_random / none | 5 | 2.9059 | 0.0335 | [2.8410, 2.9557] |
| independent_batched_isometry / 32 / 128 / zero_residual_subspace / none | 5 | 0.0442 | 0.0025 | [0.0429, 0.0480] |
| malvetti_baseline / 24 / 64 / repeated_prefix / none | 5 | 1.8328 | 0.0534 | [1.7804, 1.8503] |
| malvetti_baseline / 24 / 64 / seeded_random / none | 5 | 1.8665 | 0.0190 | [1.8228, 1.8993] |
| malvetti_baseline / 24 / 64 / zero_residual_subspace / none | 5 | 0.0277 | 0.0004 | [0.0264, 0.0292] |
| malvetti_baseline / 32 / 128 / repeated_prefix / none | 5 | 4.3689 | 0.1315 | [4.2762, 4.4943] |
| malvetti_baseline / 32 / 128 / seeded_random / none | 5 | 4.5253 | 0.0555 | [4.3908, 4.8199] |
| malvetti_baseline / 32 / 128 / zero_residual_subspace / none | 5 | 0.0455 | 0.0043 | [0.0416, 0.0538] |

## End-to-end state-preparation compile time (ms)

| Method / workload | Seeds | Median | IQR | 95% bootstrap CI |
|---|---:|---:|---:|---|
| repeated_prefix / random_complex / all_positive | 5 | 1.3224 | 0.0142 | [1.3065, 1.3523] |
| repeated_prefix / random_complex / random_pm_one | 5 | 1.5392 | 0.1524 | [1.4001, 1.7002] |
| repeated_prefix / random_real_positive / all_positive | 5 | 1.1844 | 0.0159 | [1.1520, 1.1935] |
| repeated_prefix / random_real_positive / random_pm_one | 5 | 1.4161 | 0.1268 | [1.2844, 1.5502] |
| repeated_prefix / uniform_real_positive / all_positive | 5 | 1.1994 | 0.0103 | [1.1647, 1.2097] |
| repeated_prefix / uniform_real_positive / random_pm_one | 5 | 1.4141 | 0.1380 | [1.2539, 1.5306] |
| seeded_random / random_complex / all_positive | 5 | 1.2989 | 0.0040 | [1.2113, 1.3158] |
| seeded_random / random_complex / random_pm_one | 5 | 1.4737 | 0.2426 | [1.3903, 1.6973] |
| seeded_random / random_real_positive / all_positive | 5 | 1.1754 | 0.0137 | [1.0753, 1.2012] |
| seeded_random / random_real_positive / random_pm_one | 5 | 1.3691 | 0.2698 | [1.2740, 1.5611] |
| seeded_random / uniform_real_positive / all_positive | 5 | 1.1787 | 0.0038 | [1.0692, 1.1822] |
| seeded_random / uniform_real_positive / random_pm_one | 5 | 1.3368 | 0.2201 | [1.2714, 1.5155] |
| zero_residual_subspace / random_complex / all_positive | 5 | 1.1956 | 0.0109 | [1.1932, 1.2364] |
| zero_residual_subspace / random_complex / random_pm_one | 5 | 1.4088 | 0.1367 | [1.3032, 1.5507] |
| zero_residual_subspace / random_real_positive / all_positive | 5 | 1.0612 | 0.0102 | [1.0476, 1.0646] |
| zero_residual_subspace / random_real_positive / random_pm_one | 5 | 1.2669 | 0.1183 | [1.1562, 1.3989] |
| zero_residual_subspace / uniform_real_positive / all_positive | 5 | 1.0510 | 0.0125 | [1.0290, 1.0811] |
| zero_residual_subspace / uniform_real_positive / random_pm_one | 5 | 1.2639 | 0.1478 | [1.1470, 1.3941] |

The confidence interval is a percentile bootstrap over independent seed-level medians (five seeds per complete group). Repeated timing samples within a seed are summarized first and are not treated as independent problem instances.
- PASS — `authors_artifact_checksum_match`
- PASS — `authors_rust_unit_tests_pass`
- OPEN — `authors_extension_build_and_import_smoke`
- OPEN — `authors_differential_all_costs_match`
- PASS — `cpu_scaling_matrix_complete`
- PASS — `gpu_basis_row_matrix_complete`
- PASS — `end_to_end_statevector_all_pass`
- PASS — `test_suites_pass`
- PASS — `resource_accounting_complete`
- PASS — `end_to_end_resource_accounting_complete`
- PASS — `cuda_probe_pass`
- PASS — `timing_separates_synthesis_from_final_verification`
- PASS — `windows_runner_portable_peak_memory`
- PASS — `distribution_package_verified`

## Output artifacts

- `cpu_scaling.csv`
- `authors_differential.csv`
- `gpu_basis_rows.csv`
- `end_to_end_statevector.csv`
- `resource_accounting.csv`
- `statistical_summary.json`
- `run_manifest.json`
- `workload_inputs.jsonl` (ordered supports, normalized coefficients and sign metadata)
- `machine_manifest.json` (sanitized)
- `closure_status.json`
- per-case logs and raw JSONL ledgers

## Distribution and release

- Repository package verification: PASS
- Local release action: only attempted after this report is finalized; see `closure_status.json`.
- A local Git tag is created only after package verification and all scientific gates pass; no push is performed.

## Reproducibility and limitations

All ordered support rows are stored in `workload_inputs.jsonl`, not merely hashed. The report is specific to the recorded source commit, hardware, Python, CUDA and CuPy versions. No native hardware gate counts, physical depth, T-count or QPU execution are claimed.
The authors' official source is retained unmodified. The compiled local extension is stored under the ignored `reference/authors-artifact/build/` directory and is not included in source releases.
