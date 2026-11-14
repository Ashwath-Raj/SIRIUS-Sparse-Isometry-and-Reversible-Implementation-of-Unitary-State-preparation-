from __future__ import annotations
import random
import pytest
from sparseprep.model import SparseStateProblem
from sparseprep.algorithm3 import Algorithm3Error, run_algorithm3


def test_algorithm3_encodes_signs_and_returns_zero_residuals():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    result = run_algorithm3(problem, (1, -1, 1, -1))
    result.verify()
    assert result.phases == (1, -1, 1, -1)
    assert result.final_markers == (0, 0, 0, 0)
    assert len(set(result.compact_labels)) == problem.s
    assert result.restricted_pui_count >= 1


def test_marker_escape_and_counter_effect_path_is_exercised():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    result = run_algorithm3(problem, (1, -1, -1, 1))
    assert result.marker_cx_count >= 1
    assert result.counter_effect_cx_count >= 1
    assert any(e.kind == "marker_escape_batch" for e in result.events)
    assert any(e.kind == "counter_effect_cx" for e in result.events)


def test_simple_no_escape_instance():
    problem = SparseStateProblem(4, ("0000", "0001", "0010", "0011"))
    result = run_algorithm3(problem, (1, -1, 1, -1))
    result.verify()
    assert result.marker_cx_count == 0
    assert result.phases == (1, -1, 1, -1)


def test_forward_and_inverse_circuit_round_trip_every_support_row():
    problem = SparseStateProblem(5, ("00000", "00101", "01010", "01111", "10011", "11100"))
    result = run_algorithm3(problem, (1, -1, 1, -1, 1, -1))
    result.verify()
    assert len(result.forward_gates) == len(result.inverse_gates)


def test_default_signs_are_positive():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    result = run_algorithm3(problem)
    assert result.phases == (1, 1, 1, 1)


def test_invalid_sign_vectors_are_rejected():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    for signs in ((1, -1), (1, 0, 1, -1), (1, True, 1, -1), (1, 1.0, 1, -1)):
        with pytest.raises(Algorithm3Error):
            run_algorithm3(problem, signs)


def test_single_row_boundary():
    problem = SparseStateProblem(4, ("1010",))
    result = run_algorithm3(problem, (-1,))
    result.verify()
    assert result.final_tableau == ("0000",)
    assert result.phases == (-1,)


def test_zero_residual_width_boundary():
    problem = SparseStateProblem(2, ("00", "01", "10", "11"))
    result = run_algorithm3(problem, (1, -1, 1, -1))
    result.verify()
    assert result.final_tableau == problem.support
    assert result.final_markers == (0, 0, 0, 0)
    assert result.phases == (1, -1, 1, -1)


def test_resource_counts_include_batch_and_pui_toffolis():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    result = run_algorithm3(problem, (1, -1, 1, -1))
    assert result.paper_accounted_toffolis >= result.batch_toffoli_count
    assert result.coherent_toffolis >= result.paper_accounted_toffolis


def test_seeded_randomized_algorithm3_instances():
    rng = random.Random(20261115)
    cases = 0
    for n in range(3, 8):
        for s in range(2, min(12, 1 << n) + 1):
            ell = (s - 1).bit_length()
            if ell >= n:
                continue
            for _ in range(8):
                support = tuple(format(x, f"0{n}b") for x in rng.sample(range(1 << n), s))
                signs = tuple(rng.choice((-1, 1)) for _ in range(s))
                result = run_algorithm3(SparseStateProblem(n, support), signs)
                result.verify()
                assert result.phases == signs
                cases += 1
    assert cases >= 300
