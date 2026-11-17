# Phase 7.1 acceptance checklist

- [ ] Extract this ZIP into the existing project root. It is additive; it does not overwrite Phase 3–6 source files or the root README.
- [ ] Run `bash scripts/run_phase7_1_tests.sh` (uses the existing `.venv`).
- [ ] Run `bash scripts/run_phase6_tests.sh` as the full existing-suite regression check.
- [ ] Confirm both commands pass; record any CUDA skips separately from Phase 7.1 CPU tests.
- [ ] Inspect `git diff --check` and `git status --short`.
- [ ] Commit only the new Phase 7.1 files with `feat: add Algorithm 3 sign-marker reference model`.
- [ ] Do not push.

Phase 7.1 is accepted only as the sign/marker reference model. Do not mark Algorithm 3 complete until Phase 7.2 gate synthesis and integration pass.
