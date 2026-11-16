# Initial Repository Audit — SIRIUS Project

**Date:** 2026-11-16  
**Auditor:** Senior Quantum Software Engineer & Research Infrastructure Maintainer  
**Repository:** SIRIUS (Sparse Isometry and Reversible Implementation of Unitary State Preparation)  
**Paper Authority:** Felix Rupprecht and Sabine Wölk (2026), *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208 (2026). DOI: [10.22331/q-2026-09-10-2208](https://doi.org/10.22331/q-2026-09-10-2208)  
**Official Artifact:** Zenodo Record 18234600 (MD5: `c58634ba415b4e3fb729648460f32ad7`)

---

## 1. Executive Summary

This audit establishes the pre-refactor baseline for the SIRIUS research repository before beginning repository modernization, structural reorganization, and Phase 9.2 execution.

The repository represents an independent implementation of the Rupprecht & Wölk (2026) sparse quantum state preparation algorithm. The algorithmic implementation spans Phases 1 through 8.2 and the Phase 9.1 benchmark architecture design.

All core quantum algorithms, reversible gate models, tableaux, PUI tree emissions, and state preparation routines are structurally sound and verified:
- **Baseline Test Suite (`candidate_ai/tests`):** 150 passed in 6.99s (100% pass rate).
- **Root Unit Tests (`tests/`):** 9 passed (7 subtests) in 0.18s.
- **Phase 9.1 Benchmark Plan Validator:** PASS (4,050 planned dry-run jobs; 720 smoke-tier jobs).
- **Official Artifact Checksum:** `c58634ba415b4e3fb729648460f32ad7` (Verified matching official archive `reference/authors-artifact/official-artifact.zip`).
- **GPU Hardware & Backend:** NVIDIA GeForce RTX 3050 6GB Laptop GPU detected (Driver 595.99.02, CUDA 13.2). CuPy 14.2.0 installed in `.venv` and verified functional for uint64 basis-row batch transformations.

---

## 2. Existing Workspace Structure

The workspace contains the following top-level directory layout:

| Directory / File | Description | Role / Classification |
|---|---|---|
| `README.md` | Primary project README (partially updated for Phase 9.1) | Authoritative documentation entrypoint candidate |
| `DECISIONS.md`, `HANDOFF.md`, `WORKLOG.md`, `INSTALL_INTO_EMPTY_PROJECT_DIR.md` | Phase 1 historical records at root | Historical records to be archived |
| `PHASE*_ACCEPTANCE_CHECKLIST.md` (Phases 3–9.1) | Phase acceptance checklists (12 files) | Historical records to be archived in `research/archive/phases/` |
| `PHASE*_STARTER_VALIDATION.md` (Phases 3–9.1) | Phase starter validation notes (9 files) | Historical records to be archived in `research/archive/phases/` |
| `PHASE*_README.md` (Phases 7.1, 7.2, 8.1, 8.2, 9.1) | Phase-specific README files (5 files) | Historical records to be archived in `research/archive/phases/` |
| `PHASE*_SHA256SUMS` (Phases 7.1, 7.2, 8.1, 8.2, 9.1) | Phase integrity manifests (5 files) | Historical validation records to be archived |
| `PHASE1_VALIDATION.md`, `PHASE8_COMPLETION_RECORD.md` | Phase milestone records | Historical validation records |
| `candidate_ai/src/sparseprep/` | Core Python package source | Research-critical executable algorithm source |
| `candidate_ai/tests/` | Algorithm test suite | Research-critical regression tests (150 tests) |
| `candidate_ai/README.md` | Subdirectory notes | Secondary documentation |
| `benchmarking/` | Phase 9.1 benchmark architecture, schemas, and plan | Benchmark infrastructure (canonical) |
| `benchmarks/` | Empty placeholder with `.gitkeep` | Obsolete placeholder (to be safely removed) |
| `docs/` | Architecture, overview, and Phase 9.1 design documents | Modern documentation |
| `environment/` | Agent environment JSON and software versions | Local environment manifests |
| `handoff/` | Phase 1 Git bundle and tarball | Historical snapshot |
| `reference/authors-artifact/` | Official authors' zip and extracted source | External reference artifact |
| `reference/sources/` | Paper PDF and implementation guide | External reference literature |
| `research-notes/` | Phase-by-phase design decision notes | Historical research documentation |
| `results/` | Raw results, figures, and summary notes | Output directory |
| `scripts/` | Shell and Python helper scripts | Validation and operational tools |
| `tests/` | Root-level hardware probe and design tests | Supporting integration tests (9 tests) |

---

## 3. Important Source Modules (`candidate_ai/src/sparseprep/`)

| Module | Core Responsibility | Public Entrypoints & Invariants |
|---|---|---|
| `model.py` | Validated problem model | `SparseStateProblem`, `ProblemValidationError`, `bitstring_to_int`, `int_to_bitstring`. Invariants: big-endian bitstrings, distinct support, normalized complex coefficients, independent $\pm 1$ sign metadata. |
| `gates.py` | Reversible gate intermediate representation (IR) | `X`, `CX`, `MCX`, `CMX`, `Toffoli`, `SWAP`, `NegativeControlToffoli`, `PUIMacro`, `invert_sequence`. Invariants: self-inverses, control polarity, exact gate commutation models. |
| `simulator.py` | Exact CPU computational-basis simulation | `apply_gate`, `simulate_basis_state`, `simulate_support`. Simulates exact reversible basis transformations without materializing statevector. |
| `tableau.py` | Tableau tracking representation | `Tableau`, `TableauRow`. Invariants: stable row IDs, separate phase metadata, distinct row mappings. |
| `resources.py` | Logical resource accounting | `ResourceCounts`, `count_emitted_resources`. Distinguishes emitted IR gate counts from paper-accounted Toffoli costs. |
| `malvetti_baseline.py` | Sequential Malvetti et al. isometry baseline | `run_malvetti_baseline`, `MalvettiResult`, `MalvettiStep`. Invariants: zeroes non-subspace suffix using $s(\ell - 1)$ upper bound. |
| `pui.py` | Partial Unary Iteration (PUI) interval plans and cost models | `PUIPlan`, `build_pui_plan`, `mcx_ladder_cost`. Invariants: unrestricted and restricted PUI cost models matching paper Equations 7 and 8. |
| `pui_tree.py` | Optimized reversible PUI tree circuit emitter | `compile_pui_tree`, `PUITreeCircuit`. Invariants: $2^w - 2$ Toffolis for full unary iteration, clean ancilla uncomputation, depth-reused ancillas $\le w-1$. |
| `batched_isometry.py` | Independent batched isometry construction | `run_batched_isometry`, `BatchedIsometryResult`, `BatchedIsometryResources`. Invariants: support injectivity, zero residual suffix, forward-inverse round-trip. |
| `algorithm3.py` | Algorithm 3 sign- and marker-aware construction | `run_algorithm3`, `Algorithm3Result`, `Algorithm3Event`. Invariants: marker wire tracking, positive/negative support separation, uncomputation. |
| `algorithms/phase_fixing.py` | Signed tableau model and phase-fixing logic | `PhaseFixingPlan`, `compute_phase_fixing_plan`. Invariants: visit-partitioning, sign assignment correctness. |
| `phase_synthesis.py` | Real-sign diagonal phase oracle | `compile_real_sign_phase_oracle`, `PhaseOracleCircuit`. Invariants: ladder ancilla uncomputation, exact $-1$ phase placement on negative labels. |
| `state_preparation.py` | Complete logical sparse-state preparation pipeline | `compile_sparse_state_preparation`, `prepare_sparse_state`, `SparseStatePreparationCircuit`. Combines dense compact loader, complex phase rotations, inverse isometry, and marker uncomputation. Includes exact statevector verifier (bounded by configurable qubit cap). |
| `support_generators.py` | Deterministic structural workload generators | `random_support`, `random_problem`, `support_inside_subspace`, `support_with_repeated_prefix`, `partial_final_batch_problem`. |
| `backends/cupy_simulator.py` | Optional GPU basis-state row batch simulator | `CuPyBasisRowSimulator`, `simulate_basis_batch_gpu`. Operates on batches of `uint64` computational basis words ($n \in [1, 63]$). NOT a statevector simulator. |

---

## 4. Baseline Test & Verification Results

Executed locally on 2026-11-16:

1. **Algorithm Regression Suite (`candidate_ai/tests`):**
   - Command: `PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest candidate_ai/tests -v`
   - Result: **150 passed in 6.99s**
   - Breakdown:
     - `test_algorithm3.py`: 8 passed
     - `test_batched_isometry.py`: 12 passed
     - `test_cupy_parity.py`: 2 passed (both CPU/GPU parity tests executed on RTX 3050 GPU)
     - `test_gates.py`: 11 passed
     - `test_malvetti_baseline.py`: 10 passed
     - `test_model.py`: 16 passed
     - `test_phase_fixing.py`: 13 passed
     - `test_phase_synthesis_8_1.py`: 14 passed
     - `test_pui.py`: 20 passed
     - `test_pui_tree.py`: 16 passed
     - `test_state_preparation_8_2.py`: 13 passed
     - `test_support_generators.py`: 5 passed
     - `test_tableau.py`: 3 passed
   - Note: Previous report stated "148 passed, 2 skipped" due to lack of CUDA in the earlier container. In the present environment, CuPy is functional and all 150 tests pass.

2. **Root Supporting Tests (`tests/`):**
   - Command: `./.venv/bin/pytest tests -v`
   - Result: **9 passed, 7 subtests passed in 0.18s**
   - Breakdown:
     - `test_artifact_fetcher.py`: 2 passed
     - `test_hardware_probe.py`: 3 passed
     - `test_phase9_1_design.py`: 4 passed (with 7 subtests)

3. **Phase 9.1 Benchmark Plan Validation:**
   - Full Plan: `python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json`
     - Status: **PASS**
     - Planned jobs: 4,050
     - Tiers: smoke, scaling, stress
   - Smoke Tier Manifest: `python scripts/phase9_1_validate.py --plan benchmarking/config/phase9_1_benchmark_plan.json --tier smoke --emit-manifest /tmp/sirius-smoke-plan.json`
     - Status: **PASS**
     - Planned jobs: 720
     - Manifest emitted: `/tmp/sirius-smoke-plan.json`

4. **Official Reference Artifact Verification:**
   - File: `reference/authors-artifact/official-artifact.zip`
   - MD5: `c58634ba415b4e3fb729648460f32ad7`
   - Match: **EXACT MATCH** with Zenodo record 18234600.

---

## 5. Duplicate or Redundant Documentation Analysis

The repository root currently contains 28 phase-specific files from earlier sprints:
- `PHASE1_VALIDATION.md`
- `PHASE3_ACCEPTANCE_CHECKLIST.md`, `PHASE3_STARTER_VALIDATION.md`
- `PHASE4_ACCEPTANCE_CHECKLIST.md`, `PHASE4_STARTER_VALIDATION.md`
- `PHASE5_ACCEPTANCE_CHECKLIST.md`, `PHASE5_STARTER_VALIDATION.md`, `PHASE5_TREE_ACCEPTANCE_CHECKLIST.md`
- `PHASE6_ACCEPTANCE_CHECKLIST.md`, `PHASE6_STARTER_VALIDATION.md`
- `PHASE7_1_ACCEPTANCE_CHECKLIST.md`, `PHASE7_1_README.md`, `PHASE7_1_SHA256SUMS`, `PHASE7_1_STARTER_VALIDATION.md`
- `PHASE7_2_ACCEPTANCE_CHECKLIST.md`, `PHASE7_2_README.md`, `PHASE7_2_SHA256SUMS`, `PHASE7_2_STARTER_VALIDATION.md`
- `PHASE8_1_ACCEPTANCE_CHECKLIST.md`, `PHASE8_1_README.md`, `PHASE8_1_SHA256SUMS`, `PHASE8_1_STARTER_VALIDATION.md`
- `PHASE8_2_ACCEPTANCE_CHECKLIST.md`, `PHASE8_2_README.md`, `PHASE8_2_SHA256SUMS`, `PHASE8_2_STARTER_VALIDATION.md`
- `PHASE8_COMPLETION_RECORD.md`
- `PHASE9_1_ACCEPTANCE_CHECKLIST.md`, `PHASE9_1_README.md`, `PHASE9_1_SHA256SUMS`, `PHASE9_1_STARTER_VALIDATION.md`
- `DECISIONS.md`, `HANDOFF.md`, `WORKLOG.md`, `INSTALL_INTO_EMPTY_PROJECT_DIR.md`

**Findings & Plan:**
- None of these files should be deleted (non-negotiable rule 0.3).
- They represent historical sprint handoffs and should be archived in:
  - `research/archive/phases/` (phase acceptance checklists, starter validations, phase readmes, phase checksums)
  - `research/decisions/` (decisions log)
  - `research/validation/` (validation records)
- Root `README.md` must be rewritten as the single, authoritative entrypoint for the SIRIUS research package.
- `docs/` should be structured cleanly into `architecture/`, `methodology/`, `benchmarking/`, and `development/`.

---

## 6. Packaging & Installation Deficiencies

1. **Missing Root `pyproject.toml`:**
   - No standard Python packaging metadata exists at root.
   - The project cannot currently be installed via `pip install -e .` or `pip install -e ".[dev]"`.
   - Running tests requires manually prefixing `PYTHONPATH=candidate_ai/src`.

2. **Incomplete Public Export Contract:**
   - Rule 0.2 requires:
     ```python
     from sparseprep import (
         SparseStateProblem,
         run_malvetti_baseline,
         run_batched_isometry,
         run_algorithm3,
         compile_sparse_state_preparation,
         prepare_sparse_state,
     )
     ```
   - In the existing `candidate_ai/src/sparseprep/__init__.py`, `run_malvetti_baseline` was not imported into `sparseprep`'s top-level namespace, causing `from sparseprep import run_malvetti_baseline` to fail.

3. **Dependency Classification:**
   - Core runtime dependencies: `numpy>=1.24.0`.
   - Dev/Testing dependencies: `pytest>=8.0.0`, `jsonschema>=4.19.0`.
   - Optional GPU dependencies: `cupy` (e.g. `cupy-cuda13x` or matching user's CUDA driver). Must remain optional.

---

## 7. Benchmarking Deficiencies & Phase 9.2 Requirements

1. **Lack of Executable Runners:**
   - `benchmarking/` contains configuration, metrics catalog, and schemas, but NO runners or adapters.
   - Scripts like `phase9_1_validate.py` are strictly dry-run tools that explicitly avoid running benchmarks.
   - Phase 9.2 requires an executable, robust runner (`benchmarking/runners/run_benchmarks.py`) supporting:
     - Process isolation / timeout management.
     - Deterministic workload generation matching Phase 9.1 plan.
     - Separation of compilation time, memory measurement, and GPU batch throughput.
     - Generation of validated, immutable JSONL raw records.

2. **Environment Probe:**
   - Needs a clean, sanitized probe (`benchmarking/runners/environment_probe.py`) that captures CPU, RAM, OS, Python, and optional GPU device details without crashing on systems lacking NVIDIA hardware or `nvidia-smi`.

3. **Statistical Analysis & Summaries:**
   - Need an aggregation tool (`benchmarking/analysis/`) that groups records, computes median, IQR, min, max, and 95% bootstrap confidence intervals across independent seeds.

4. **Authors' Reference Artifact Adapter Status:**
   - The authors' artifact in `reference/authors-artifact/source/...` is built on Qualtran Bloqs and a Rust extension (`_isometry_algorithms`).
   - It requires external dependencies (`qualtran`, `attrs`, `rsmf`, Rust `maturin`).
   - A dedicated adapter must be designed to interface with it, or its blocked state must be cleanly documented with exact technical details per Rule 8.1.

---

## 8. Technical Risks

1. **GPU Boundary Clarification:**
   - SIRIUS's CuPy backend performs batched `uint64` row manipulations for $n \in [1, 63]$.
   - It is NOT a complex statevector simulator, NOT a GPU implementation of the isometry synthesis, and NOT multi-GPU distributed.
   - Documentation and benchmark runners must strictly isolate and label this distinction.

2. **Statevector Simulation Memory Limits:**
   - Full complex statevector verification in `state_preparation.py` allocates $2^n$ complex numbers.
   - Default cap is $n \le 20$ (approx. 16 MB).
   - Any statevector verification must be guarded by this cap to prevent OOM errors during benchmarking.

3. **Authors' Reference Artifact Isolation:**
   - The authors' package source should never be imported directly into the `sparseprep` namespace.
   - It must remain in `reference/` and only be accessed via an external differential adapter if compatible.

---

## 9. Recommended Target Structure & Next Steps

Target structure matches Part 3:
- Archive historical phase markdown files into `research/archive/phases/`.
- Organize current docs into `docs/architecture/`, `docs/methodology/`, `docs/benchmarking/`, `docs/development/`.
- Introduce modern `pyproject.toml` supporting editable install.
- Export `run_malvetti_baseline` in `sparseprep/__init__.py`.
- Remove empty `benchmarks/` placeholder.
- Implement Phase 9.2 environment probe, benchmark runner, and analysis tools.
- Set up GitHub Actions CI workflow for reproducible CPU-side testing.

---
*Audit Completed Successfully. Baseline established.*
