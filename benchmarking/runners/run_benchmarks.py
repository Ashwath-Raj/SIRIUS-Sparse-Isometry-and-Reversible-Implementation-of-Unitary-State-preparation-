"""Automated, reproducible device-local benchmark runner for SIRIUS (Phase 9.2).

Executes workloads defined in Phase 9.1 plan, enforces process isolation and timeouts,
captures wall/CPU timing, memory, logical resources, correctness, and optional CuPy GPU lane,
and emits immutable schema-validated JSONL records.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import random
import resource
import sys
import time
from typing import Any

from sparseprep import (
    ProblemValidationError,
    SparseStateProblem,
    ceil_log2_positive,
    compile_sparse_state_preparation,
    prepare_sparse_state,
    random_support,
    run_algorithm3,
    run_batched_isometry,
    run_malvetti_baseline,
    support_inside_subspace,
    support_with_repeated_prefix,
)
from sparseprep.simulator import simulate_basis_state

from .environment_probe import get_git_commit, get_git_diff_sha256, get_git_dirty, probe_run_environment

RUN_RECORD_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "run-record.schema.json"
DEFAULT_PLAN_PATH = Path(__file__).resolve().parents[1] / "config" / "phase9_1_benchmark_plan.json"
STATEVECTOR_MAX_QUBITS_DEFAULT = 20
STATEVECTOR_ATOL_DEFAULT = 2e-9


def compute_support_hash(support: tuple[str, ...], n: int | None = None) -> str:
    """Hash the exact ordered support, with width and unambiguous JSON framing."""
    from sparseprep import ProblemValidationError, SparseStateProblem

    rows = tuple(support)
    if not rows:
        raise ProblemValidationError("support must contain at least one basis state")
    width = len(rows[0]) if n is None else n
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ProblemValidationError("register width must be a positive integer")
    SparseStateProblem(n=width, support=rows)
    payload = json.dumps(
        {"identity_version": "ordered-support-v2", "n": width, "support": rows},
        ensure_ascii=True, separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def compute_workload_identity(
    *, n: int, support: tuple[str, ...], coefficients: tuple[complex, ...],
    signs: tuple[int, ...], support_family: str, coefficient_family: str,
    sign_profile: str, seed: int, generator_version: str = "0.9.2",
    workload_parameters: dict[str, Any] | None = None,
    algorithm_configuration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return versioned, deterministic identity metadata for a complete workload."""
    support_sha256 = compute_support_hash(support, n)
    payload = {
        "identity_version": "sirius-workload-v1", "n": n,
        "ordered_support": list(support), "support_sha256": support_sha256,
        "coefficients": [[float(c.real), float(c.imag)] for c in coefficients],
        "coefficient_family": coefficient_family, "signs": list(signs),
        "sign_profile": sign_profile, "support_family": support_family,
        "generator_version": generator_version, "seed": seed,
        "workload_parameters": workload_parameters or {},
        "algorithm_configuration": algorithm_configuration or {},
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {**payload, "sha256": digest}


def generate_coefficients(s: int, family: str, seed: int) -> tuple[complex, ...]:
    if family == "uniform_real_positive":
        val = 1.0 / math.sqrt(s)
        return tuple(complex(val, 0.0) for _ in range(s))
    elif family == "random_real_positive":
        rng = random.Random(seed + 1000)
        raw = [rng.uniform(0.1, 1.0) for _ in range(s)]
        norm = math.sqrt(sum(r * r for r in raw))
        return tuple(complex(r / norm, 0.0) for r in raw)
    elif family == "random_complex":
        rng = random.Random(seed + 2000)
        raw_mags = [rng.uniform(0.1, 1.0) for _ in range(s)]
        norm = math.sqrt(sum(r * r for r in raw_mags))
        coeffs = []
        for r in raw_mags:
            theta = rng.uniform(0.0, 2.0 * math.pi)
            coeffs.append(complex((r / norm) * math.cos(theta), (r / norm) * math.sin(theta)))
        return tuple(coeffs)
    else:
        raise ValueError(f"Unknown coefficient family: {family}")


def generate_signs(s: int, profile: str, seed: int) -> tuple[int, ...]:
    if profile == "all_positive":
        return tuple(1 for _ in range(s))
    elif profile == "random_pm_one":
        rng = random.Random(seed + 3000)
        return tuple(rng.choice((-1, 1)) for _ in range(s))
    else:
        raise ValueError(f"Unknown sign profile: {profile}")


def generate_support(n: int, s: int, family: str, seed: int) -> tuple[str, ...]:
    ell = ceil_log2_positive(s)
    if family == "seeded_random":
        return random_support(n, s, seed)
    elif family == "zero_residual_subspace":
        prob = support_inside_subspace(n, s, seed)
        return prob.support
    elif family == "repeated_prefix":
        residual = n - ell
        if residual < 1 or s > (1 << residual):
            raise ValueError(f"repeated_prefix requires residual >= 1 and s <= 2**(n-ell); got n={n}, s={s}, ell={ell}")
        prob = support_with_repeated_prefix(n, s, seed)
        return prob.support
    else:
        raise ValueError(f"Unknown support family: {family}")


def _execute_compile_worker(
    algorithm_id: str,
    n: int,
    s: int,
    support: tuple[str, ...],
    coefficients: tuple[complex, ...],
    signs: tuple[int, ...],
    repetitions: int,
    warmups: int,
    qubit_cap: int,
) -> dict[str, Any]:
    """Isolated child worker function executing compilation and verification."""
    problem = SparseStateProblem(
        n=n,
        support=support,
        coefficients=coefficients,
        signs=signs,
    )

    # 1. Warm-ups
    for _ in range(warmups):
        if algorithm_id == "independent_batched_isometry":
            _ = run_batched_isometry(problem)
        elif algorithm_id == "malvetti_baseline":
            _ = run_malvetti_baseline(problem)
        elif algorithm_id == "end_to_end_state_preparation":
            _ = compile_sparse_state_preparation(problem)
        elif algorithm_id == "authors_reference_artifact":
            from benchmarking.adapters.authors_adapter import run_authors_reference_isometry
            _ = run_authors_reference_isometry(problem)
        else:
            raise ValueError(f"Unsupported algorithm_id: {algorithm_id}")

    # 2. Measured repetitions
    wall_samples_ms: list[float] = []
    cpu_samples_ms: list[float] = []
    last_res: Any = None

    for _ in range(repetitions):
        t0_wall = time.perf_counter_ns()
        t0_cpu = time.process_time_ns()

        if algorithm_id == "independent_batched_isometry":
            last_res = run_batched_isometry(problem)
        elif algorithm_id == "malvetti_baseline":
            last_res = run_malvetti_baseline(problem)
        elif algorithm_id == "end_to_end_state_preparation":
            last_res = compile_sparse_state_preparation(problem)
        elif algorithm_id == "authors_reference_artifact":
            from benchmarking.adapters.authors_adapter import run_authors_reference_isometry
            last_res = run_authors_reference_isometry(problem)

        t1_cpu = time.process_time_ns()
        t1_wall = time.perf_counter_ns()

        wall_samples_ms.append((t1_wall - t0_wall) / 1e6)
        cpu_samples_ms.append((t1_cpu - t0_cpu) / 1e6)

    # Median timing
    wall_samples_ms.sort()
    cpu_samples_ms.sort()
    mid = len(wall_samples_ms) // 2
    compile_wall_ms = wall_samples_ms[mid]
    compile_cpu_ms = cpu_samples_ms[mid]

    # Peak resident set size (Linux ru_maxrss is in KiB)
    rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024

    # Extract logical resources
    resources: dict[str, Any] = {
        "logical_qubits": None,
        "clean_ancillas": None,
        "paper_accounted_toffoli": None,
        "coherent_toffoli": None,
        "emitted_toffoli_ir": None,
        "logical_depth": None,
        "emitted_operation_count": None,
        "native_gate_count": None,
        "t_count": None,
        "resource_scope": "isometry_only",
        "dense_loader_emitted_toffoli": None,
        "sign_oracle_emitted_toffoli": None,
        "inverse_isometry_emitted_toffoli": None,
        "marker_cleanup_emitted_toffoli": None,
        "end_to_end_emitted_toffoli_ir": None,
    }

    correctness: dict[str, Any] = {
        "statevector_status": "not_applicable",
        "fidelity": None,
        "maximum_amplitude_error": None,
        "outside_support_probability": None,
        "workspace_leakage_probability": None,
        "inverse_round_trip_error": 0.0,
    }

    if algorithm_id == "independent_batched_isometry":
        r = last_res.resources
        anc_count = len(last_res.ancilla_wires)
        resources["paper_accounted_toffoli"] = r.total_paper_accounted_toffolis
        resources["coherent_toffoli"] = r.total_coherent_toffolis
        resources["emitted_toffoli_ir"] = sum(
            1 for g in last_res.forward_gates if type(g).__name__ in ("Toffoli", "NegativeControlToffoli")
        )
        resources["clean_ancillas"] = r.max_clean_ancillas_used
        resources["logical_qubits"] = n + anc_count
        resources["emitted_operation_count"] = len(last_res.forward_gates)

        # Invariant check: round-trip on all basis inputs
        for bitstr in support:
            state_in = bitstr + ("0" * anc_count)
            fwd = simulate_basis_state(state_in, last_res.forward_gates)
            rev = simulate_basis_state(fwd, last_res.inverse_gates)
            if rev[:n] != bitstr:
                correctness["inverse_round_trip_error"] = 1.0
                break

    elif algorithm_id == "malvetti_baseline":
        r = last_res.resources
        anc_count = r.clean_ancillas
        resources["paper_accounted_toffoli"] = r.toffoli_count
        resources["coherent_toffoli"] = r.toffoli_count
        resources["clean_ancillas"] = anc_count
        resources["logical_qubits"] = n + anc_count
        resources["emitted_toffoli_ir"] = sum(
            1 for g in last_res.forward_gates if type(g).__name__ in ("Toffoli", "NegativeControlToffoli")
        )
        resources["emitted_operation_count"] = len(last_res.forward_gates)

        # Invariant check
        for bitstr in support:
            state_in = bitstr + ("0" * anc_count)
            fwd = simulate_basis_state(state_in, last_res.forward_gates)
            rev = simulate_basis_state(fwd, last_res.inverse_gates)
            if rev[:n] != bitstr:
                correctness["inverse_round_trip_error"] = 1.0
                break

    elif algorithm_id == "end_to_end_state_preparation":
        r = last_res.resources
        resources["resource_scope"] = "end_to_end; paper-accounted count is isometry component only"
        resources["paper_accounted_toffoli"] = r.algorithm3_paper_accounted_toffolis
        resources["coherent_toffoli"] = r.algorithm3_coherent_toffolis
        resources["clean_ancillas"] = r.algorithm3_clean_ancillas + r.phase_clean_ancillas
        resources["logical_qubits"] = r.total_qubits
        resources["emitted_toffoli_ir"] = r.total_toffolis
        resources["dense_loader_emitted_toffoli"] = r.dense_loader.toffoli
        resources["sign_oracle_emitted_toffoli"] = r.sign_oracle.toffoli
        resources["inverse_isometry_emitted_toffoli"] = r.inverse_isometry.toffoli
        resources["marker_cleanup_emitted_toffoli"] = r.marker_cleanup.toffoli
        resources["end_to_end_emitted_toffoli_ir"] = r.total_toffolis
        resources["emitted_operation_count"] = r.total_operations

        # Exact statevector validation if within cap
        if r.total_qubits <= qubit_cap:
            try:
                _, metrics = prepare_sparse_state(
                    problem, max_statevector_qubits=qubit_cap,
                    atol=STATEVECTOR_ATOL_DEFAULT,
                )
                correctness["statevector_status"] = "passed"
                correctness["fidelity"] = float(metrics.fidelity)
                correctness["maximum_amplitude_error"] = float(metrics.maximum_amplitude_error)
                correctness["outside_support_probability"] = float(metrics.outside_support_probability)
                correctness["workspace_leakage_probability"] = float(metrics.workspace_leakage_probability)
                correctness["inverse_round_trip_error"] = float(metrics.inverse_round_trip_error)
            except Exception as exc:
                correctness["statevector_status"] = "failed"
                correctness["statevector_error"] = f"{type(exc).__name__}: {exc}"
        else:
            correctness["statevector_status"] = "not_run_resource_cap"
    elif algorithm_id == "authors_reference_artifact":
        resources["paper_accounted_toffoli"] = last_res["paper_accounted_toffoli"]
        resources["coherent_toffoli"] = last_res["paper_accounted_toffoli"]
        resources["authors_counter_raw"] = last_res["paper_accounted_toffoli_raw"]
        resources["authors_counter_status"] = last_res["resource_count_status"]
        resources["authors_reference_status"] = last_res["reference_status"]
        resources["logical_depth"] = None
        resources["authors_circuit_batches_count"] = last_res["circuit_batches_count"]

    return {
        "compile_wall_ms": compile_wall_ms,
        "compile_cpu_ms": compile_cpu_ms,
        "rss_bytes": rss_bytes,
        "logical_resources": resources,
        "correctness": correctness,
    }


def _execute_gpu_lane(support: tuple[str, ...], n: int, gates: tuple[Any, ...], ancilla_count: int) -> dict[str, Any]:
    """Execute a compiled SIRIUS reversible sequence on GPU basis rows and check CPU parity."""
    from sparseprep.simulator import simulate_basis_state

    try:
        import cupy as cp
        from sparseprep.backends.cupy_simulator import simulate_int_states_cupy
        from sparseprep.model import bitstring_to_int
    except Exception as exc:
        return {"gpu_execution_status": "unavailable", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": f"{type(exc).__name__}: {exc}"}

    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            return {"gpu_execution_status": "unavailable", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": "CuPy reports no CUDA device"}
    except Exception as exc:
        return {"gpu_execution_status": "unavailable", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": f"CUDA device probe failed: {type(exc).__name__}: {exc}"}

    wire_count = n + ancilla_count
    if wire_count > 63:
        return {"gpu_execution_status": "unsupported_width", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": f"uint64 backend limit is 63 wires; workload requires {wire_count}"}

    rows = tuple(s + "0" * ancilla_count for s in support)
    int_words = [bitstring_to_int(s) for s in rows]
    expected = tuple(simulate_basis_state(row, gates) for row in rows)
    t0_total = time.perf_counter_ns()
    t0_h2d = time.perf_counter_ns()
    d_arr = cp.asarray(int_words, dtype=cp.uint64)
    cp.cuda.Stream.null.synchronize()
    t1_h2d = time.perf_counter_ns()
    t0_kern = time.perf_counter_ns()
    d_out = simulate_int_states_cupy(d_arr, wire_count, gates)
    cp.cuda.Stream.null.synchronize()
    t1_kern = time.perf_counter_ns()
    t0_d2h = time.perf_counter_ns()
    h_out = cp.asnumpy(d_out)
    cp.cuda.Stream.null.synchronize()
    t1_d2h = time.perf_counter_ns()
    t1_total = time.perf_counter_ns()
    actual = tuple(format(int(value), f"0{wire_count}b") for value in h_out)
    if actual != expected:
        return {"gpu_execution_status": "parity_failed", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": "GPU basis-row output differs from CPU simulator"}

    return {
        "gpu_execution_status": "passed",
        "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW",
        "gpu_basis_batch_wall_ms": (t1_total - t0_total) / 1e6,
        "gpu_kernel_ms": (t1_kern - t0_kern) / 1e6,
        "host_to_device_ms": (t1_h2d - t0_h2d) / 1e6,
        "device_to_host_ms": (t1_d2h - t0_d2h) / 1e6,
        "gpu_rows_verified": len(rows),
    }


def validate_run_record(record: dict[str, Any], schema_file: Path | None = None) -> list[str]:
    path = schema_file or RUN_RECORD_SCHEMA_PATH
    if not path.exists():
        return [f"Schema file not found: {path}"]
    try:
        import jsonschema
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        return [f"{e.json_path}: {e.message}" for e in validator.iter_errors(record)]
    except ImportError:
        # Minimal fallback
        for key in ("record_version", "run_id", "plan_id", "tier", "algorithm_id", "status", "problem", "seed", "environment", "timings", "logical_resources", "correctness", "provenance"):
            if key not in record:
                return [f"Missing required key: {key}"]
        return []


def run_benchmark_job(
    plan_id: str,
    tier: str,
    algorithm_id: str,
    n: int,
    s: int,
    seed: int,
    support_family: str,
    coefficient_family: str,
    sign_profile: str,
    run_id: str,
    repetitions: int,
    warmups: int,
    timeout_sec: float,
    enable_gpu: bool,
    environment: dict[str, Any],
    paper_doi: str,
    artifact_md5: str,
    qubit_cap: int = STATEVECTOR_MAX_QUBITS_DEFAULT,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ell = ceil_log2_positive(s)
    from benchmarking.adapters.authors_adapter import get_reference_artifact_sha256
    artifact_sha256 = get_reference_artifact_sha256()

    # Generate deterministic workload
    try:
        support = generate_support(n, s, support_family, seed)
        coeffs = generate_coefficients(s, coefficient_family, seed)
        signs = generate_signs(s, sign_profile, seed)
        support_hash = compute_support_hash(support, n)
        input_identity = compute_workload_identity(
            n=n, support=support, coefficients=coeffs, signs=signs,
            support_family=support_family, coefficient_family=coefficient_family,
            sign_profile=sign_profile, seed=seed,
            workload_parameters={"tier": tier, "s": s},
        )
    except Exception as exc:
        ended_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "record_version": "1.1.0",
            "run_id": run_id,
            "plan_id": plan_id,
            "tier": tier,
            "algorithm_id": algorithm_id,
            "status": "skipped" if "repeated_prefix" in support_family else "invalid",
            "problem": {
                "n": n,
                "s": s,
                "ell": ell,
                "support_family": support_family,
                "coefficient_family": coefficient_family,
                "sign_profile": sign_profile,
                "support_sha256": None,
            },
            "seed": seed,
            "environment": environment,
            "timings": {},
            "logical_resources": {},
            "correctness": {},
            "provenance": {
                "git_commit": get_git_commit(),
                "git_dirty": get_git_dirty(),
                "source_diff_sha256": get_git_diff_sha256(),
                "paper_doi": paper_doi,
                "artifact_md5": artifact_md5,
                "generator_version": "0.9.2",
                "started_at_utc": started_at,
                "ended_at_utc": ended_at,
            },
            "notes": f"Workload generation skipped or invalid: {exc}",
        }

    if algorithm_id == "authors_reference_artifact":
        from benchmarking.adapters.authors_adapter import get_authors_artifact_status
        status_info = get_authors_artifact_status()
        if status_info.get("reference_status") != "PASS":
            ended_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return {
                "record_version": "1.1.0", "run_id": run_id, "plan_id": plan_id,
                "tier": tier, "algorithm_id": algorithm_id, "status": "skipped",
                "problem": {"n": n, "s": s, "ell": ell, "support_family": support_family,
                            "coefficient_family": coefficient_family, "sign_profile": sign_profile,
                            "support_sha256": support_hash},
                "input_identity": input_identity,
                "benchmark_configuration": {"plan_id": plan_id, "tier": tier, "repetitions": repetitions,
                    "warmups": warmups, "timeout_seconds": timeout_sec, "gpu_enabled": enable_gpu,
                    "statevector_max_qubits": qubit_cap},
                "seed": seed, "environment": environment,
                "timings": {}, "logical_resources": {}, "correctness": {},
                "provenance": {"git_commit": get_git_commit(), "git_dirty": get_git_dirty(),
                               "source_diff_sha256": get_git_diff_sha256(), "paper_doi": paper_doi,
                               "artifact_md5": artifact_md5, "artifact_sha256": artifact_sha256,
                               "reference_status": status_info.get("reference_status"),
                               "generator_version": "0.9.2", "started_at_utc": started_at,
                               "ended_at_utc": ended_at},
                "notes": f"Authors reference {status_info.get('reference_status')}: {status_info.get('blocked_reason') or status_info.get('artifact_integrity')}",
            }

    # Run compilation with process isolation and timeout
    status = "completed"
    error_note: str | None = None
    timings: dict[str, Any] = {}
    logical_resources: dict[str, Any] = {}
    correctness: dict[str, Any] = {}

    try:
        # Explicit spawn avoids Python 3.14's platform default forkserver, which
        # requires an IPC resource that may be unavailable in managed runners.
        mp_context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=1, mp_context=mp_context) as executor:
            future = executor.submit(
                _execute_compile_worker,
                algorithm_id,
                n,
                s,
                support,
                coeffs,
                signs,
                repetitions,
                warmups,
                qubit_cap,
            )
            worker_res = future.result(timeout=timeout_sec)
            timings["compile_wall_ms"] = worker_res["compile_wall_ms"]
            timings["compile_cpu_ms"] = worker_res["compile_cpu_ms"]
            logical_resources = worker_res["logical_resources"]
            correctness = worker_res["correctness"]

            if correctness.get("inverse_round_trip_error", 0.0) > STATEVECTOR_ATOL_DEFAULT:
                status = "failed"
                error_note = "Inverse round-trip check failed on support basis states."
            if correctness.get("statevector_status") == "failed":
                status = "failed"
                error_note = f"Exact statevector verification failed: {correctness.get('statevector_error', 'unspecified error')}"
    except FutureTimeoutError:
        status = "timed_out"
        error_note = f"Compilation exceeded timeout of {timeout_sec}s."
    except Exception as exc:
        status = "failed"
        error_note = f"Worker raised exception: {type(exc).__name__}: {exc}"

    # Optional GPU throughput lane
    if enable_gpu and status == "completed":
        try:
            if algorithm_id != "independent_batched_isometry":
                gpu_res = {"gpu_execution_status": "not_applicable", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": "GPU lane currently requires independent_batched_isometry output"}
            else:
                problem = SparseStateProblem(n=n, support=support, coefficients=coeffs, signs=signs)
                compiled = run_batched_isometry(problem)
                gpu_res = _execute_gpu_lane(support, n, compiled.forward_gates, len(compiled.ancilla_wires))
            timings.update(gpu_res)
            if gpu_res.get("gpu_execution_status") in ("failed", "parity_failed"):
                status = "failed"
                error_note = f"GPU reversible basis-row validation failed: {gpu_res.get('gpu_error', gpu_res['gpu_execution_status'])}"
        except Exception as exc:
            timings.update({"gpu_execution_status": "failed", "gpu_execution_kind": "SIRIUS_REVERSIBLE_BASIS_ROW", "gpu_error": f"{type(exc).__name__}: {exc}"})
            status = "failed"
            error_note = f"GPU reversible basis-row validation failed: {type(exc).__name__}: {exc}"

    ended_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    record: dict[str, Any] = {
        "record_version": "1.1.0",
        "run_id": run_id,
        "plan_id": plan_id,
        "tier": tier,
        "algorithm_id": algorithm_id,
        "status": status,
        "problem": {
            "n": n,
            "s": s,
            "ell": ell,
            "support_family": support_family,
            "coefficient_family": coefficient_family,
            "sign_profile": sign_profile,
            "support_sha256": support_hash,
        },
        "input_identity": input_identity,
        "benchmark_configuration": {"plan_id": plan_id, "tier": tier, "repetitions": repetitions,
            "warmups": warmups, "timeout_seconds": timeout_sec, "gpu_enabled": enable_gpu,
            "statevector_max_qubits": qubit_cap},
        "seed": seed,
        "environment": environment,
        "timings": timings,
        "logical_resources": logical_resources,
        "correctness": correctness,
        "provenance": {
            "git_commit": get_git_commit(),
            "git_dirty": get_git_dirty(),
            "source_diff_sha256": get_git_diff_sha256(),
            "paper_doi": paper_doi,
            "artifact_md5": artifact_md5,
            "artifact_sha256": artifact_sha256,
            "generator_version": "0.9.2",
            "started_at_utc": started_at,
            "ended_at_utc": ended_at,
        },
    }
    if error_note:
        record["notes"] = error_note
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute reproducible SIRIUS benchmarks (Phase 9.2).")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN_PATH, help="Phase 9.1 benchmark plan JSON path")
    parser.add_argument("--tier", type=str, default="smoke", choices=["smoke", "scaling", "stress", "custom"], help="Execution tier")
    parser.add_argument("--methods", nargs="+", default=["independent_batched_isometry", "malvetti_baseline", "end_to_end_state_preparation"], help="Algorithms to benchmark")
    parser.add_argument("--output", type=Path, default=Path("results/raw"), help="Output directory for raw JSONL records")
    parser.add_argument("--enable-gpu", action="store_true", help="Enable optional CuPy GPU basis-row throughput lane")
    parser.add_argument("--max-jobs", type=int, default=None, help="Cap total executed jobs (useful for smoke test verification)")
    parser.add_argument("--dry-run", action="store_true", help="Print preflight job plan without running benchmarks")
    parser.add_argument("--confirm-large-sweep", action="store_true", help="Acknowledge execution of large benchmark sweeps (>1000 jobs)")
    args = parser.parse_args()

    # Load plan
    if not args.plan.exists():
        print(f"Error: plan file not found: {args.plan}", file=sys.stderr)
        return 1
    plan = json.loads(args.plan.read_text(encoding="utf-8"))

    tier_cfg = plan["tiers"].get(args.tier)
    if not tier_cfg:
        print(f"Error: tier '{args.tier}' not defined in plan.", file=sys.stderr)
        return 1

    # Extract workload parameters
    n_values = tier_cfg["n_values"]
    s_values = tier_cfg["s_values"]
    seeds = tier_cfg["seeds"]
    support_families = tier_cfg["support_families"]
    coeff_families = tier_cfg["coefficient_families"]
    sign_profiles = tier_cfg["sign_profiles"]
    repetitions = tier_cfg["repetitions"]
    warmups = tier_cfg["warmups"]
    timeout_sec = float(tier_cfg["timeout_seconds_per_compile"])

    # Enumerate jobs
    jobs: list[dict[str, Any]] = []
    for method in args.methods:
        for n in n_values:
            for s in s_values:
                if s > (1 << n):
                    continue
                for fam in support_families:
                    # Filter repeated prefix eligibility
                    ell = ceil_log2_positive(s)
                    if fam == "repeated_prefix" and (n - ell < 1 or s > (1 << (n - ell))):
                        continue
                    for coeff in coeff_families:
                        for sign in sign_profiles:
                            for seed in seeds:
                                jobs.append({
                                    "algorithm_id": method,
                                    "n": n,
                                    "s": s,
                                    "seed": seed,
                                    "support_family": fam,
                                    "coefficient_family": coeff,
                                    "sign_profile": sign,
                                })

    total_jobs = len(jobs)
    if args.max_jobs and args.max_jobs < total_jobs:
        jobs = jobs[:args.max_jobs]
        total_jobs = len(jobs)

    # Preflight summary
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ")
    run_id = f"sirius_{args.tier}_{run_timestamp}"

    print("================================================================================")
    print("                     SIRIUS PHASE 9.2 BENCHMARK RUNNER                          ")
    print("================================================================================")
    print(f"Plan ID:            {plan.get('plan_id')}")
    print(f"Tier:               {args.tier}")
    print(f"Run ID:             {run_id}")
    print(f"Selected Methods:   {', '.join(args.methods)}")
    print(f"Total Jobs to Run:  {total_jobs}")
    print(f"Repetitions / Job:  {repetitions} (Warmups: {warmups})")
    print(f"Timeout / Job:      {timeout_sec}s")
    print(f"GPU Lane:           {'ENABLED (CuPy)' if args.enable_gpu else 'DISABLED'}")
    print(f"Statevector Cap:    <= {STATEVECTOR_MAX_QUBITS_DEFAULT} qubits")
    print("================================================================================")

    if args.dry_run:
        print("Dry run requested. Exiting without execution.")
        return 0

    if total_jobs > 1000 and not args.confirm_large_sweep:
        print("Preflight check: Large benchmark sweep detected (> 1000 jobs).", file=sys.stderr)
        print("Please rerun with --confirm-large-sweep to explicitly authorize.", file=sys.stderr)
        return 1

    # Probe environment
    environment = probe_run_environment()
    paper_doi = plan["project"].get("paper_doi", "10.22331/q-2026-09-10-2208")
    artifact_md5 = plan["project"].get("authors_artifact_md5", "c58634ba415b4e3fb729648460f32ad7")

    args.output.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output / f"{run_id}.jsonl"

    print(f"Writing raw records to: {jsonl_path}")

    completed_count = 0
    failed_count = 0
    skipped_count = 0
    timeout_count = 0
    schema_error_count = 0

    with jsonl_path.open("a", encoding="utf-8") as f_out:
        for idx, job in enumerate(jobs, start=1):
            record = run_benchmark_job(
                plan_id=plan.get("plan_id", "phase9-cross-device-v1"),
                tier=args.tier,
                algorithm_id=job["algorithm_id"],
                n=job["n"],
                s=job["s"],
                seed=job["seed"],
                support_family=job["support_family"],
                coefficient_family=job["coefficient_family"],
                sign_profile=job["sign_profile"],
                run_id=run_id,
                repetitions=repetitions,
                warmups=warmups,
                timeout_sec=timeout_sec,
                enable_gpu=args.enable_gpu,
                environment=environment,
                paper_doi=paper_doi,
                artifact_md5=artifact_md5,
            )

            # Validate against schema
            errors = validate_run_record(record)
            if errors:
                schema_error_count += 1
                print(f"\nWarning: Record failed schema validation (Job {idx}):", file=sys.stderr)
                for err in errors:
                    print(f"  {err}", file=sys.stderr)

            # Write immutable record line
            f_out.write(json.dumps(record) + "\n")
            f_out.flush()

            status = record["status"]
            if status == "completed":
                completed_count += 1
            elif status == "failed":
                failed_count += 1
            elif status == "skipped":
                skipped_count += 1
            elif status == "timed_out":
                timeout_count += 1

            status_char = "." if status == "completed" else ("S" if status == "skipped" else ("T" if status == "timed_out" else "F"))
            sys.stdout.write(status_char)
            if idx % 50 == 0 or idx == total_jobs:
                sys.stdout.write(f" [{idx}/{total_jobs}]\n")
            sys.stdout.flush()

    print("\n--------------------------------------------------------------------------------")
    print(f"Benchmark run complete: {total_jobs} jobs executed.")
    print(f"  Completed: {completed_count}")
    print(f"  Failed:    {failed_count}")
    print(f"  Skipped:   {skipped_count}")
    print(f"  Timed out: {timeout_count}")
    print(f"  Schema-invalid records: {schema_error_count}")
    print(f"Raw immutable output preserved: {jsonl_path}")
    print("--------------------------------------------------------------------------------")
    return 0 if failed_count == 0 and schema_error_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
