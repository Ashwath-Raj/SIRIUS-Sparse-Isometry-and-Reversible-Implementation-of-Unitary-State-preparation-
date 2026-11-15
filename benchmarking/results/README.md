# Benchmark result storage (Phase 9.2 only)

This directory is intentionally empty in Phase 9.1. Do not add fabricated or illustrative measurements.

Phase 9.2 writes immutable raw JSONL/JSON run records under a device-and-date folder, plus summaries generated from those raw records. Keep each machine's raw records separate; merge only after schema validation and provenance checks.

Suggested local-only layout (not committed):

```text
benchmarking/local-runs/                # gitignored in Phase 9.2
  laptop-rtx3050/2026-.../
    machine-manifest.json
    raw-runs.jsonl
    summary.json
    plots/
  dgx-node-alias/2026-.../
    machine-manifest.json
    raw-runs.jsonl
    summary.json
    plots/
```

The committed project contains schemas and templates, not device measurements.
