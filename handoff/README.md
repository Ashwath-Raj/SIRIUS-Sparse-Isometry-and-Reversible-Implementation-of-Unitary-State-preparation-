# Handoff area

Generated handoff artifacts (Git bundles, source archives, checksums and commit logs) are intentionally not committed into the repository. Use:

```bash
scripts/create_phase_handoff.sh 01
```

The resulting directory is placed alongside the repository unless an explicit output directory is supplied. The bundle is local-only; no remote is contacted.
