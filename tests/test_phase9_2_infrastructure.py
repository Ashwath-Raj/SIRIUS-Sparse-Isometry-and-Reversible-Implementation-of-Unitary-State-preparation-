"""Unit and integration tests for Phase 9.2 benchmark infrastructure."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from benchmarking.runners.environment_probe import (
    probe_machine_manifest,
    probe_run_environment,
    validate_manifest,
)
from benchmarking.runners.run_benchmarks import (
    compute_support_hash,
    generate_coefficients,
    generate_signs,
    generate_support,
    run_benchmark_job,
    validate_run_record,
)
from benchmarking.analysis.aggregate import (
    aggregate_records,
    compute_quantiles,
    validate_summary,
)


class Phase92InfrastructureTests(unittest.TestCase):
    def test_environment_probe_validates_against_schema(self) -> None:
        manifest = probe_machine_manifest(machine_id="test-runner", notes="Test manifest")
        errors = validate_manifest(manifest)
        self.assertEqual(errors, [], f"Manifest failed validation: {errors}")

    def test_run_environment_probe_shape(self) -> None:
        env = probe_run_environment("test-host")
        for key in ("hostname_alias", "os", "python", "cpu_model", "gpu_devices"):
            self.assertIn(key, env)
        self.assertIsInstance(env["gpu_devices"], list)

    def test_deterministic_workload_generation(self) -> None:
        sup1 = generate_support(n=4, s=3, family="seeded_random", seed=42)
        sup2 = generate_support(n=4, s=3, family="seeded_random", seed=42)
        self.assertEqual(sup1, sup2)
        self.assertEqual(len(set(sup1)), 3)

        c1 = generate_coefficients(s=3, family="uniform_real_positive", seed=42)
        c2 = generate_coefficients(s=3, family="uniform_real_positive", seed=42)
        self.assertEqual(c1, c2)

        s1 = generate_signs(s=3, profile="random_pm_one", seed=42)
        s2 = generate_signs(s=3, profile="random_pm_one", seed=42)
        self.assertEqual(s1, s2)

        h1 = compute_support_hash(sup1)
        h2 = compute_support_hash(sup2)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_run_single_benchmark_job_validates_record(self) -> None:
        env = probe_run_environment("test-host")
        record = run_benchmark_job(
            plan_id="phase9-cross-device-v1",
            tier="smoke",
            algorithm_id="independent_batched_isometry",
            n=4,
            s=3,
            seed=101,
            support_family="seeded_random",
            coefficient_family="uniform_real_positive",
            sign_profile="all_positive",
            run_id="test_run_001",
            repetitions=1,
            warmups=1,
            timeout_sec=10.0,
            enable_gpu=False,
            environment=env,
            paper_doi="10.22331/q-2026-09-10-2208",
            artifact_md5="c58634ba415b4e3fb729648460f32ad7",
        )
        self.assertEqual(record["status"], "completed")
        errors = validate_run_record(record)
        self.assertEqual(errors, [], f"Run record failed schema validation: {errors}")

    def test_aggregation_and_summary_validation(self) -> None:
        env = probe_run_environment("test-host")
        record1 = run_benchmark_job(
            plan_id="phase9-cross-device-v1",
            tier="smoke",
            algorithm_id="independent_batched_isometry",
            n=4,
            s=3,
            seed=101,
            support_family="seeded_random",
            coefficient_family="uniform_real_positive",
            sign_profile="all_positive",
            run_id="test_run_002",
            repetitions=1,
            warmups=0,
            timeout_sec=10.0,
            enable_gpu=False,
            environment=env,
            paper_doi="10.22331/q-2026-09-10-2208",
            artifact_md5="c58634ba415b4e3fb729648460f32ad7",
        )
        record2 = run_benchmark_job(
            plan_id="phase9-cross-device-v1",
            tier="smoke",
            algorithm_id="malvetti_baseline",
            n=4,
            s=3,
            seed=101,
            support_family="seeded_random",
            coefficient_family="uniform_real_positive",
            sign_profile="all_positive",
            run_id="test_run_002",
            repetitions=1,
            warmups=0,
            timeout_sec=10.0,
            enable_gpu=False,
            environment=env,
            paper_doi="10.22331/q-2026-09-10-2208",
            artifact_md5="c58634ba415b4e3fb729648460f32ad7",
        )

        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as tf:
            tf.write(json.dumps(record1) + "\n")
            tf.write(json.dumps(record2) + "\n")
            temp_path = Path(tf.name)

        try:
            summary = aggregate_records([temp_path])
            errors = validate_summary(summary)
            self.assertEqual(errors, [], f"Summary schema validation failed: {errors}")
            self.assertGreater(len(summary["groups"]), 0)
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
