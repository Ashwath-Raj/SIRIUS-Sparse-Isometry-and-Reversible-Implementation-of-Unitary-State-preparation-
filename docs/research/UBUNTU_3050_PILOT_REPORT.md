# Ubuntu RTX 3050 Pilot Report

## Run identity and machine

- Run label: `ubuntu3050-pilot-20261118T001500Z` (the suffix is an opaque label, not a timestamp); plan: `sirius-ubuntu-laptop-pilot-v1` version 1.0.0.
- Actual record interval (UTC): `2026-11-17T18:35:23.783631Z` through `2026-11-17T18:35:30.453859Z`.
- Git HEAD: `1aa1991bc65e28e2401a80e5b23bbe27bf8cfa5d`; the working tree was dirty during the pilot. Raw records capture the dirty flag but not a source-diff digest/snapshot, so the exact as-run patch cannot be reconstructed from this pilot evidence alone. The runner now records source diff and untracked-file digests for future runs. The per-run plan and machine manifest are adjacent under `results/manifests/ubuntu-amd-ryzen6600h-rtx3050-laptop/`.
- OS: Linux #43-Ubuntu SMP PREEMPT_DYNAMIC Fri Oct 23 13:25:25 UTC 2026; kernel `7.0.0-43-generic`.
- Python: 3.12.14; CPU: AMD Ryzen 5 6600H with Radeon Graphics (6 physical / 12 logical cores).
- RAM: 15491403776 total bytes; swap: 4294963200 bytes.
- GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU (6442450944 bytes; compute capability 8.6); driver 595.99.02; CUDA compatibility from `nvidia-smi`: 13.2; CuPy runtime 13.2; CuPy 14.2.0; local `nvcc` toolkit: None.

## Attempt and validation results

| Track | Attempts | Completed | Failed | Skipped | Timed out | Invalid | Schema-invalid lines |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paper reproduction | 14 | 14 | 0 | 0 | 0 | 0 | 0 |
| Symmetry extension | 48 | 48 | 0 | 0 | 0 | 0 | 0 |

Seeds: 101 and 211. Widths: n=8,10. Sparsities: s=3,5. The symmetry track used k=n//2, random support, fixed-weight lexicographic support, and fixed-weight seeded-shuffled support. Algorithms were the independent batched-isometry implementation and Malvetti baseline. One end-to-end statevector and one authors-reference run were added in the paper track. The selected design consumed 62/64 allowed attempts.

## Paper reproduction observations

The table reports seed-101 matched candidate and Malvetti construction runs. Construction wall time is one in-process compilation measurement; values are workload-specific and are not a significance test. Resource conventions remain distinct; operation count is not depth.

| n | s | Algorithm | Seed | Construction wall ms | Paper-accounted Toffoli | Coherent Toffoli | Emitted operations | GPU lane |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 3 | independent_batched_isometry | 101 | 0.709449 | 2 | 4 | 16 | passed |
| 8 | 3 | malvetti_baseline | 101 | 0.405498 | 3 | 3 | 8 | passed |
| 8 | 5 | independent_batched_isometry | 101 | 1.074602 | 4 | 8 | 28 | passed |
| 8 | 5 | malvetti_baseline | 101 | 0.901783 | 10 | 10 | 16 | passed |
| 10 | 3 | independent_batched_isometry | 101 | 0.711662 | 2 | 4 | 16 | passed |
| 10 | 3 | malvetti_baseline | 101 | 0.517304 | 3 | 3 | 12 | passed |
| 10 | 5 | independent_batched_isometry | 101 | 1.178253 | 4 | 8 | 28 | passed |
| 10 | 5 | malvetti_baseline | 101 | 0.774369 | 10 | 10 | 20 | passed |

End-to-end exact CPU statevector status: `passed`; fidelity `1.0`, maximum amplitude error `1.1102230246251565e-16`, workspace leakage `3.466673899897024e-33`. Authors reference status: `PASS`; mapping total/injective/row-total checks: `{'mapping_injective': True, 'mapping_rows_total': True, 'mapping_total': True, 'residual_row_behavior': 'not_exposed_by_authors_api'}`. The authors API does not expose primitive gates or residual-row output for independent gate-sequence comparison.

