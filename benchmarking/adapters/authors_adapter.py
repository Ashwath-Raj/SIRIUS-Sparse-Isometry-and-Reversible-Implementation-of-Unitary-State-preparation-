"""Adapter for Rupprecht & Wölk (2026) authors' official reference artifact.

Interfaces with the authors' compiled Rust kernel (_isometry_algorithms)
for finding the batched isometry and evaluating paper-accounted Toffoli cost.
Kept strictly isolated from sparseprep core.
"""
from __future__ import annotations

import importlib.util
import hashlib
from functools import lru_cache
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


class AuthorsReferenceUnsupportedInput(ValueError):
    """The official kernel has a narrower input domain than SparseStateProblem."""


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


@lru_cache(maxsize=1)
def get_reference_artifact_sha256() -> str | None:
    archive = AUTHORS_ARTIFACT_SRC.parents[3] / "official-artifact.zip"
    return hashlib.sha256(archive.read_bytes()).hexdigest() if archive.is_file() else None


def get_authors_artifact_status() -> dict[str, Any]:
    mod, reason = _load_authors_rust_extension()
    archive = AUTHORS_ARTIFACT_SRC.parents[3] / "official-artifact.zip"
    digest = get_reference_artifact_sha256()
    expected_md5 = "c58634ba415b4e3fb729648460f32ad7"
    archive_md5 = None
    if archive.is_file():
        md5 = hashlib.md5()
        md5.update(archive.read_bytes())
        archive_md5 = md5.hexdigest()
    artifact_integrity = "verified" if archive_md5 == expected_md5 else "missing_or_digest_mismatch"
    reference_status = (
        "BLOCKED_ARTIFACT" if artifact_integrity != "verified"
        else "BLOCKED_BUILD" if mod is None
        else "PASS"
    )
    return {
        "available": mod is not None,
        "reference_status": reference_status,
        "blocked_reason": reason,
        "artifact_path": str(AUTHORS_ARTIFACT_SRC),
        "artifact_sha256": digest,
        "artifact_md5": archive_md5,
        "artifact_integrity": artifact_integrity,
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
    if problem.s < 2 or problem.residual_width < 1:
        raise AuthorsReferenceUnsupportedInput(
            "authors' Rust isometry kernel requires s >= 2 and at least one residual wire "
            f"(got n={problem.n}, s={problem.s}, residual_width={problem.residual_width})"
        )

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
    raw_cost = int(toffoli_cost)
    counter_status = "valid"
    reported_cost: int | None = raw_cost
    if raw_cost > sys.maxsize:
        # The official Rust source uses `next_power_of_two() - 2`; for a
        # zero-operation bucket this underflows usize and Python receives a
        # huge wrapped count. Preserve the raw value, never present it as cost.
        counter_status = "suspected_usize_underflow"
        reported_cost = None
    mapping = tuple((int(label), int(row)) for label, row in bijection)
    labels = [label for label, _ in mapping]
    rows = [row for _, row in mapping]
    if len(mapping) != problem.s or sorted(rows) != list(range(problem.s)):
        raise RuntimeError("authors' reference returned a non-total row mapping")
    if len(set(labels)) != len(labels) or any(label < 0 or label >= (1 << problem.ell) for label in labels):
        raise RuntimeError("authors' reference returned a non-injective or out-of-range compact-label mapping")

    return {
        "bijection": mapping,
        "circuit_batches_count": len(circuit),
        "paper_accounted_toffoli": reported_cost,
        "paper_accounted_toffoli_raw": raw_cost,
        "resource_count_status": counter_status,
        "mapping_status": "passed",
        "artifact_status": "verified",
        "reference_status": "PASS",
    }
