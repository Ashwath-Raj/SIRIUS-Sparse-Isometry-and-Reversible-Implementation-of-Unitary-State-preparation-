#!/usr/bin/env python3
"""Validate the Phase 9.1 benchmark plan and emit a dry-run workload manifest.

This tool deliberately does not import candidate algorithms, touch CUDA, or
execute measurements. It freezes the planned work for Phase 9.2 only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_SUPPORT_FAMILIES = {
    "seeded_random", "zero_residual_subspace", "repeated_prefix"
}
VALID_COEFFICIENT_FAMILIES = {
    "uniform_real_positive", "random_real_positive", "random_complex"
}
VALID_SIGN_PROFILES = {"all_positive", "random_pm_one"}


class PlanValidationError(ValueError):
    """Raised when the benchmark plan is internally inconsistent."""


def ceil_log2_positive(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("value must be a positive integer")
    return (value - 1).bit_length()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanValidationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanValidationError(f"top-level JSON value must be an object: {path}")
    return value


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("plan_version", "plan_id", "project", "comparison_methods", "workload_families", "tiers", "measurement_policy", "correctness_policy", "guardrails"):
        if key not in plan:
            errors.append(f"missing required top-level key: {key}")
    if errors:
        return errors

    project = plan["project"]
    if not isinstance(project, dict) or not project.get("paper_doi"):
        errors.append("project.paper_doi must be a non-empty string")

    methods = plan["comparison_methods"]
    if not isinstance(methods, list) or not methods:
        errors.append("comparison_methods must be a non-empty array")
    else:
        ids = [m.get("id") for m in methods if isinstance(m, dict)]
        if len(ids) != len(methods) or len(set(ids)) != len(ids) or any(not x for x in ids):
            errors.append("comparison_methods must contain unique non-empty ids")
        for method in methods:
            if not isinstance(method, dict):
                continue
            if not isinstance(method.get("automated_in_9_2"), bool):
                errors.append(f"method {method.get('id')}: automated_in_9_2 must be boolean")
            if method.get("scope") not in {"isometry", "end_to_end"}:
                errors.append(f"method {method.get('id')}: scope must be isometry or end_to_end")
            if not method.get("entrypoint") and method.get("automated_in_9_2"):
                errors.append(f"method {method.get('id')}: automated method requires an entrypoint")
            if not method.get("automated_in_9_2") and not method.get("blocked_reason"):
                errors.append(f"method {method.get('id')}: manual method must explain its blocker")

    families = plan["workload_families"]
    for key, valid in (("support", VALID_SUPPORT_FAMILIES), ("coefficients", VALID_COEFFICIENT_FAMILIES), ("sign_profiles", VALID_SIGN_PROFILES)):
        values = families.get(key, []) if isinstance(families, dict) else []
        ids = [x.get("id") for x in values if isinstance(x, dict)]
        if len(ids) != len(values) or len(set(ids)) != len(ids):
            errors.append(f"workload_families.{key} must have unique object ids")
        unknown = set(ids) - valid
        if unknown:
            errors.append(f"unknown {key} ids: {sorted(unknown)}")

    tiers = plan["tiers"]
    if not isinstance(tiers, dict) or not tiers:
        errors.append("tiers must be a non-empty object")
    else:
        for tier_name, tier in tiers.items():
            if not isinstance(tier, dict):
                errors.append(f"tier {tier_name} must be an object")
                continue
            required = ("n_values", "s_values", "seeds", "support_families", "coefficient_families", "sign_profiles", "repetitions", "warmups", "timeout_seconds_per_compile")
            missing = [x for x in required if x not in tier]
            if missing:
                errors.append(f"tier {tier_name} missing {missing}")
                continue
            for field in ("n_values", "s_values", "seeds"):
                values = tier[field]
                if not isinstance(values, list) or not values:
                    errors.append(f"tier {tier_name}.{field} must be a non-empty array")
                elif any(isinstance(v, bool) or not isinstance(v, int) for v in values):
                    errors.append(f"tier {tier_name}.{field} must contain integers")
                elif len(set(values)) != len(values):
                    errors.append(f"tier {tier_name}.{field} contains duplicates")
            if isinstance(tier.get("n_values"), list) and any(n < 1 or n > 63 for n in tier["n_values"] if isinstance(n, int) and not isinstance(n, bool)):
                errors.append(f"tier {tier_name}.n_values must be between 1 and 63 for the current uint64 GPU lane")
            if isinstance(tier.get("s_values"), list) and any(s < 1 for s in tier["s_values"] if isinstance(s, int) and not isinstance(s, bool)):
                errors.append(f"tier {tier_name}.s_values must be positive")
            for n in tier.get("n_values", []) if isinstance(tier.get("n_values"), list) else []:
                for s in tier.get("s_values", []) if isinstance(tier.get("s_values"), list) else []:
                    if isinstance(n, int) and isinstance(s, int) and not isinstance(n, bool) and not isinstance(s, bool) and s > (1 << n):
                        errors.append(f"tier {tier_name}: support size s={s} exceeds 2**n for n={n}")
            for field, valid in (("support_families", VALID_SUPPORT_FAMILIES), ("coefficient_families", VALID_COEFFICIENT_FAMILIES), ("sign_profiles", VALID_SIGN_PROFILES)):
                values = tier.get(field, [])
                if not isinstance(values, list) or not values:
                    errors.append(f"tier {tier_name}.{field} must be a non-empty array")
                elif set(values) - valid:
                    errors.append(f"tier {tier_name}.{field} has unknown values {sorted(set(values)-valid)}")
            for field, minimum in (("repetitions", 1), ("warmups", 0), ("timeout_seconds_per_compile", 1)):
                value = tier.get(field)
                if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                    errors.append(f"tier {tier_name}.{field} must be an integer >= {minimum}")
    return errors


def repeated_prefix_eligible(n: int, s: int) -> bool:
    ell = ceil_log2_positive(s)
    residual_width = n - ell
    return residual_width >= 0 and s <= (1 << residual_width)


def build_manifest(plan: dict[str, Any], tier_name: str | None = None) -> dict[str, Any]:
    errors = validate_plan(plan)
    if errors:
        raise PlanValidationError("\n".join(errors))
    tiers = plan["tiers"]
    selected = [tier_name] if tier_name else list(tiers)
    unknown = set(selected) - set(tiers)
    if unknown:
        raise PlanValidationError(f"unknown tier(s): {sorted(unknown)}")

    methods = [m for m in plan["comparison_methods"] if m.get("automated_in_9_2")]
    isometry_methods = [m["id"] for m in methods if m.get("scope") == "isometry"]
    stateprep_methods = [m["id"] for m in methods if m.get("scope") == "end_to_end"]
    if not isometry_methods or not stateprep_methods:
        raise PlanValidationError("plan must include at least one automated isometry method and one end-to-end method")
    jobs: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for name in selected:
        tier = tiers[name]
        for n in tier["n_values"]:
            for s in tier["s_values"]:
                if s > (1 << n):
                    continue
                ell = ceil_log2_positive(s)
                for support_family in tier["support_families"]:
                    if support_family == "repeated_prefix" and not repeated_prefix_eligible(n, s):
                        exclusions.append({"tier": name, "n": n, "s": s, "support_family": support_family,
                                           "reason": "insufficient residual suffix capacity for distinct repeated-prefix rows"})
                        continue
                    for seed in tier["seeds"]:
                        base = {
                            "tier": name, "n": n, "s": s, "ell": ell,
                            "seed": seed, "support_family": support_family,
                            "repetitions": tier["repetitions"], "warmups": tier["warmups"],
                            "timeout_seconds_per_compile": tier["timeout_seconds_per_compile"]
                        }
                        # Isometry comparison does not depend on coefficient values or phase metadata.
                        jobs.append({
                            "job_key": f"{name}-n{n}-s{s}-{support_family}-seed{seed}-isometry",
                            **base,
                            "job_type": "isometry_comparison",
                            "coefficient_family": "not_applicable",
                            "sign_profile": "not_applicable",
                            "method_ids": isometry_methods,
                            "external_reference_status": "adapter_required",
                            "execution_status": "planned_not_executed"
                        })
                        # Full preparation sweeps vary complex coefficients and independent sign metadata.
                        for coefficient_family in tier["coefficient_families"]:
                            for sign_profile in tier["sign_profiles"]:
                                jobs.append({
                                    "job_key": f"{name}-n{n}-s{s}-{support_family}-{coefficient_family}-{sign_profile}-seed{seed}-stateprep",
                                    **base,
                                    "job_type": "end_to_end_state_preparation",
                                    "coefficient_family": coefficient_family,
                                    "sign_profile": sign_profile,
                                    "method_ids": stateprep_methods,
                                    "external_reference_status": "not_applicable",
                                    "execution_status": "planned_not_executed"
                                })
    return {
        "manifest_version": "1.0.0",
        "manifest_type": "dry_run_planned_work_not_measurements",
        "plan_id": plan["plan_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_tiers": selected,
        "execution_notice": "No algorithms were imported or executed. This file enumerates intended Phase 9.2 jobs only.",
        "job_count": len(jobs),
        "excluded_case_count": len(exclusions),
        "jobs": jobs,
        "excluded_cases": exclusions
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("benchmarking/config/phase9_1_benchmark_plan.json"))
    parser.add_argument("--tier", choices=("smoke", "scaling", "stress"), help="select one tier; default validates/enumerates all")
    parser.add_argument("--emit-manifest", type=Path, help="write a dry-run manifest; does not execute measurements")
    args = parser.parse_args(argv)
    try:
        plan = load_json(args.plan)
        errors = validate_plan(plan)
        if errors:
            raise PlanValidationError("\n".join(errors))
        manifest = build_manifest(plan, args.tier)
        summary = {k: manifest[k] for k in ("manifest_type", "plan_id", "selected_tiers", "job_count", "excluded_case_count")}
        print("Phase 9.1 plan validation: PASS")
        print(json.dumps(summary, indent=2))
        if args.emit_manifest:
            args.emit_manifest.parent.mkdir(parents=True, exist_ok=True)
            args.emit_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"Dry-run manifest written: {args.emit_manifest}")
        print("No benchmark code was imported or executed.")
        return 0
    except (PlanValidationError, OSError) as exc:
        print(f"Phase 9.1 validation: FAIL\n{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
