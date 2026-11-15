from __future__ import annotations

import random
from types import SimpleNamespace

import pytest

from sparseprep.algorithm3 import run_algorithm3
from sparseprep.model import SparseStateProblem
from sparseprep.phase_synthesis import (
    PhaseSynthesisError,
    compile_real_sign_phase_oracle,
    direct_sign_phase,
)


def _close(a, b, tol=1e-10):
    return len(a) == len(b) and all(abs(x-y) <= tol for x, y in zip(a, b))


def test_compiles_phase7_signs_onto_compact_labels():
    problem = SparseStateProblem(4, ("0000", "0011", "1100", "1111"))
    result = run_algorithm3(problem, (1, -1, 1, -1))
    oracle = compile_real_sign_phase_oracle(result)
    assert oracle.negative_labels == tuple(
        label for label, sign in zip(result.compact_labels, result.signs) if sign == -1
    )
    oracle.verify()


def test_every_basis_label_gets_exact_requested_phase_and_no_leakage():
    result = SimpleNamespace(ell=3, compact_labels=(0, 2, 5, 7), signs=(1, -1, -1, 1))
    oracle = compile_real_sign_phase_oracle(result)
    for label in range(8):
        state = [0j] * 8
        state[label] = 1 + 0j
        out = oracle.apply(state)
        expected_sign = -1 if label in (2, 5) else 1
        assert abs(out[label] - expected_sign) < 1e-12
        assert sum(abs(x) ** 2 for i, x in enumerate(out) if i != label) < 1e-20


def test_arbitrary_complex_superposition_matches_independent_diagonal_oracle():
    rng = random.Random(8001)
    for ell in range(1, 7):
        dim = 1 << ell
        raw = [complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(dim)]
        norm = sum(abs(x) ** 2 for x in raw) ** 0.5
        state = tuple(x / norm for x in raw)
        labels = tuple(rng.sample(range(dim), min(dim, max(1, dim // 2))))
        signs = tuple(rng.choice((-1, 1)) for _ in labels)
        oracle = compile_real_sign_phase_oracle(
            SimpleNamespace(ell=ell, compact_labels=labels, signs=signs)
        )
        expected = direct_sign_phase(state, dict(zip(labels, signs)))
        assert _close(oracle.apply(state), expected)
        oracle.verify()


def test_more_than_three_phase_controls_use_clean_ancilla_ladder():
    result = SimpleNamespace(ell=6, compact_labels=(0, 13, 42), signs=(-1, 1, -1))
    oracle = compile_real_sign_phase_oracle(result)
    assert oracle.clean_ancillas == 3
    assert oracle.resources.toffoli > 0
    assert oracle.resources.total_operations == len(oracle.operations)
    oracle.verify()


def test_single_qubit_and_zero_qubit_boundaries():
    one = compile_real_sign_phase_oracle(
        SimpleNamespace(ell=1, compact_labels=(0, 1), signs=(-1, 1))
    )
    assert _close(one.apply((1+0j, 0j)), (-1+0j, 0j))
    one.verify()

    zero = compile_real_sign_phase_oracle(
        SimpleNamespace(ell=0, compact_labels=(0,), signs=(-1,))
    )
    assert zero.apply((1+0j,)) == (-1+0j,)
    assert zero.resources.global_phase == 1
    zero.verify()


def test_all_positive_signs_compile_to_identity():
    oracle = compile_real_sign_phase_oracle(
        SimpleNamespace(ell=3, compact_labels=(0, 3, 7), signs=(1, 1, 1))
    )
    assert oracle.operations == ()
    assert oracle.apply((1, 0, 0, 0, 0, 0, 0, 0)) == (1+0j, 0j, 0j, 0j, 0j, 0j, 0j, 0j)


@pytest.mark.parametrize("bad", [
    SimpleNamespace(ell=-1, compact_labels=(0,), signs=(1,)),
    SimpleNamespace(ell=2, compact_labels=(0, 0), signs=(1, -1)),
    SimpleNamespace(ell=2, compact_labels=(4,), signs=(-1,)),
    SimpleNamespace(ell=2, compact_labels=(0,), signs=(0,)),
    SimpleNamespace(ell=2, compact_labels=(0,), signs=(True,)),
])
def test_rejects_invalid_phase_oracle_metadata(bad):
    with pytest.raises((PhaseSynthesisError, TypeError)):
        compile_real_sign_phase_oracle(bad)


def test_resource_counts_are_gate_level_and_do_not_claim_paper_toffoli_cost():
    oracle = compile_real_sign_phase_oracle(
        SimpleNamespace(ell=5, compact_labels=(1, 4, 20), signs=(-1, -1, 1))
    )
    r = oracle.resources
    assert r.phase_flips == 2
    assert r.total_operations == r.h + r.x + r.z + r.cx + r.toffoli + r.global_phase
    assert r.clean_ancillas == oracle.clean_ancillas
