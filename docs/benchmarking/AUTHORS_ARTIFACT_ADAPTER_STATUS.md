# Authors' Reference Artifact Audit & Adapter Status

**Date:** 2026-11-16  
**Artifact Identifier:** Zenodo Record 18234600  
**Artifact Archive:** `reference/authors-artifact/official-artifact.zip`  
**Expected MD5:** `c58634ba415b4e3fb729648460f32ad7` (Verified matching)  
**Extracted Path:** `reference/authors-artifact/source/Code_for_Sparse_quantum_state_preparation_with_improved_Toffoli_cost`  
**License:** Apache-2.0 (source code), CC-BY-4.0 (figures)  

---

## 1. Official Artifact Architecture

The authors' artifact is divided into two primary layers:
1. **Qualtran Bloq Layer (Python):**
   - High-level quantum state preparation circuits represented as Google Qualtran Bloqs:
     - `SparseStatePreparation` (in `sparse_state_preparation/sparse_state_preparation.py`)
     - `IsometryToSubspaceViaBatching` (in `sparse_state_preparation/isometry.py`)
     - `DenseStatePreparationViaQROAM` (in `sparse_state_preparation/dense_state_preparation.py`)
   - Dependencies: `qualtran` (requires installation from git repository `https://github.com/quantumlib/Qualtran`), `attrs`, `rsmf`, and a Jupyter notebook environment.
   - Note on security: The authors explicitly note in their README that Qualtran requires `nbconvert <= 7.16.6`, which has a known CVE (GHSA-xm59-rqc7-hhvf).

2. **Computational Isometry Engine (Rust / C-ABI Extension):**
   - Implemented in Rust under `src/isometry_algorithms/`:
     - `problem.rs`: Batched isometry synthesis and problem partitioning.
     - `tableau.rs`: Tableau representation and column updates.
     - `column.rs`: Bit-column operations.
     - `gates.rs`: Gate definitions and reversible operations.
   - Python C-ABI binding via `pyo3`: `src/lib.rs`.
   - Pre-compiled ABI3 shared object: `_isometry_algorithms.abi3.so`.

---

## 2. Kernel Interface & Entrypoints

The Rust extension exposes two core functions directly to Python:
```python
find_bijection_and_circuit(
    state: np.ndarray[bool, 2D],
    signs: np.ndarray[bool, 1D] | None,
    sub_problem_size: int | None
) -> tuple[list[list[int]], list[tuple[BatchCreationData, BatchZeroingData]]]
```
and:
```python
fast_toffoli_counter(circuit) -> int
```

- **Input Representation:**
  - `state`: Boolean numpy array of shape `(s, n)`, where each row is an $n$-bit computational basis state.
  - `signs`: Boolean numpy array of length $s$, where `True` indicates a $-1$ phase sign.
  - `sub_problem_size`: Optional integer.
- **Output Representation:**
  - `bijection`: Mapping of subspace labels to input rows.
  - `circuit`: Sequence of batch creation and zeroing steps.
  - `fast_toffoli_counter`: Computes the exact paper-accounted Toffoli cost of the generated batched isometry.

---

## 3. SIRIUS Differential Adapter Implementation

SIRIUS implements a clean, isolated adapter in `benchmarking/adapters/authors_adapter.py`:
- Dynamically loads `_isometry_algorithms.abi3.so` from the extracted reference directory without polluting SIRIUS's package namespace.
- Does NOT require installing heavy Qualtran or git-pinned dependencies.
- Converts `SparseStateProblem` instances directly into the required boolean numpy arrays.
- Provides `is_authors_artifact_available()` and `run_authors_reference_isometry()`.
- Verified in `tests/test_authors_adapter.py`: on identical support sets, the authors' Rust kernel Toffoli cost matches SIRIUS's independent batched isometry implementation.

---

## 4. Fallback & Cross-Platform Protection

If running on an operating system or CPU architecture where `_isometry_algorithms.abi3.so` is incompatible (e.g. non-Linux x86_64 without Rust installed), the adapter gracefully reports:
- `available = False`
- `blocked_reason = "Building requires Rust toolchain and maturin: 'maturin develop' or 'uv sync'"`
- Benchmark runner marks `authors_reference_artifact` jobs as `status = "skipped"` with the exact blocked reason recorded, preserving run integrity without crashing.
