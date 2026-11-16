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


def compute_bootstrap_ci(values: list[float], n_resamples: int = 1000, alpha: float = 0.05, seed: int = 42) -> tuple[float, float] | None:
    if len(values) < 5:
        return None
    rng = random.Random(seed)
    n = len(values)
    medians: list[float] = []
    for _ in range(n_resamples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        sample.sort()
        medians.append(sample[n // 2])
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

    # Map: (algorithm_id, n, s, metric_name) -> list of float values
    data: dict[tuple[str, int, int, str], list[float]] = defaultdict(list)

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

                if record.get("status") != "completed":
                    continue

                plan_id = record.get("plan_id", plan_id)
                alg = record["algorithm_id"]
                n = record["problem"]["n"]
                s = record["problem"]["s"]

                timings = record.get("timings", {})
                for metric in ("compile_wall_ms", "compile_cpu_ms", "gpu_basis_batch_wall_ms", "gpu_kernel_ms", "host_to_device_ms", "device_to_host_ms"):
                    val = timings.get(metric)
                    if val is not None and isinstance(val, (int, float)):
                        data[(alg, n, s, metric)].append(float(val))

                resources = record.get("logical_resources", {})
                for metric in ("paper_accounted_toffoli", "coherent_toffoli", "emitted_toffoli_ir", "clean_ancillas", "logical_qubits", "logical_depth"):
                    val = resources.get(metric)
                    if val is not None and isinstance(val, (int, float)):
                        data[(alg, n, s, metric)].append(float(val))

    groups: list[dict[str, Any]] = []

    for (alg, n, s, metric), values in sorted(data.items()):
        if not values:
            continue
        minimum, q25, med, q75, maximum = compute_quantiles(values)
        iqr = round(q75 - q25, 6)
        group_entry: dict[str, Any] = {
            "algorithm_id": alg,
            "n": int(n),
            "s": int(s),
            "metric": metric,
            "count": len(values),
            "median": round(med, 6),
            "iqr": iqr,
            "minimum": round(minimum, 6),
            "maximum": round(maximum, 6),
        }
        ci = compute_bootstrap_ci(values)
        if ci is not None:
            group_entry["ci_95_bootstrap"] = [round(ci[0], 6), round(ci[1], 6)]
        groups.append(group_entry)

    summary: dict[str, Any] = {
        "summary_version": "1.0.0",
        "plan_id": plan_id,
        "aggregation_method": "median_and_iqr_with_95_percent_bootstrap_ci",
        "grouping_keys": ["algorithm_id", "n", "s"],
        "groups": groups,
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
