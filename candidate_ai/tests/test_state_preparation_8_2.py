from __future__ import annotations

import math
import random

import pytest

from sparseprep.model import SparseStateProblem
from sparseprep.phase_synthesis import apply_operations
from sparseprep.state_preparation import (
    StatePreparationError,
    compile_dense_compact_preparation,
    compile_sparse_state_preparation,
    prepare_sparse_state,
)


def _normalized_complex(count: int, seed: int) -> tuple[complex, ...]:
    rng = random.Random(seed)
    raw = [complex(rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)) for _ in range(count)]
    norm = math.sqrt(sum(abs(value) ** 2 for value in raw))
    return tuple(value / norm for value in raw)


def test_end_to_end_prepares_exact_arbitrary_complex_sparse_state() -> None:
    coeffs = (1 / math.sqrt(3), 1j / math.sqrt(3), -1 / math.sqrt(3))
    problem = SparseStateProblem(
        4, ("0001", "0110", "1011"), coefficients=coeffs, signs=(1, -1, 1)
    )
    circuit, metrics = prepare_sparse_state(problem)
    assert metrics.fidelity == pytest.approx(1.0, abs=2e-10)
    assert metrics.maximum_amplitude_error < 2e-10
    assert metrics.workspace_leakage_probability < 1e-12
    assert metrics.outside_support_probability < 1e-12
    assert metrics.inverse_round_trip_error < 2e-10
    for bitstring, coefficient, sign in zip(problem.support, coeffs, problem.signs):
        assert circuit.target_state[int(bitstring, 2)] == coefficient * sign


def test_compact_label_permutation_is_respected_not_assumed_row_order() -> None:
    problem = SparseStateProblem(
        3, ("000", "011"), coefficients=(1 / math.sqrt(2), 1j / math.sqrt(2))
    )
    circuit, metrics = prepare_sparse_state(problem)
    assert circuit.compact_labels == (1, 0)
    assert metrics.fidelity == pytest.approx(1.0, abs=1e-10)
    assert metrics.maximum_amplitude_error < 1e-10


def test_dense_loader_prepares_arbitrary_sparse_compact_labels_and_cleans_work() -> None:
    labels = (1, 5, 6)
    coeffs = _normalized_complex(3, 813)
    operations = compile_dense_compact_preparation(
        coeffs, labels, data_qubits=3, work_ancillas=(3,)
    )
    state = [0j] * 16
    state[0] = 1 + 0j
    actual = apply_operations(state, 4, operations)
    expected = [0j] * 16
    for label, coefficient in zip(labels, coeffs):
        expected[label << 1] = coefficient
    assert max(abs(a - b) for a, b in zip(actual, expected)) < 1e-10
    assert sum(abs(value) ** 2 for index, value in enumerate(actual) if index & 1) < 1e-12


def test_multi_controlled_rotation_and_phase_ladders_are_exercised() -> None:
    n, s = 8, 9  # ell=4: deepest loader controls require clean AND ladders.
    rng = random.Random(20261115)
    support = tuple(format(v, f"0{n}b") for v in rng.sample(range(1 << n), s))
    signs = tuple(rng.choice((-1, 1)) for _ in range(s))
    problem = SparseStateProblem(
        n, support, coefficients=_normalized_complex(s, 29), signs=signs
    )
    circuit, metrics = prepare_sparse_state(problem, max_statevector_qubits=20)
    assert circuit.ell == 4
    assert circuit.phase_ancilla_wires
    assert circuit.resources.dense_loader.toffoli > 0
    assert metrics.fidelity == pytest.approx(1.0, abs=2e-9)
    assert metrics.workspace_leakage_probability < 2e-10


def test_zero_coefficients_are_supported_without_losing_row_mapping() -> None:
    problem = SparseStateProblem(
        4, ("0000", "0111", "1010"), coefficients=(1 / math.sqrt(2), 0j, 1j / math.sqrt(2)),
        signs=(-1, 1, -1),
    )
    circuit, metrics = prepare_sparse_state(problem)
    assert metrics.fidelity == pytest.approx(1.0, abs=1e-10)
    assert circuit.target_state[int("0111", 2)] == 0j
    assert metrics.outside_support_probability < 1e-12


def test_single_support_state_and_global_coefficient_phase() -> None:
    problem = SparseStateProblem(5, ("10101",), coefficients=(1j,), signs=(-1,))
    circuit, metrics = prepare_sparse_state(problem)
    assert circuit.ell == 0
    assert circuit.target_state[int("10101", 2)] == -1j
    assert metrics.maximum_amplitude_error < 1e-12
    assert metrics.workspace_leakage_probability == pytest.approx(0.0, abs=1e-12)


