# Results layout

Generated results live under repository-root `results/`. Each machine uses its own stable machine ID, and each execution has a unique run ID.

```text
results/
  raw/<machine-id>/paper_reproduction/<run-id>.jsonl
  raw/<machine-id>/extensions/symmetry_structured_sparse_supports/<run-id>.jsonl
  summaries/<machine-id>/<track>/
  tables/<machine-id>/<track>/
  figures/<machine-id>/<track>/
  manifests/<machine-id>/
  logs/<machine-id>/
  reports/<machine-id>/<track>/
  checkpoints/<machine-id>/
```

Track A uses the original random-support reproduction family and preserves separate candidate, Malvetti, end-to-end, and eligible authors-reference records. Track B is exploratory and has its own generator and support-order identities. Machine IDs are never aggregated together. Historical tracked Phase 1/2 and Phase 9 repair evidence is retained; generated machine-specific results are not included in source distributions by default.

The summarizer reads only the selected machine's canonical raw directories, validates each record, and reports status counts. Numerical summaries and plots use completed records. Paired extension contrasts are emitted per seed and require matching algorithm, dimensions, seed, coefficient/sign profile and ordering; lexicographic/shuffled pairs additionally share the canonical mathematical-instance digest. Random/fixed-weight supports are matched by design variables and coefficient/sign seed, but are distinct mathematical states. The pilot has two seeds in most strata, so it reports no confidence intervals.
