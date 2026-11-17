# Phase 1 handoff

## What is included

- Isolated research-source copies in `reference/sources/`.
- Hardware probe supporting optional PyTorch, CuPy and Numba CUDA checks.
- Source SHA-256 manifest generator.
- Official Zenodo artifact fetcher with record MD5 verification.
- Lightweight unit tests for hardware probe parsing.
- Phase 1 source audit, decisions, worklog and validation notes.

## Important incomplete item

The official Zenodo ZIP is not included because the build container could not resolve `zenodo.org`. Fetch it on Ubuntu:

```bash
python3 scripts/fetch_reference_artifact.py --output reference/authors-artifact/official-artifact.zip
```

The user RTX 3050 CUDA check also remains pending:

```bash
python3 scripts/hardware_probe.py --require-cuda --output environment/laptop-hardware.json
```

## Recover from Git bundle

If `phase-01.bundle` is included, clone all bundled history with:

```bash
git clone handoff/phase-01.bundle "Sparse Quantum State Preperation"
cd "Sparse Quantum State Preperation"
git status --short --branch
git log --oneline --decorate -10
```

No remote is configured and no push has been performed.

## Local phase-acceptance checklist

- [ ] Source files/hashes are correct.
- [ ] Official artifact downloaded and MD5 verified.
- [ ] `python3 -m unittest discover -s tests -v` passes.
- [ ] `scripts/hardware_probe.py --require-cuda` passes on the RTX 3050.
- [ ] User inspected all commits and changes.

Phase 2 should not begin until the operator accepts this handoff and authorizes it.