## Symmetry extension paired contrasts

Contrasts below are right-minus-left deltas computed per matched seed, then summarized by the median of the two seed differences for each (n,k,s,algorithm,metric). For family comparisons, random and fixed-weight workloads share dimension, seed strategy, and coefficient/sign generation profile, but are distinct supports and states. For order comparisons, canonical support/amplitude/sign mappings match exactly. `n=2` seed pairs are descriptive and have no confidence intervals.

| Contrast | Algorithm | n | k | s | Metric | Paired seeds | Median delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 3 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 3 | construction_wall_ms | 2 | -0.044737 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 3 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 5 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 5 | construction_wall_ms | 2 | 0.147679 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 10 | 5 | 5 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 3 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 3 | construction_wall_ms | 2 | -0.082423 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 3 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 5 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 5 | construction_wall_ms | 2 | -0.102278 |
| lexicographic_vs_seeded_shuffled | independent_batched_isometry | 8 | 4 | 5 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 3 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 3 | construction_wall_ms | 2 | 0.109738 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 3 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 5 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 5 | construction_wall_ms | 2 | 0.058092 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 10 | 5 | 5 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 3 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 3 | construction_wall_ms | 2 | -0.160517 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 3 | paper_accounted_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 5 | coherent_toffoli | 2 | 0.000000 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 5 | construction_wall_ms | 2 | 0.097069 |
| lexicographic_vs_seeded_shuffled | malvetti_baseline | 8 | 4 | 5 | paper_accounted_toffoli | 2 | 0.000000 |

Observed median deltas vary across width/sparsity and algorithm. The pilot does not establish a general geometry effect or ordering benefit. Prefix and Hamming descriptors and all per-attempt values are in raw records/CSV; the figures visualize individual completed observations.

## GPU basis-row lane

| Track | GPU stages | Status counts | Kernel samples | Median measured kernel ms |
| --- | --- | --- | --- | --- |
| paper_reproduction | 12 | {'passed': 12} | 12 | 1.728403 |
| symmetry_structured_sparse_supports | 48 | {'passed': 48} | 48 | 1.526836 |

All GPU stages applied actual emitted reversible gates to uint64 computational-basis rows and checked exact output parity against the CPU basis-row simulator. This is not GPU circuit construction, complex-amplitude statevector simulation, or hardware execution. Per-job intervals are a single synchronized observation; the first CuPy use can include JIT/cache warm-up, so kernel timings are exploratory and no throughput or speedup claim is made.

## Evidence paths and rerun

- Paper raw: `results/raw/ubuntu-amd-ryzen6600h-rtx3050-laptop/paper_reproduction/ubuntu3050-pilot-20261118T001500Z.jsonl`
- Symmetry raw: `results/raw/ubuntu-amd-ryzen6600h-rtx3050-laptop/extensions/symmetry_structured_sparse_supports/ubuntu3050-pilot-20261118T001500Z.jsonl`
- Machine and plan manifests: `results/manifests/ubuntu-amd-ryzen6600h-rtx3050-laptop/ubuntu3050-pilot-20261118T001500Z_machine_manifest.json`, `ubuntu3050-pilot-20261118T001500Z_plan.json`.
- CSV tables and matched contrasts: `results/tables/ubuntu-amd-ryzen6600h-rtx3050-laptop/.../ubuntu3050-pilot-20261118T001500Z_attempts.csv` and `ubuntu3050-pilot-20261118T001500Z_matched_contrasts.csv`.
- Figures, logs, summaries, checkpoints and per-track reports: matching `results/figures`, `results/logs`, `results/summaries`, `results/checkpoints`, `results/reports` machine/track directories.

```bash
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" SIRIUS_RUN_ID="new-unique-run-id" bash scripts/ubuntu/run_laptop_pilot.sh
PYTHONPATH=candidate_ai/src .venv-ubuntu-3.12/bin/python scripts/summarize_ubuntu_results.py --run-id new-unique-run-id
```

Full Phase 9.1 scaling/stress and the larger symmetry workstation campaign were **NOT_RUN** on this laptop. The full campaign definitions remain separate in `benchmarking/config/phase9_1_benchmark_plan.json` and `benchmarking/config/ubuntu_workstation_campaign_v1.json`.
