#!/usr/bin/env python3
"""Deterministic random-support verification for Phase 6 Algorithm 1."""
from __future__ import annotations

import json
import random

from sparseprep.batched_isometry import run_batched_isometry
from sparseprep.model import SparseStateProblem


def main() -> None:
    rng = random.Random(20261114)
    passed = 0
    method_counts = {"direct": 0, "swap": 0, "toffoli": 0}
    final_repairs = 0
    eq1_not_reported = 0
    eq1_violations = []

    for n in range(2, 9):
        for s in range(1, min(12, 1 << n) + 1):
            for _ in range(50):
                values = rng.sample(range(1 << n), s)
                support = tuple(format(value, f"0{n}b") for value in values)
                result = run_batched_isometry(SparseStateProblem(n, support))
                result.verify()
                passed += 1
                for step in result.batch_steps:
                    method_counts[step.method] += 1
                final_repairs += result.resources.final_collision_repair_count
                bound = result.resources.equation_1_isometry_upper_bound
                if bound is None:
                    eq1_not_reported += 1
                elif result.resources.total_paper_accounted_toffolis > bound + 1e-9:
                    eq1_violations.append({
                        "n": n, "s": s, "support": support,
                        "actual": result.resources.total_paper_accounted_toffolis,
                        "bound": bound,
                    })

    report = {
        "seed": 20261114,
        "cases_verified": passed,
        "batch_build_methods": method_counts,
        "final_collision_repairs": final_repairs,
        "eq1_not_reported_out_of_domain_or_boundary": eq1_not_reported,
        "eq1_bound_violations": len(eq1_violations),
    }
    print(json.dumps(report, indent=2))
    if passed != 3600 or eq1_violations:
        raise SystemExit(f"Phase 6 fuzz validation failed: {eq1_violations[:3]}")


if __name__ == "__main__":
    main()
