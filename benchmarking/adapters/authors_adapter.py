"""Adapter for Rupprecht & Wölk (2026) authors' official reference artifact.

Interfaces with the authors' compiled Rust kernel (_isometry_algorithms)
for finding the batched isometry and evaluating paper-accounted Toffoli cost.
Kept strictly isolated from sparseprep core.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

import numpy as np

from sparseprep import SparseStateProblem

AUTHORS_ARTIFACT_SRC = (
    Path(__file__).resolve().parents[2]
    / "reference"
    / "authors-artifact"
    / "source"
    / "Code_for_Sparse_quantum_state_preparation_with_improved_Toffoli_cost"
    / "src"
    / "sparse_state_preparation"
)

_RUST_MODULE: Any = None
_LOAD_ATTEMPTED = False
_BLOCK_REASON: str | None = None


def _load_authors_rust_extension() -> tuple[Any, str | None]:
    global _RUST_MODULE, _LOAD_ATTEMPTED, _BLOCK_REASON
    if _LOAD_ATTEMPTED:
        return _RUST_MODULE, _BLOCK_REASON
    _LOAD_ATTEMPTED = True

    if not AUTHORS_ARTIFACT_SRC.exists():
        _BLOCK_REASON = f"Authors artifact directory not found at {AUTHORS_ARTIFACT_SRC}"
        return None, _BLOCK_REASON

    str_path = str(AUTHORS_ARTIFACT_SRC)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

    try:
        import _isometry_algorithms  # type: ignore
        _RUST_MODULE = _isometry_algorithms
        _BLOCK_REASON = None
        return _RUST_MODULE, None
    except Exception as exc:
        _RUST_MODULE = None
        _BLOCK_REASON = (
            f"Failed to load _isometry_algorithms: {type(exc).__name__}: {exc}. "
            "Building requires Rust toolchain and maturin: 'maturin develop' or 'uv sync'."
        )
        return None, _BLOCK_REASON


def is_authors_artifact_available() -> bool:
    mod, _ = _load_authors_rust_extension()
    return mod is not None


def get_authors_artifact_status() -> dict[str, Any]:
    mod, reason = _load_authors_rust_extension()
    return {
        "available": mod is not None,
        "blocked_reason": reason,
        "artifact_path": str(AUTHORS_ARTIFACT_SRC),
    }


def run_authors_reference_isometry(
    problem: SparseStateProblem,
    sub_problem_size: int | None = None,
) -> dict[str, Any]:
    """Executes the authors' official Rust isometry construction.

    Parameters
    ----------
    problem : SparseStateProblem
        Input sparse-state problem.
    sub_problem_size : int | None
        Optional sub-problem size parameter for the authors' partitioner.

    Returns
    -------
    dict[str, Any]
        Dictionary with 'bijection', 'circuit_batches_count', and 'paper_accounted_toffoli'.
    """
    mod, reason = _load_authors_rust_extension()
    if mod is None:
        raise RuntimeError(f"Authors' reference artifact is unavailable: {reason}")

    # Build 2-D numpy bool array (shape s x n)
    state_arr = np.array(
        [[bit == "1" for bit in bitstr] for bitstr in problem.support],
        dtype=bool,
    )

    signs_arr: np.ndarray | None = None
    if problem.signs is not None:
        # In authors' Rust kernel, true indicates negative sign (-1)
        signs_arr = np.array([s == -1 for s in problem.signs], dtype=bool)

    bijection, circuit = mod.find_bijection_and_circuit(state_arr, signs_arr, sub_problem_size)
    toffoli_cost = mod.fast_toffoli_counter(circuit)

    return {
        "bijection": bijection,
        "circuit_batches_count": len(circuit),
        "paper_accounted_toffoli": int(toffoli_cost),
    }
