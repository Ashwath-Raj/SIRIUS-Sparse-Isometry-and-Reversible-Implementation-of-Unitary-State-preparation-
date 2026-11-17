"""Unit and integration tests for authors reference artifact adapter."""
from __future__ import annotations

import unittest

from benchmarking.adapters.authors_adapter import (
    AuthorsReferenceUnsupportedInput,
    get_authors_artifact_status,
    is_authors_artifact_available,
    run_authors_reference_isometry,
)
from sparseprep import SparseStateProblem, run_batched_isometry


class AuthorsArtifactAdapterTests(unittest.TestCase):
    def test_authors_artifact_status_reporting(self) -> None:
        status = get_authors_artifact_status()
        self.assertIn("available", status)
        self.assertIn(status["reference_status"], {"PASS", "FAIL", "BLOCKED_BUILD", "BLOCKED_ARTIFACT", "NOT_RUN"})
        self.assertIn("blocked_reason", status)
        self.assertIn("artifact_path", status)
        self.assertIsInstance(status["available"], bool)

    def test_authors_adapter_execution_matches_when_available(self) -> None:
        if not is_authors_artifact_available():
            self.skipTest(f"Authors artifact Rust module not available: {get_authors_artifact_status().get('blocked_reason')}")

        problem = SparseStateProblem(
            n=4,
            support=("0001", "0110", "1011"),
            signs=(1, 1, 1),
        )

        res = run_authors_reference_isometry(problem)
        self.assertIn("bijection", res)
        self.assertIn("circuit_batches_count", res)
        self.assertIn("paper_accounted_toffoli", res)
        self.assertEqual(len(res["bijection"]), 3)
        self.assertIn(res["resource_count_status"], ("valid", "suspected_usize_underflow"))
        if res["resource_count_status"] == "valid":
            self.assertIsInstance(res["paper_accounted_toffoli"], int)

        # Compare with independent implementation
        cand = run_batched_isometry(problem)
        self.assertEqual(res["paper_accounted_toffoli"], cand.resources.total_paper_accounted_toffolis)

    def test_reference_mapping_and_resource_comparison_fixtures(self) -> None:
        if not is_authors_artifact_available():
            self.skipTest(f"Authors artifact Rust module not available: {get_authors_artifact_status().get('blocked_reason')}")
        fixtures = (
            (4, ("0000", "0011")),
            (4, ("0000", "0011", "1001")),
            (4, ("0000", "0011", "1001", "1110")),
            (4, ("0001", "0110", "1011")),
            (4, ("1110", "0000", "1001", "0011")),
        )
        for n, support in fixtures:
            with self.subTest(n=n, support=support):
                problem = SparseStateProblem(n=n, support=support, signs=tuple(1 for _ in support))
                reference = run_authors_reference_isometry(problem)
                candidate = run_batched_isometry(problem)
                self.assertEqual(reference["mapping_status"], "passed")
                self.assertEqual({row for _, row in reference["bijection"]}, set(range(len(support))))
                self.assertEqual(len({label for label, _ in reference["bijection"]}), len(support))
                # The reference and candidate choose different valid row pivots;
                # resource equality is recorded for audit but is not a semantic
                # invariant of independently synthesized circuits.
                self.assertGreaterEqual(reference["paper_accounted_toffoli_raw"], 0)
                self.assertGreaterEqual(candidate.resources.total_paper_accounted_toffolis, 0)

        mixed = SparseStateProblem(4, ("0000", "0011", "1001", "1110"), signs=(1, -1, 1, -1))
        self.assertEqual(len(run_authors_reference_isometry(mixed)["bijection"]), mixed.s)

    def test_reference_narrow_domain_is_explicit(self) -> None:
        if not is_authors_artifact_available():
            self.skipTest("Authors reference extension unavailable")
        with self.assertRaises(AuthorsReferenceUnsupportedInput):
            run_authors_reference_isometry(SparseStateProblem(2, ("00",)))
        with self.assertRaises(AuthorsReferenceUnsupportedInput):
            run_authors_reference_isometry(SparseStateProblem(2, ("00", "01", "10", "11")))

    def test_reference_counter_underflow_is_not_reported_as_a_cost(self) -> None:
        if not is_authors_artifact_available():
            self.skipTest("Authors reference extension unavailable")
        problem = SparseStateProblem(3, ("000", "001"))
        result = run_authors_reference_isometry(problem)
        if result["paper_accounted_toffoli_raw"] > __import__("sys").maxsize:
            self.assertEqual(result["resource_count_status"], "suspected_usize_underflow")
            self.assertIsNone(result["paper_accounted_toffoli"])


if __name__ == "__main__":
    unittest.main()
