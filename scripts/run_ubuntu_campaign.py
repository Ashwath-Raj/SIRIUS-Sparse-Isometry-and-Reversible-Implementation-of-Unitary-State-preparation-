#!/usr/bin/env python3
"""Execute versioned, resumable Ubuntu laptop pilot records for both SIRIUS tracks."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidate_ai" / "src"))
sys.path.insert(0, str(ROOT))

from sparseprep import SparseStateProblem, compile_sparse_state_preparation, prepare_sparse_state, run_batched_isometry, run_malvetti_baseline
from sparseprep.model import bitstring_to_int
from sparseprep.resources import count_emitted_resources
from sparseprep.simulator import simulate_basis_state
from benchmarking.adapters.authors_adapter import run_authors_reference_isometry, get_authors_artifact_status, get_reference_artifact_sha256
from benchmarking.extensions.symmetry_workloads import make_symmetry_workload
from benchmarking.runners.environment_probe import probe_machine_manifest, validate_manifest, get_git_diff_sha256
from benchmarking.runners.run_benchmarks import generate_coefficients, generate_signs, generate_support, _execute_gpu_lane, compute_support_hash

MACHINE_ID = "ubuntu-amd-ryzen6600h-rtx3050-laptop"
PLAN_ID = "sirius-ubuntu-laptop-pilot-v1"
MAX_ATTEMPTS = 64
GPU_FREE_FRACTION = 0.35
RUN_SOURCE_MANIFEST_SHA256: str | None = None


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_jobs() -> tuple[list[dict], list[dict]]:
    jobs: list[dict] = []
    # Track A: balanced candidate/baseline grid and independent-seed candidate checks.
    for n in (8, 10):
        for s in (3, 5):
            for algorithm in ("independent_batched_isometry", "malvetti_baseline"):
                jobs.append({"track": "paper_reproduction", "algorithm_id": algorithm, "n": n, "s": s, "seed": 101,
                             "support_family": "seeded_random", "coefficient_family": "random_complex", "sign_profile": "random_pm_one"})
            jobs.append({"track": "paper_reproduction", "algorithm_id": "independent_batched_isometry", "n": n, "s": s, "seed": 211,
                         "support_family": "seeded_random", "coefficient_family": "random_complex", "sign_profile": "random_pm_one"})
    jobs.append({"track": "paper_reproduction", "algorithm_id": "end_to_end_state_preparation", "n": 8, "s": 3, "seed": 101,
                 "support_family": "seeded_random", "coefficient_family": "random_complex", "sign_profile": "random_pm_one"})
    jobs.append({"track": "paper_reproduction", "algorithm_id": "authors_reference_artifact", "n": 8, "s": 3, "seed": 101,
                 "support_family": "seeded_random", "coefficient_family": "random_complex", "sign_profile": "random_pm_one"})
    # Track B: matched random, fixed-weight lexical and fixed-weight seeded order.
    for n in (8, 10):
        k = n // 2
        for s in (3, 5):
            for seed in (101, 211):
                for family, ordering in (("seeded_random", "lexicographic"), ("fixed_hamming_weight", "lexicographic"), ("fixed_hamming_weight", "seeded_shuffled")):
                    for algorithm in ("independent_batched_isometry", "malvetti_baseline"):
                        jobs.append({"track": "symmetry_structured_sparse_supports", "algorithm_id": algorithm, "n": n, "k": k if family == "fixed_hamming_weight" else None, "s": s, "seed": seed,
                                     "support_family": family, "ordering": ordering, "coefficient_family": "random_complex", "sign_profile": "random_pm_one"})
    assert len(jobs) == 62, len(jobs)
    excluded = [
        {"algorithm_id": "authors_reference_artifact", "reason": "adapter exposes an isometry mapping/counter only; symmetry permutations and broad semantic comparison are kept out of the extension pilot"},
        {"algorithm_id": "end_to_end_state_preparation", "reason": "kept to one small paper-track exact-statevector case to stay within the 64-attempt pilot cap"},
        {"family": "fixed_hamming_weight_gray", "reason": "optional ordering omitted; no independently validated revolving-door implementation"},
        {"support_family": "zero_residual_subspace/repeated_prefix", "reason": "original reproduction plans retain these families; pilot prioritizes random vs fixed-weight geometry"},
    ]
    return jobs, excluded


def select_stratified_jobs(jobs: list[dict], limit: int, seed: int) -> list[dict]:
    """Seeded round-robin over track/algorithm/size/family/order strata."""
    import random as _random
    buckets: dict[tuple, list[dict]] = {}
    for job in jobs:
        key = (job["track"], job["algorithm_id"], job["n"], job["s"], job["support_family"], job.get("ordering", "none"))
        buckets.setdefault(key, []).append(job)
    rng = _random.Random(seed)
    keys = list(buckets)
    rng.shuffle(keys)
    for bucket in buckets.values():
        rng.shuffle(bucket)
    selected = []
    while len(selected) < min(limit, len(jobs)):
        advanced = False
        for key in keys:
            if buckets[key] and len(selected) < limit:
                selected.append(buckets[key].pop())
                advanced = True
        if not advanced: break
    return selected


def job_identity(job: dict) -> str:
    return hashlib.sha256(json.dumps(job, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def collect_completed_job_ids(paths: list[Path]) -> set[str]:
    """Recover checkpoint identity from canonical JSONL without duplicating attempts."""
    completed = set()
    for path in paths:
        if not path.exists(): continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                if isinstance(record.get("job_id"), str): completed.add(record["job_id"])
            except (json.JSONDecodeError, AttributeError):
                continue
    return completed


def get_rss_peak_bytes() -> int | None:
    try:
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    except Exception:
        return None


def available_memory_bytes() -> int | None:
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except Exception:
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        except Exception:
            return None
    return None


def thermal_gpu_state() -> dict:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {"available": False, "reason": "nvidia-smi not found"}
    result = subprocess.run([smi, "--query-gpu=temperature.gpu,memory.free,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    if result.returncode:
        return {"available": False, "reason": result.stderr.strip()}
    fields = [v.strip() for v in result.stdout.splitlines()[0].split(",")]
    return {"available": True, "temperature_c": int(fields[0]), "free_vram_mib": int(fields[1]), "total_vram_mib": int(fields[2])}


def make_job_workload(job: dict):
    if job["track"] == "symmetry_structured_sparse_supports":
        return make_symmetry_workload(n=job["n"], s=job["s"], seed=job["seed"], support_family=job["support_family"],
                                      ordering=job["ordering"], k=job.get("k"), coefficient_family=job["coefficient_family"], sign_profile=job["sign_profile"])
    support = generate_support(job["n"], job["s"], job["support_family"], job["seed"])
    coefficients = generate_coefficients(job["s"], job["coefficient_family"], job["seed"])
    signs = generate_signs(job["s"], job["sign_profile"], job["seed"])
    # The base support generator returns sorted support; associate generated coefficients/signs in that order.
    return type("Workload", (), {"n": job["n"], "k": None, "support_family": job["support_family"], "seed": job["seed"],
        "ordering": "lexicographic", "support": support, "coefficients": coefficients, "signs": signs,
        "canonical_instance_sha256": None, "ordered_input_sha256": None, "geometry": {}})()


def resource_fields(result, algorithm_id: str) -> tuple[dict, dict]:
    if algorithm_id in ("independent_batched_isometry", "malvetti_baseline"):
        gates = result.forward_gates
        hist = asdict(count_emitted_resources(gates))
        if algorithm_id == "independent_batched_isometry":
            r = result.resources
            values = {"paper_accounted_toffoli": r.total_paper_accounted_toffolis,
                      "coherent_toffoli": r.total_coherent_toffolis,
                      "clean_ancillas": r.max_clean_ancillas_used,
                      "emitted_operation_count": len(gates), "emitted_toffoli_count": hist["toffoli"] + hist["negative_control_toffoli"],
                      "resource_scope": "isometry_only", "pui_event_count": len(result.pui_events),
                      "restricted_pui_events": sum(x.kind == "restricted" for x in result.pui_events),
                      "unrestricted_pui_events": sum(x.kind == "unrestricted" for x in result.pui_events),
                      "number_of_batches": r.number_of_batches, "batch_size_limit": r.batch_size_limit}
            clean = result.verify() is None
        else:
            r = result.resources
            values = {"paper_accounted_toffoli": r.toffoli_count, "coherent_toffoli": r.toffoli_count,
                      "clean_ancillas": r.clean_ancillas, "emitted_operation_count": len(gates),
                      "emitted_toffoli_count": hist["toffoli"] + hist["negative_control_toffoli"], "resource_scope": "isometry_only",
                      "baseline_step_count": len(result.steps)}
            result.verify(); clean = True
        return values, {"mapping_injective": len(set(result.f)) == result.s, "residual_rows_zero": all(row[result.ell:] == "0" * result.residual_width for row in result.final_tableau),
                        "forward_inverse_and_ancilla_clean": bool(clean), "basis_rows_checked": result.s, "gate_histogram": hist}
    if algorithm_id == "end_to_end_state_preparation":
        res = result.resources
        return {"paper_accounted_toffoli": res.algorithm3_paper_accounted_toffolis, "coherent_toffoli": res.algorithm3_coherent_toffolis,
                "clean_ancillas": res.algorithm3_clean_ancillas + res.phase_clean_ancillas, "emitted_operation_count": res.total_operations,
                "emitted_toffoli_count": res.total_toffolis, "resource_scope": "end_to_end; paper cost is isometry component",
                "dense_loader_operations": res.dense_loader.operations, "sign_oracle_operations": res.sign_oracle.operations,
                "inverse_isometry_operations": res.inverse_isometry.operations, "marker_cleanup_operations": res.marker_cleanup.operations}, {}
    return {}, {}


def execute_job(job: dict, run_id: str, machine_manifest: dict, gpu_enabled: bool, gpu_budget_fraction: float) -> dict:
    started = utc(); t0 = time.perf_counter_ns(); cpu0 = time.process_time_ns()
    memory_before = available_memory_bytes(); gpu_before = thermal_gpu_state()
    record = {"record_version": "ubuntu-attempt-v1", "plan_id": PLAN_ID, "track": job["track"], "run_id": run_id,
              "job_id": hashlib.sha256(json.dumps(job, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
              "algorithm_id": job["algorithm_id"], "status": "failed", "seed": job["seed"], "job": job,
              "machine_id": MACHINE_ID, "machine_manifest_sha256": hashlib.sha256(json.dumps(machine_manifest, sort_keys=True).encode()).hexdigest(),
              "started_at_utc": started, "resources": {}, "correctness": {}, "timings": {}, "geometry": {},
              "provenance": {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                             "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                             "source_diff_sha256": get_git_diff_sha256(ROOT), "source_manifest_sha256": RUN_SOURCE_MANIFEST_SHA256,
                             "paper_doi": "10.22331/q-2026-09-10-2208", "artifact_sha256": get_reference_artifact_sha256()}}
    try:
        workload = make_job_workload(job)
        problem = SparseStateProblem(n=job["n"], support=workload.support, coefficients=workload.coefficients, signs=workload.signs,
                                     seed=job["seed"], metadata=(("family", job["support_family"]), ("ordering", workload.ordering)))
        support_hash = compute_support_hash(workload.support, job["n"])
        ordered_identity = {"n": job["n"], "support": list(workload.support),
                            "coefficients": [[c.real, c.imag] for c in workload.coefficients], "signs": list(workload.signs)}
        ordered_input_sha = hashlib.sha256(json.dumps(ordered_identity, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        canonical_states = sorted([[row, [coef.real, coef.imag], sign] for row, coef, sign in zip(workload.support, workload.coefficients, workload.signs)])
        canonical_sha = hashlib.sha256(json.dumps({"n": job["n"], "states": canonical_states}, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        record["input_identity"] = {"ordered_support_sha256": support_hash,
            "ordered_input_sha256": ordered_input_sha,
            "canonical_mathematical_instance_sha256": workload.canonical_instance_sha256 or canonical_sha,
            "coefficient_sign_attachment": "basis-state keyed; reordered with support"}
        record["problem"] = {"n": job["n"], "s": job["s"], "k": job.get("k"), "support_family": job["support_family"],
                              "coefficient_family": job["coefficient_family"], "sign_profile": job["sign_profile"],
                              "ordering": getattr(workload, "ordering", "lexicographic"), "support": list(workload.support),
                              "coefficients": [[c.real, c.imag] for c in workload.coefficients], "signs": list(workload.signs), "seed": job["seed"]}
        record["geometry"] = workload.geometry
        record["correctness"]["amplitude_norm"] = sum(abs(c) ** 2 for c in workload.coefficients)
        construction_wall_start = time.perf_counter_ns()
        construction_cpu_start = time.process_time_ns()
        if job["algorithm_id"] == "independent_batched_isometry":
            result = run_batched_isometry(problem)
        elif job["algorithm_id"] == "malvetti_baseline":
            result = run_malvetti_baseline(problem)
        elif job["algorithm_id"] == "end_to_end_state_preparation":
            result = compile_sparse_state_preparation(problem)
        elif job["algorithm_id"] == "authors_reference_artifact":
            status = get_authors_artifact_status()
            if status.get("reference_status") != "PASS":
                record["status"] = "skipped"; record["failure_reason"] = f"authors reference {status.get('reference_status')}: {status.get('blocked_reason')}"
                return finalize_record(record, t0, cpu0, memory_before, gpu_before)
            result = run_authors_reference_isometry(problem)
        else:
            raise ValueError(f"unsupported algorithm: {job['algorithm_id']}")
        wall_ms = (time.perf_counter_ns() - construction_wall_start) / 1e6
        cpu_ms = (time.process_time_ns() - construction_cpu_start) / 1e6
        if job["algorithm_id"] == "authors_reference_artifact":
            mapping = result.get("bijection", ())
            labels = [int(pair[0]) for pair in mapping]
            rows = [int(pair[1]) for pair in mapping]
            record["resources"] = {k: result.get(k) for k in ("paper_accounted_toffoli", "paper_accounted_toffoli_raw", "resource_count_status", "reference_status", "circuit_batches_count")}
            record["correctness"] = {"mapping_total": len(mapping) == job["s"], "mapping_injective": len(set(labels)) == len(labels),
                                      "mapping_rows_total": sorted(rows) == list(range(job["s"])),
                                      "residual_row_behavior": "not_exposed_by_authors_api"}
        else:
            record["resources"], record["correctness"] = resource_fields(result, job["algorithm_id"])
        record["timings"].update({"construction_wall_ms": wall_ms, "construction_process_cpu_ms": cpu_ms,
                                  "peak_process_rss_bytes": get_rss_peak_bytes(), "timing_scope": "one in-process construction; excludes input generation and GPU lane"})
        record["status"] = "completed" if all(v is True for k,v in record["correctness"].items() if k in {"mapping_injective", "residual_rows_zero", "forward_inverse_and_ancilla_clean"}) else "failed"
        if job["algorithm_id"] == "end_to_end_state_preparation":
            try:
                _, metrics = prepare_sparse_state(problem, max_statevector_qubits=20)
                record["correctness"].update({"statevector_status": "passed", "fidelity": metrics.fidelity,
                    "maximum_amplitude_error": metrics.maximum_amplitude_error,
                    "workspace_leakage_probability": metrics.workspace_leakage_probability,
                    "outside_support_probability": metrics.outside_support_probability})
            except Exception as exc:
                record["correctness"].update({"statevector_status": "failed", "statevector_error": f"{type(exc).__name__}: {exc}"})
                record["status"] = "failed"
        elif job["algorithm_id"] == "authors_reference_artifact":
            record["status"] = "completed" if all(record["correctness"].get(k) is True for k in ("mapping_total", "mapping_injective", "mapping_rows_total")) else "failed"
        if gpu_enabled and job["algorithm_id"] in ("independent_batched_isometry", "malvetti_baseline") and record["status"] == "completed":
            record["timings"]["gpu_memory_budget_fraction_of_free_at_start"] = gpu_budget_fraction
            try:
                import cupy as cp
                free_vram, total_vram = cp.cuda.runtime.memGetInfo()
                gpu_probe0 = thermal_gpu_state()
                if gpu_probe0.get("temperature_c", 0) >= 82 or free_vram < int(total_vram * 0.10):
                    record["gpu"] = {"status": "skipped_resource_guard", "reason": "temperature or free-VRAM guard threshold reached"}
                else:
                    gates = result.forward_gates
                    ancilla_count = len(getattr(result, "ancilla_wires", ())) or int(getattr(getattr(result, "resources", None), "clean_ancillas", 0))
                    try:
                        gpu_result = _execute_gpu_lane(workload.support, job["n"], gates, ancilla_count,
                                                       memory_budget_fraction=gpu_budget_fraction)
                    except Exception as gpu_exc:
                        try:
                            import cupy as cp
                            oom = isinstance(gpu_exc, cp.cuda.memory.OutOfMemoryError)
                        except Exception:
                            oom = "out of memory" in str(gpu_exc).lower() or "cudaErrorMemoryAllocation" in str(gpu_exc)
                        record["gpu"] = {"status": "out_of_memory" if oom else "failed", "reason": f"{type(gpu_exc).__name__}: {gpu_exc}",
                                          "free_vram_before_bytes": int(free_vram), "total_vram_bytes": int(total_vram),
                                          "memory_budget_bytes": int(free_vram * gpu_budget_fraction)}
                        record["status"] = "failed"
                        gpu_result = None
                    if gpu_result is not None:
                        record["gpu"] = {"status": gpu_result.get("gpu_execution_status", "missing"), **gpu_result,
                                          "free_vram_before_bytes": int(free_vram), "total_vram_bytes": int(total_vram),
                                          "temperature_before_c": gpu_probe0.get("temperature_c"),
                                          "memory_budget_bytes": int(free_vram * gpu_budget_fraction)}
                        if record["gpu"]["status"] != "passed": record["status"] = "failed"
            except Exception as exc:
                record["gpu"] = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
                record["status"] = "failed"
    except Exception as exc:
        record["status"] = "failed"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
    return finalize_record(record, t0, cpu0, memory_before, gpu_before)


def finalize_record(record: dict, t0: int, cpu0: int, memory_before: int | None, gpu_before: dict) -> dict:
    record["ended_at_utc"] = utc()
    record.setdefault("timings", {})
    record["timings"].setdefault("total_attempt_wall_ms", (time.perf_counter_ns() - t0) / 1e6)
    record["timings"].setdefault("total_attempt_process_cpu_ms", (time.process_time_ns() - cpu0) / 1e6)
    record["monitoring"] = {"available_ram_before_bytes": memory_before, "available_ram_after_bytes": available_memory_bytes(),
                            "gpu_before": gpu_before, "gpu_after": thermal_gpu_state(), "cpu_worker_count": 1}
    return record


class AttemptTimeout(TimeoutError):
    pass


def _timeout_handler(_signum, _frame):
    raise AttemptTimeout("attempt exceeded 180 second pilot job limit")


def nonexecution_record(job: dict, run_id: str, manifest: dict, status: str, reason: str) -> dict:
    start = utc()
    job_id = hashlib.sha256(json.dumps(job, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = {"record_version": "ubuntu-attempt-v1", "plan_id": PLAN_ID, "track": job["track"], "run_id": run_id,
              "job_id": job_id, "algorithm_id": job["algorithm_id"], "status": status, "seed": job["seed"], "job": job,
              "machine_id": MACHINE_ID, "machine_manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
              "started_at_utc": start, "ended_at_utc": utc(), "failure_reason": reason,
              "provenance": {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                             "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                             "source_diff_sha256": get_git_diff_sha256(ROOT), "source_manifest_sha256": RUN_SOURCE_MANIFEST_SHA256,
                             "paper_doi": "10.22331/q-2026-09-10-2208", "artifact_sha256": get_reference_artifact_sha256()}}
    try:
        w = make_job_workload(job)
        payload = {"n": job["n"], "support": list(w.support), "coefficients": [[c.real,c.imag] for c in w.coefficients], "signs": list(w.signs)}
        result["input_identity"] = {"ordered_support_sha256": compute_support_hash(w.support, job["n"]),
                                     "ordered_input_sha256": hashlib.sha256(json.dumps(payload,separators=(",", ":")).encode()).hexdigest(),
                                     "canonical_mathematical_instance_sha256": w.canonical_instance_sha256,
                                     "coefficient_sign_attachment": "basis-state keyed; reordered with support"}
    except Exception as exc:
        result["failure_reason"] += f"; workload identity unavailable: {type(exc).__name__}: {exc}"
    return result


def main() -> int:
    global RUN_SOURCE_MANIFEST_SHA256
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", choices=("both", "paper_reproduction", "symmetry_structured_sparse_supports"), default="both")
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--selection-seed", type=int, default=20261117)
    parser.add_argument("--gpu-memory-budget-fraction", type=float, default=GPU_FREE_FRACTION)
    parser.add_argument("--no-gpu", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 0 < args.gpu_memory_budget_fraction <= 0.5:
        parser.error("GPU memory budget fraction must be in (0, 0.5]")
    jobs, excluded = build_jobs()
    if args.track != "both": jobs = [x for x in jobs if x["track"] == args.track]
    if args.max_attempts < 1 or args.max_attempts > MAX_ATTEMPTS:
        parser.error(f"max-attempts must be within [1,{MAX_ATTEMPTS}]")
    # Stable stratified selection across lanes, support sizes and seeds. All defaults fit the full pilot.
    selected = select_stratified_jobs(jobs, args.max_attempts, args.selection_seed)
    run_id = args.run_id or f"pilot-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:6]}"
    manifest = probe_machine_manifest(MACHINE_ID, notes="SIRIUS Ubuntu laptop campaign; GPU restricted to uint64 reversible basis-row parity/measurement.")
    manifest_errors = validate_manifest(manifest)
    if manifest_errors: raise SystemExit("Machine manifest invalid: " + "; ".join(manifest_errors))
    outroot = args.results_root
    plan_dir = outroot / "manifests" / MACHINE_ID
    if args.dry_run:
        print(json.dumps({"run_id": run_id, "selected_attempts": len(selected), "tracks": {t: sum(j["track"] == t for j in selected) for t in ("paper_reproduction", "symmetry_structured_sparse_supports")}, "gpu_enabled": not args.no_gpu and bool(manifest["gpu_devices"]), "excluded": excluded, "jobs": selected}, indent=2))
        return 0
    plan_dir.mkdir(parents=True, exist_ok=True)
    diff_result = subprocess.run(["git", "diff", "HEAD", "--binary"], cwd=ROOT, capture_output=True, check=True)
    diff_sha256 = hashlib.sha256(diff_result.stdout).hexdigest()
    (plan_dir / f"{run_id}_source.diff").write_bytes(diff_result.stdout)
    untracked_result = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    untracked = []
    for name in untracked_result.stdout.decode().split("\0"):
        if name:
            path = ROOT / name
            if path.is_file(): untracked.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    source_manifest = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                       "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                       "tracked_diff_sha256": diff_sha256, "untracked_file_hashes": untracked,
                       "captured_at_utc": utc()}
    RUN_SOURCE_MANIFEST_SHA256 = hashlib.sha256(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    source_manifest["source_manifest_sha256"] = RUN_SOURCE_MANIFEST_SHA256
    (plan_dir / f"{run_id}_source_manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    (plan_dir / f"{run_id}_plan.json").write_text(json.dumps({"plan_id": PLAN_ID, "version": "1.0.0", "selection_seed": args.selection_seed,
        "max_attempts": args.max_attempts, "selected": selected, "excluded": excluded, "machine_id": MACHINE_ID,
        "source_diff_sha256": diff_sha256, "source_manifest_sha256": RUN_SOURCE_MANIFEST_SHA256}, indent=2) + "\n")
    manifest_path = plan_dir / f"{run_id}_machine_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    checkpoint_dir = outroot / "checkpoints" / MACHINE_ID
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"{run_id}.json"
    # Checkpointed raw files are the canonical source of truth and allow exact resume by job ID.
    paths = {
        "paper_reproduction": outroot / "raw" / MACHINE_ID / "paper_reproduction" / f"{run_id}.jsonl",
        "symmetry_structured_sparse_supports": outroot / "raw" / MACHINE_ID / "extensions" / "symmetry_structured_sparse_supports" / f"{run_id}.jsonl",
    }
    for path in paths.values(): path.parent.mkdir(parents=True, exist_ok=True)
    completed_ids = collect_completed_job_ids(list(paths.values()))
    checkpoint = {"run_id": run_id, "plan_id": PLAN_ID, "machine_id": MACHINE_ID, "completed_job_ids": sorted(completed_ids), "updated_at_utc": utc()}
    checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n")
    gpu_enabled = not args.no_gpu and bool(manifest["gpu_devices"])
    counts = {k: 0 for k in ("completed", "failed", "skipped", "timed_out", "invalid")}
    for index, job in enumerate(selected, 1):
        job_id = job_identity(job)
        if job_id in completed_ids:
            print(f"RESUME_SKIP {index}/{len(selected)} {job_id}")
            continue
        mem = available_memory_bytes()
        gpu_probe = thermal_gpu_state()
        if mem is not None and mem < 1_500_000_000 or gpu_enabled and gpu_probe.get("temperature_c", 0) >= 82:
            rec = nonexecution_record(job, run_id, manifest, "skipped", "resource guard: available RAM below 1.5 GB or GPU temperature at/above 82 C")
        else:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(180)
            try:
                rec = execute_job(job, run_id, manifest, gpu_enabled, args.gpu_memory_budget_fraction)
            except AttemptTimeout as exc:
                rec = nonexecution_record(job, run_id, manifest, "timed_out", str(exc))
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        rec["selection_index"] = index
        try:
            import jsonschema
            validator = jsonschema.Draft202012Validator(json.loads((ROOT / "benchmarking/schemas/ubuntu-attempt.schema.json").read_text()))
            errors = [error.message for error in validator.iter_errors(rec)]
        except Exception as exc:
            errors = [f"schema validation error: {type(exc).__name__}: {exc}"]
        if errors:
            rec["status"] = "invalid"
            rec["schema_errors"] = errors
        dest = paths[job["track"]]
        with dest.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(rec, sort_keys=True, allow_nan=False) + "\n"); stream.flush(); os.fsync(stream.fileno())
        completed_ids.add(job_id)
        checkpoint = {"run_id": run_id, "plan_id": PLAN_ID, "machine_id": MACHINE_ID, "completed_job_ids": sorted(completed_ids),
                      "last_selection_index": index, "updated_at_utc": utc()}
        temp_checkpoint = checkpoint_path.with_suffix(".tmp")
        temp_checkpoint.write_text(json.dumps(checkpoint, indent=2) + "\n")
        os.replace(temp_checkpoint, checkpoint_path)
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        print(f"{rec['status'].upper()} {index}/{len(selected)} {job['track']} {job['algorithm_id']} n={job['n']} s={job['s']} seed={job['seed']}" + (f" gpu={rec.get('gpu',{}).get('status')}" if gpu_enabled and job['algorithm_id'] in ("independent_batched_isometry","malvetti_baseline") else ""), flush=True)
    print(json.dumps({"run_id": run_id, "attempts": counts, "gpu_enabled": gpu_enabled, "raw_paths": {k: str(v) for k,v in paths.items()}}, indent=2))
    return 0 if counts["failed"] == 0 and counts["invalid"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
