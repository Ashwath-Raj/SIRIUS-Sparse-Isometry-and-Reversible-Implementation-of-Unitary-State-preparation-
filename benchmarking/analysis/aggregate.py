"""Statistical aggregation and summary emitter for SIRIUS benchmark records.

Validates raw JSONL records against run-record.schema.json, groups by algorithm, n, and s,
computes non-parametric summary statistics (median, IQR, min, max) and 95% bootstrap
confidence intervals, and validates output against summary.schema.json.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any

SUMMARY_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "summary.schema.json"
RUN_RECORD_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "run-record.schema.json"


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_quantiles(values: list[float]) -> tuple[float, float, float, float, float]:
    """Returns (min, q25, median, q75, max)."""
    if not values:
        raise ValueError("Cannot compute quantiles of empty list")
    vals = sorted(values)
    n = len(vals)
    minimum = vals[0]
    maximum = vals[-1]

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return vals[int(k)]
        d0 = vals[int(f)] * (c - k)
        d1 = vals[int(c)] * (k - f)
        return d0 + d1

    q25 = percentile(0.25)
    med = percentile(0.50)
    q75 = percentile(0.75)
    return minimum, q25, med, q75, maximum


def metric_unit(metric: str) -> str:
    if metric.endswith("_ms"):
        return "ms"
    if metric.endswith("_bytes"):
        return "bytes"
    if metric in {"paper_accounted_toffoli", "coherent_toffoli", "emitted_toffoli_ir", "dense_loader_emitted_toffoli", "sign_oracle_emitted_toffoli", "inverse_isometry_emitted_toffoli", "marker_cleanup_emitted_toffoli", "end_to_end_emitted_toffoli_ir"}:
        return "Toffoli gates"
    if metric in {"clean_ancillas", "logical_qubits"}:
        return "qubits"
    if metric == "emitted_operation_count":
        return "operations"
    if metric == "logical_depth":
        return "scheduled layers"
    if metric == "run_status":
        return "attempts"
    return "unitless"


def compute_bootstrap_ci(values: list[float], n_resamples: int = 1000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float] | None:
    if len(values) < 5:
        return None
    rng = random.Random(seed)
    n = len(values)
    medians: list[float] = []
    for _ in range(n_resamples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        medians.append(compute_quantiles(sample)[2])
    medians.sort()
    lower_idx = int((alpha / 2.0) * n_resamples)
    upper_idx = int((1.0 - alpha / 2.0) * n_resamples)
    return medians[lower_idx], medians[upper_idx]


def validate_summary(summary_data: dict[str, Any], schema_file: Path | None = None) -> list[str]:
    path = schema_file or SUMMARY_SCHEMA_PATH
    if not path.exists():
        return [f"Schema file not found: {path}"]
    try:
        import jsonschema
        schema = json.loads(path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        return [f"{e.json_path}: {e.message}" for e in validator.iter_errors(summary_data)]
    except ImportError:
        for k in ("summary_version", "plan_id", "aggregation_method", "grouping_keys", "groups", "source_record_hashes"):
            if k not in summary_data:
                return [f"Missing required key: {k}"]
        return []


def aggregate_records(record_files: list[Path], plan_id_override: str | None = None) -> dict[str, Any]:
    file_hashes: list[str] = []
    plan_id = plan_id_override or "phase9-cross-device-v1"
    observed_plan_ids: set[str] = set()
    # Replicates are independent seeds. Repeated records for one seed are first
    # collapsed to a per-seed median; environment/workload strata never mix.
    fields = (
        "support_family", "coefficient_family", "sign_profile", "backend",
        "cpu_model", "gpu_identity", "hardware_fingerprint", "python",
        "compiler_version", "runtime_version", "benchmark_configuration",
        "reference_artifact_digest", "input_identity_sha256",
        "source_version_sha256",
    )
    observations: dict[tuple[tuple[Any, ...], str, int], list[float]] = defaultdict(list)
    pairing: dict[tuple[str, str, str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    statuses: dict[tuple[Any, ...], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stratum_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    record_validation_errors: list[dict[str, Any]] = []

    for rf in record_files:
        if not rf.exists():
            continue
        file_hashes.append(sha256_file(rf))

        with rf.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Warning: JSON decode error in {rf}:{line_no}: {exc}", file=sys.stderr)
                    continue

                plan_id = record.get("plan_id", plan_id)
                observed_plan_ids.add(str(record.get("plan_id", "legacy_unknown")))
                problem = record.get("problem", {})
                env = record.get("environment", {})
                provenance = record.get("provenance", {})
                identity = record.get("input_identity", {})
                hardware = {
                    "cpu_model": env.get("cpu_model", env.get("cpu", {}).get("model", "legacy_unknown")),
                    "gpu_identity": env.get("gpu_devices", "legacy_unknown"),
                    "hardware_fingerprint": env.get("hardware_fingerprint", "legacy_unknown"),
                    "python": env.get("python", "legacy_unknown"),
                    "compiler_version": env.get("compiler_version", "not_applicable"),
                    "runtime_version": env.get("runtime_version", "not_applicable"),
                }
                values = {
                    "algorithm_id": record.get("algorithm_id", "legacy_unknown"),
                    "n": problem.get("n", -1), "s": problem.get("s", -1),
                    "support_family": problem.get("support_family", "legacy_unknown"),
                    "coefficient_family": problem.get("coefficient_family", "legacy_unknown"),
                    "sign_profile": problem.get("sign_profile", "legacy_unknown"),
                    "backend": record.get("backend", "cpu_compile"),
                    **hardware,
                    "benchmark_configuration": record.get("benchmark_configuration", {"plan_id": record.get("plan_id"), "tier": record.get("tier")}),
                    "reference_artifact_digest": provenance.get("artifact_sha256", provenance.get("artifact_md5", "legacy_unknown")),
                    "input_identity_sha256": identity.get("sha256", problem.get("support_sha256", "legacy_unknown")),
                    "source_version_sha256": provenance.get("source_diff_sha256", provenance.get("git_commit", "legacy_unknown")),
                }
                stratum = tuple(json.dumps(values[k], sort_keys=True, separators=(",", ":"), default=str) for k in ("algorithm_id", "n", "s", *fields))
                stratum_rows[stratum] = values
                status = record.get("status", "invalid")
                validation_errors: list[str] = []
                try:
                    from benchmarking.runners.run_benchmarks import validate_run_record
                    validation_errors = validate_run_record(record)
                except Exception as exc:
                    validation_errors = [f"validator_error: {type(exc).__name__}: {exc}"]
                if validation_errors:
                    record_validation_errors.append({"file": str(rf), "line": line_no, "run_id": record.get("run_id"), "errors": validation_errors})
                    status = "schema_invalid"
                statuses[stratum][status] += 1
                gpu_status = record.get("timings", {}).get("gpu_execution_status")
                if gpu_status is not None:
                    statuses[stratum][f"gpu_{gpu_status}"] += 1
                if status != "completed":
                    continue
                seed = record.get("seed", -1)
                environment_identity = {
                    key: env.get(key) for key in (
                        "os", "python", "cpu_model", "gpu_devices", "cuda_version", "cupy_version", "ram_bytes",
                        "compiler_version", "runtime_version",
                    )
                }
                environment_sha = hashlib.sha256(json.dumps(environment_identity, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
                comparison_context = {
                    "input_identity_sha256": identity.get("sha256", problem.get("support_sha256", "legacy_unknown")),
                    "seed": seed, "environment_sha256": environment_sha,
                    "benchmark_configuration": record.get("benchmark_configuration", {"plan_id": record.get("plan_id"), "tier": record.get("tier")}),
                    "reference_artifact_digest": provenance.get("artifact_sha256", provenance.get("artifact_md5", "legacy_unknown")),
                    "source_version_sha256": provenance.get("source_diff_sha256", provenance.get("git_commit", "legacy_unknown")),
                }
                pair_context_sha = hashlib.sha256(json.dumps(comparison_context, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
                pair_base = (pair_context_sha, str(seed), environment_sha)

                timings = record.get("timings", {})
                for metric in ("compile_wall_ms", "compile_cpu_ms", "gpu_basis_batch_wall_ms", "gpu_kernel_ms", "host_to_device_ms", "device_to_host_ms"):
                    val = timings.get(metric)
                    if val is not None and isinstance(val, (int, float)):
                        observations[(stratum, metric, seed)].append(float(val))
                        pairing[(pair_base[0], str(pair_base[1]), pair_base[2], metric)][record["algorithm_id"]].append(float(val))

                resources = record.get("logical_resources", {})
                for metric in ("paper_accounted_toffoli", "coherent_toffoli", "emitted_toffoli_ir", "emitted_operation_count", "dense_loader_emitted_toffoli", "sign_oracle_emitted_toffoli", "inverse_isometry_emitted_toffoli", "marker_cleanup_emitted_toffoli", "end_to_end_emitted_toffoli_ir", "clean_ancillas", "logical_qubits", "logical_depth"):
                    val = resources.get(metric)
                    if val is not None and isinstance(val, (int, float)):
                        observations[(stratum, metric, seed)].append(float(val))
                        pairing[(pair_base[0], str(pair_base[1]), pair_base[2], metric)][record["algorithm_id"]].append(float(val))

    groups: list[dict[str, Any]] = []

    grouped_metrics: dict[tuple[tuple[Any, ...], str], dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (stratum, metric, seed), values in observations.items():
        grouped_metrics[(stratum, metric)][seed].extend(values)
    for (stratum, metric), per_seed in sorted(grouped_metrics.items(), key=lambda item: repr(item[0])):
        values = [sorted(seed_values)[len(seed_values) // 2] for seed_values in per_seed.values()]
        if not values:
            continue
        minimum, q25, med, q75, maximum = compute_quantiles(values)
        iqr = round(q75 - q25, 6)
        group_entry: dict[str, Any] = {
            **stratum_rows[stratum],
            "metric": metric,
            "unit": metric_unit(metric),
            "count": len(values),
            "mean": round(sum(values) / len(values), 6),
            "standard_deviation": round(math.sqrt(sum((v - sum(values) / len(values)) ** 2 for v in values) / (len(values) - 1)), 6) if len(values) > 1 else None,
            "median": round(med, 6),
            "iqr": iqr,
            "minimum": round(minimum, 6),
            "maximum": round(maximum, 6),
            "sample_unit": "independent_seed",
            "status_counts": dict(statuses[stratum]),
        }
        ci = compute_bootstrap_ci(values)
        if ci is not None:
            group_entry["ci_95_bootstrap"] = [round(ci[0], 6), round(ci[1], 6)]
        groups.append(group_entry)

    # Preserve strata for which every attempt failed/skipped/timed out instead
    # of making them disappear simply because no numerical metric exists.
    for stratum, counts in statuses.items():
        if any(entry.get("algorithm_id") == stratum_rows[stratum]["algorithm_id"]
               and entry.get("n") == stratum_rows[stratum]["n"]
               and entry.get("s") == stratum_rows[stratum]["s"]
               and all(entry.get(field) == stratum_rows[stratum][field] for field in fields)
               and entry.get("metric") == "run_status"
               for entry in groups):
            continue
        groups.append({**stratum_rows[stratum], "metric": "run_status", "unit": metric_unit("run_status"), "count": 0,
                       "median": 0, "iqr": 0, "minimum": 0, "maximum": 0,
                       "mean": None, "standard_deviation": None,
                       "sample_unit": "attempt", "status_counts": dict(counts)})

    paired_comparisons: list[dict[str, Any]] = []
    paired_values: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    algorithm_ids = sorted({alg for bucket in pairing.values() for alg in bucket})
    for (pair_context_sha, seed, environment_sha, metric), algorithms in pairing.items():
        for left_index, candidate in enumerate(algorithm_ids):
            if candidate not in algorithms:
                continue
            for reference in algorithm_ids[left_index + 1:]:
                if reference not in algorithms:
                    continue
                # Collapse repeated timer samples within an independent seed.
                left = sorted(algorithms[candidate])[len(algorithms[candidate]) // 2]
                right = sorted(algorithms[reference])[len(algorithms[reference]) // 2]
                paired_values[(candidate, reference, metric)]["difference"].append(left - right)
                if right != 0:
                    paired_values[(candidate, reference, metric)]["ratio"].append(left / right)
                paired_values[(candidate, reference, metric)]["pair_context"].append(pair_context_sha)
    for (candidate, reference, metric), vals in sorted(paired_values.items()):
        differences = vals["difference"]
        ratios = vals["ratio"]
        if differences:
            paired_comparisons.append({
                "candidate_algorithm_id": candidate, "reference_algorithm_id": reference,
                "metric": metric, "count": len(differences),
                "unit": metric_unit(metric),
                "paired_median_difference_candidate_minus_reference": compute_quantiles(differences)[2],
                "paired_median_ratio_candidate_over_reference": compute_quantiles(ratios)[2] if ratios else None,
                "pairing_keys": ["input_identity_sha256", "seed", "hardware_runtime_fingerprint", "benchmark_configuration", "reference_artifact_digest"],
                "pair_context_count": len(set(vals["pair_context"])),
            })

    summary: dict[str, Any] = {
        "summary_version": "2.0.0",
        "plan_id": plan_id_override or (next(iter(observed_plan_ids)) if len(observed_plan_ids) == 1 else "multiple"),
        "aggregation_method": "median_and_iqr_with_95_percent_bootstrap_ci",
        "grouping_keys": ["algorithm_id", "n", "s", *fields, "metric", "seed_as_replication_unit"],
        "groups": groups,
        "paired_comparisons": paired_comparisons,
        "record_validation_errors": record_validation_errors,
        "source_record_hashes": file_hashes,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate SIRIUS benchmark records into statistical summary.")
    parser.add_argument("--input", type=Path, default=Path("results/raw"), help="Path to JSONL record file or directory of JSONL records")
    parser.add_argument("--output", type=Path, default=Path("results/summaries/benchmark_summary.json"), help="Output summary JSON path")
    parser.add_argument("--plan-id", type=str, default=None, help="Plan ID override")
    args = parser.parse_args()

    files: list[Path] = []
    if args.input.is_file():
        files = [args.input]
    elif args.input.is_dir():
        files = sorted(args.input.glob("*.jsonl"))
    else:
        print(f"Error: input path not found: {args.input}", file=sys.stderr)
        return 1

    if not files:
        print(f"Error: no .jsonl files found in {args.input}", file=sys.stderr)
        return 1

    summary = aggregate_records(files, plan_id_override=args.plan_id)
    errors = validate_summary(summary)
    if errors:
        print("Summary schema validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("Summary schema validation: PASS")

    payload = json.dumps(summary, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote validated aggregated summary to: {args.output}")
        print(f"Summary contains {len(summary['groups'])} aggregated metric groups across {len(files)} raw record file(s).")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