def test_full_dense_support_boundary_is_prepared_without_residual_work() -> None:
    coeffs = _normalized_complex(4, 415)
    support = tuple(format(i, "02b") for i in range(4))
    problem = SparseStateProblem(2, support, coefficients=coeffs)
    circuit, metrics = prepare_sparse_state(problem)
    assert circuit.ell == circuit.n
    assert circuit.algorithm3_clean_ancillas == 0
    assert metrics.fidelity == pytest.approx(1.0, abs=2e-10)


def test_sign_metadata_and_complex_coefficient_phase_are_independent() -> None:
    coeffs = (1j / math.sqrt(2), (1 + 1j) / 2)
    problem = SparseStateProblem(3, ("001", "110"), coefficients=coeffs, signs=(-1, 1))
    circuit, metrics = prepare_sparse_state(problem)
    assert circuit.target_state[int("001", 2)] == -coeffs[0]
    assert circuit.target_state[int("110", 2)] == coeffs[1]
    assert metrics.maximum_amplitude_error < 1e-10


def test_full_circuit_and_inverse_round_trip_cover_every_workspace_wire() -> None:
    problem = SparseStateProblem(
        6,
        ("000001", "001110", "101011", "111100", "011010"),
        coefficients=_normalized_complex(5, 712), signs=(1, -1, -1, 1, -1),
    )
    circuit = compile_sparse_state_preparation(problem)
    metrics = circuit.verify()
    assert circuit.total_qubits == (
        problem.n + 1 + len(circuit.algorithm3_ancilla_wires) + len(circuit.phase_ancilla_wires)
    )
    assert metrics.inverse_round_trip_error < 2e-9
    assert metrics.workspace_leakage_probability < 2e-9


def test_resources_account_for_all_three_stages_and_cleanup() -> None:
    problem = SparseStateProblem(
        5, ("00001", "00111", "10100", "11110"),
        coefficients=(0.5 + 0j, 0.5j, -0.5, -0.5j), signs=(1, -1, 1, -1),
    )
    circuit, _ = prepare_sparse_state(problem)
    stages = (
        circuit.resources.dense_loader.operations,
        circuit.resources.sign_oracle.operations,
        circuit.resources.inverse_isometry.operations,
        circuit.resources.marker_cleanup.operations,
    )
    assert sum(stages) == circuit.resources.total_operations == len(circuit.operations)
    assert circuit.resources.total_toffolis == sum(
        stage.toffoli for stage in (
            circuit.resources.dense_loader, circuit.resources.sign_oracle,
            circuit.resources.inverse_isometry, circuit.resources.marker_cleanup,
        )
    )


def test_coefficients_are_required_for_actual_state_preparation() -> None:
    problem = SparseStateProblem(3, ("000", "111"))
    with pytest.raises(StatePreparationError, match="coefficients are required"):
        compile_sparse_state_preparation(problem)


def test_invalid_statevector_cap_is_rejected_but_compilation_remains_available() -> None:
    problem = SparseStateProblem(
        4, ("0001", "0110"), coefficients=(1 / math.sqrt(2), 1j / math.sqrt(2))
    )
    circuit = compile_sparse_state_preparation(problem)
    assert circuit.operations
    with pytest.raises(StatePreparationError, match="above configured cap"):
        prepare_sparse_state(problem, max_statevector_qubits=2)


def test_seeded_randomized_end_to_end_instances() -> None:
    rng = random.Random(20261115)
    checked = 0
    for case in range(50):
        n = rng.randint(2, 7)
        s = rng.randint(1, min(6, 1 << n))
        support = tuple(format(v, f"0{n}b") for v in rng.sample(range(1 << n), s))
        coeffs = _normalized_complex(s, 90_000 + case)
        signs = tuple(rng.choice((-1, 1)) for _ in range(s))
        problem = SparseStateProblem(n, support, coefficients=coeffs, signs=signs)
        circuit, metrics = prepare_sparse_state(problem, max_statevector_qubits=18)
        assert metrics.fidelity == pytest.approx(1.0, abs=2e-9)
        assert metrics.maximum_amplitude_error < 2e-9
        assert metrics.workspace_leakage_probability < 2e-9
        assert metrics.outside_support_probability < 2e-9
        assert metrics.inverse_round_trip_error < 2e-9
        checked += 1
    assert checked == 50
