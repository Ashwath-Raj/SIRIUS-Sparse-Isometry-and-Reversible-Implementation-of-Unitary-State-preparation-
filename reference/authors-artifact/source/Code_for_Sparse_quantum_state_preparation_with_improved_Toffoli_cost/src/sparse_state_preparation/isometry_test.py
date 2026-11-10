# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from qualtran import QUInt, bloq_example

from qualtran.resource_counting import QECGatesCost, get_cost_value
from qualtran.simulation.classical_sim import do_phased_classical_simulation

from ._isometry_algorithms import fast_toffoli_counter
from .isometry import (
    IsometryToSubspaceViaBatching,
    _isometry_to_subspace,
    _isometry_to_subspace_with_phase,
)
from .utils import random_signs, random_tableau
from .utils_test import bloq_autotester


@bloq_example()
def _isometry_to_subspace_big() -> IsometryToSubspaceViaBatching:
    return IsometryToSubspaceViaBatching(random_tableau(540, 30), sub_problem_size=1)


@bloq_example()
def _isometry_to_subspace_with_phase_big() -> IsometryToSubspaceViaBatching:
    return IsometryToSubspaceViaBatching(random_tableau(540, 30), random_signs(540), 2)


@pytest.mark.parametrize(
    "bloq_ex",
    [
        _isometry_to_subspace,
        _isometry_to_subspace_with_phase,
        _isometry_to_subspace_big,
        _isometry_to_subspace_with_phase_big,
    ],
)
def test_examples(bloq_autotester, bloq_ex):
    bloq_autotester(bloq_ex)


@pytest.mark.parametrize(
    "bloq_ex",
    [_isometry_to_subspace, _isometry_to_subspace_big],
)
def test_bloq_no_phases(bloq_ex):
    bloq = bloq_ex()
    initial_states = QUInt(bloq.state_bitsize).from_bits_array(bloq.states)
    for [subspace_content, row] in bloq.bijection:
        assert subspace_content == bloq.call_classically(full=initial_states[row])[0]


@pytest.mark.parametrize(
    "bloq_ex",
    [_isometry_to_subspace_with_phase, _isometry_to_subspace_with_phase_big],
)
def test_bloq_phases(bloq_ex):
    bloq = bloq_ex()
    initial_states = QUInt(bloq.state_bitsize).from_bits_array(bloq.states)
    phases = [(-1) ** p for p in bloq.signs]
    for [subspace_content, row] in bloq.bijection:
        subspace, sign = do_phased_classical_simulation(
            bloq, {"full": initial_states[row]}
        )
        assert subspace["subspace"] == subspace_content
        assert sign == phases[row]


@pytest.mark.parametrize(
    "bloq_ex",
    [
        _isometry_to_subspace,
        _isometry_to_subspace_big,
        _isometry_to_subspace_with_phase,
        _isometry_to_subspace_with_phase_big,
    ],
)
def test_fast_toffoli_counter(bloq_ex):
    bloq = bloq_ex()
    gate_costs = get_cost_value(bloq, QECGatesCost())
    toffoli_cost_bloq = gate_costs.and_bloq + gate_costs.toffoli
    assert toffoli_cost_bloq <= fast_toffoli_counter(bloq.circuit)
