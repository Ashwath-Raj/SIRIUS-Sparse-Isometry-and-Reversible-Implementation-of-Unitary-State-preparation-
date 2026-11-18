# Benchmark result storage

The schema and runner definitions live in this directory's parent. Measured result evidence is published separately:

- Public campaign report: [docs/research/PUBLIC_BENCHMARK_RESULTS.md](../../docs/research/PUBLIC_BENCHMARK_RESULTS.md)
- Immutable campaign release: https://github.com/Ashwath-Raj/SIRIUS-Sparse-Isometry-and-Reversible-Implementation-of-Unitary-State-preparation-/releases/tag/sirius-ubuntu-rtx3050-campaign-20261117
- Earlier matched smoke raw records and summary: [research/phase9_repair/runs/sirius_repair_validation_20261117/](../../research/phase9_repair/runs/sirius_repair_validation_20261117/)

The release archives include the raw JSONL attempt records, deduplicated analytical tables, plots, manifests, validation logs and SHA-256 checksums. Do not commit the 240 MB closure archive into ordinary Git history; it is distributed as a release asset.
