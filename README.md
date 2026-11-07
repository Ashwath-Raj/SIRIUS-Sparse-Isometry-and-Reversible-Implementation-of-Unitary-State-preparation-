# Sparse Quantum State Preparation — Reproduction Workspace

Research target: Felix Rupprecht and Sabine Wölk, “Sparse quantum state preparation with improved Toffoli cost”, *Quantum* 10, 2208 (2026).

Paper: <https://quantum-journal.org/papers/q-2026-09-10-2208/>
Official research artifact: <https://zenodo.org/records/18234600>

## Phase status

**Phase 1: source audit, workspace initialization, and hardware-probe tooling.**

This package is a Phase 1 bootstrap. It does not yet implement the Malvetti baseline, PUI, or Algorithms 1/3. Those are later roadmap phases and are deliberately not represented as complete.

## Workspace layout

- `reference/sources/`: exact copies of the user-supplied research sources.
- `reference/authors-artifact/`: reserved for the official Zenodo artifact; keep it immutable.
- `candidate_ai/`: reserved for independent candidate code. Do not copy official artifact source here.
- `research-notes/`: source provenance, known source issues, and decisions.
- `environment/`: machine-specific probe output and software inventory.
- `scripts/`: source verification, hardware detection and reference-artifact retrieval helpers.
- `tests/`: lightweight Phase 1 tests.
- `results/`: benchmark output locations for later phases.
- `handoff/`: local Git bundle and source snapshot generated after commits.

## Run on the primary Ubuntu laptop

```bash
python3 scripts/hardware_probe.py --output environment/laptop-hardware.json
python3 -m unittest discover -s tests -v
python3 scripts/verify_sources.py
```

The probe tests CUDA through any available PyTorch, CuPy, or Numba CUDA runtime. It does not equate `nvidia-smi` visibility with a successful CUDA kernel. Install only the backend you intend to use; CUDA libraries are optional at this phase.

For a strict CUDA check (non-zero exit if no CUDA kernel ran):

```bash
python3 scripts/hardware_probe.py --require-cuda --output environment/laptop-hardware.json
```

## Fetch the authors' artifact

```bash
python3 scripts/fetch_reference_artifact.py --output reference/authors-artifact/official-artifact.zip
```

The script verifies the Zenodo-recorded MD5 before extraction. It does not modify any extracted files. Inspect the artifact's README and lockfile warning before installing it. Do not regenerate its `uv.lock`.

## Git policy

Local commits only. Never push, pull, fetch, alter remotes, amend, squash, rebase, or rewrite history. The operator will inspect this candidate and decide when/if to push from their own machine.
