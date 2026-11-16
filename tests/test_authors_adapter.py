"""Unit and integration tests for authors reference artifact adapter."""
from __future__ import annotations

import unittest

from benchmarking.adapters.authors_adapter import (
    get_authors_artifact_status,
    is_authors_artifact_available,
    run_authors_reference_isometry,
)
from sparseprep import SparseStateProblem, run_batched_isometry


class AuthorsArtifactAdapterTests(unittest.TestCase):
    def test_authors_artifact_status_reporting(self) -> None:
        status = get_authors_artifact_status()
        self.assertIn("available", status)
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
        self.assertIsInstance(res["paper_accounted_toffoli"], int)

        # Compare with independent implementation
        cand = run_batched_isometry(problem)
        self.assertEqual(res["paper_accounted_toffoli"], cand.resources.total_paper_accounted_toffolis)


if __name__ == "__main__":
    unittest.main()
