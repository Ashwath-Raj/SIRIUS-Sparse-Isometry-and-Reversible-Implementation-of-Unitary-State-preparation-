from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phase9_1_validate.py"
PLAN = ROOT / "benchmarking" / "config" / "phase9_1_benchmark_plan.json"


class Phase91DesignTests(unittest.TestCase):
    def test_plan_validates_without_loading_algorithm_modules(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--plan", str(PLAN)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Phase 9.1 plan validation: PASS", result.stdout)
        self.assertIn("No benchmark code was imported or executed.", result.stdout)

    def test_smoke_manifest_is_dry_run_and_deterministically_described(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "manifest.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--plan", str(PLAN), "--tier", "smoke", "--emit-manifest", str(out)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(manifest["manifest_type"], "dry_run_planned_work_not_measurements")
            self.assertGreater(manifest["job_count"], 0)
            self.assertGreaterEqual(manifest["excluded_case_count"], 0)
            self.assertTrue(all(job["execution_status"] == "planned_not_executed" for job in manifest["jobs"]))
            self.assertTrue(any(job["job_type"] == "isometry_comparison" for job in manifest["jobs"]))
            self.assertTrue(any(job["job_type"] == "end_to_end_state_preparation" for job in manifest["jobs"]))
            for job in manifest["jobs"]:
                if job["job_type"] == "isometry_comparison":
                    self.assertEqual(job["coefficient_family"], "not_applicable")
                    self.assertEqual(job["sign_profile"], "not_applicable")
                    self.assertIn("malvetti_baseline", job["method_ids"])
                else:
                    self.assertNotEqual(job["coefficient_family"], "not_applicable")

    def test_repeated_prefix_eligibility_matches_capacity_rule(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import phase9_1_validate as validator
        self.assertTrue(validator.repeated_prefix_eligible(8, 16))
        self.assertFalse(validator.repeated_prefix_eligible(8, 32))

    def test_all_json_contract_files_parse(self):
        paths = [
            PLAN,
            ROOT / "benchmarking" / "metric_catalog.json",
            ROOT / "benchmarking" / "schemas" / "run-record.schema.json",
            ROOT / "benchmarking" / "schemas" / "machine-manifest.schema.json",
            ROOT / "benchmarking" / "schemas" / "summary.schema.json",
            ROOT / "benchmarking" / "templates" / "run_record.template.json",
            ROOT / "benchmarking" / "templates" / "machine_manifest.template.json",
        ]
        for path in paths:
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
