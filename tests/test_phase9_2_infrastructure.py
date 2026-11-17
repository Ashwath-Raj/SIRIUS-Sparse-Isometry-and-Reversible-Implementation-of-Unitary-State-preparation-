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
    compute_workload_identity,
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

    def test_ordered_support_hash_contract(self) -> None:
        support = ("001", "101", "111")
        self.assertEqual(compute_support_hash(support), compute_support_hash(tuple(support)))
        self.assertNotEqual(compute_support_hash(support), compute_support_hash(("111", "001", "101")))
        self.assertNotEqual(compute_support_hash(support, 3), compute_support_hash(("0001", "0101", "0111"), 4))
        self.assertNotEqual(compute_support_hash(support), compute_support_hash(("001", "100", "111")))
        with self.assertRaises(ValueError):
            compute_support_hash(())
        with self.assertRaises(ValueError):
            compute_support_hash(("01", "1x"))
        with self.assertRaises(ValueError):
            compute_support_hash(("01", "01"))

    def test_complete_workload_identity_includes_order_coefficients_signs_and_config(self) -> None:
        coeffs = generate_coefficients(3, "uniform_real_positive", 19)
        signs = generate_signs(3, "all_positive", 19)
        common = dict(n=3, coefficients=coeffs, signs=signs, support_family="fixture",
                      coefficient_family="uniform_real_positive", sign_profile="all_positive",
                      seed=19, workload_parameters={"tier": "smoke"})
        a = compute_workload_identity(support=("001", "101", "111"), **common)
        b = compute_workload_identity(support=("111", "001", "101"), **common)
        self.assertNotEqual(a["sha256"], b["sha256"])
        self.assertEqual(a["sha256"], compute_workload_identity(support=("001", "101", "111"), **common)["sha256"])

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

    def test_end_to_end_benchmark_executes_exact_statevector_verification(self) -> None:
        record = run_benchmark_job(
            plan_id="phase9-statevector-regression", tier="smoke",
            algorithm_id="end_to_end_state_preparation", n=4, s=3, seed=7,
            support_family="seeded_random", coefficient_family="random_complex",
            sign_profile="random_pm_one", run_id="statevector-regression",
            repetitions=1, warmups=0, timeout_sec=30.0, enable_gpu=False,
            environment=probe_run_environment("test-host"),
            paper_doi="10.22331/q-2026-09-10-2208",
            artifact_md5="c58634ba415b4e3fb729648460f32ad7",
        )
        self.assertEqual(record["status"], "completed", record.get("notes"))
        self.assertEqual(record["correctness"]["statevector_status"], "passed")
        self.assertGreaterEqual(record["correctness"]["fidelity"], 1.0 - 1e-7)
        self.assertLessEqual(record["correctness"]["workspace_leakage_probability"], 1e-7)

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
        unrelated = json.loads(json.dumps(record1))
        unrelated["run_id"] = "test_run_other_family"
        unrelated["problem"]["support_family"] = "different_support_family"
        unrelated["environment"]["cpu_model"] = "different CPU fingerprint"

        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as tf:
            tf.write(json.dumps(record1) + "\n")
            tf.write(json.dumps(record2) + "\n")
            tf.write(json.dumps(unrelated) + "\n")
            temp_path = Path(tf.name)

        try:
            summary = aggregate_records([temp_path])
            errors = validate_summary(summary)
            self.assertEqual(errors, [], f"Summary schema validation failed: {errors}")
            self.assertGreater(len(summary["groups"]), 0)
            self.assertTrue(all("unit" in group for group in summary["groups"]))
            compile_groups = [g for g in summary["groups"] if g["metric"] == "compile_wall_ms" and g["algorithm_id"] == "independent_batched_isometry"]
            self.assertEqual(len(compile_groups), 2)
            self.assertEqual({g["support_family"] for g in compile_groups}, {"seeded_random", "different_support_family"})
            self.assertEqual(len({g["cpu_model"] for g in compile_groups}), 2)
            self.assertTrue(any(p["count"] == 1 and p["metric"] == "compile_wall_ms" for p in summary["paired_comparisons"]))
        finally:
            temp_path.unlink(missing_ok=True)

    def test_aggregator_excludes_and_reports_schema_invalid_raw_records(self) -> None:
        record = run_benchmark_job(
            plan_id="schema-invalid-check", tier="smoke", algorithm_id="independent_batched_isometry",
            n=4, s=3, seed=4, support_family="seeded_random", coefficient_family="uniform_real_positive",
            sign_profile="all_positive", run_id="schema-invalid-check", repetitions=1, warmups=0,
            timeout_sec=10.0, enable_gpu=False, environment=probe_run_environment("test-host"),
            paper_doi="10.22331/q-2026-09-10-2208", artifact_md5="c58634ba415b4e3fb729648460f32ad7",
        )
        record["input_identity"]["sha256"] = "bad"
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as tf:
            tf.write(json.dumps(record) + "\n")
            temp_path = Path(tf.name)
        try:
            summary = aggregate_records([temp_path])
            self.assertEqual(len(summary["record_validation_errors"]), 1)
            self.assertIn("schema_invalid", summary["groups"][0]["status_counts"])
            self.assertFalse(any(g["metric"] == "compile_wall_ms" for g in summary["groups"]))
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
