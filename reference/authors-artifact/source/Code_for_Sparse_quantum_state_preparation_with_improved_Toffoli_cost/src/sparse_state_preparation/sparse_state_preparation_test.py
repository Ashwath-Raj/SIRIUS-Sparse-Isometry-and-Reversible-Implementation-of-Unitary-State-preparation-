# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import pytest
from qualtran import BloqBuilder, QFxp
from qualtran.bloqs.rotations import PhaseGradientState

from .sparse_state_preparation import (
    SparseStatePreparation,
    _sparse_state_preparation_complex,
    _sparse_state_preparation_real,
)
from .utils_test import bloq_autotester


@pytest.mark.parametrize(
    "bloq_ex",
    [
        _sparse_state_preparation_real,
        _sparse_state_preparation_complex,
    ],
)
def test_example(bloq_autotester, bloq_ex):
    bloq_autotester(bloq_ex)


_states = [
    np.array(
        [
            [True, True, False, False, True, True, False],
            [False, True, True, False, True, True, True],
            [True, False, False, True, False, True, False],
            [False, True, True, False, True, False, True],
            [False, False, True, True, True, True, False],
            [False, False, False, True, True, True, False],
            [False, True, False, False, False, True, False],
            [False, True, True, True, True, False, False],
            [True, False, False, False, True, True, False],
            [True, True, False, True, True, True, True],
            [False, True, True, True, True, True, False],
            [True, True, True, False, False, False, False],
            [True, True, True, False, True, True, False],
        ]
    ),
    np.array(
        [
            [
                True,
                True,
                False,
                True,
                False,
                True,
                True,
                False,
                True,
                False,
                True,
                False,
            ],
            [
                False,
                False,
                True,
                False,
                True,
                False,
                False,
                False,
                True,
                True,
                False,
                True,
            ],
            [
                False,
                True,
                True,
                True,
                False,
                False,
                True,
                False,
                False,
                False,
                True,
                False,
            ],
            [
                True,
                True,
                False,
                True,
                True,
                False,
                True,
                False,
                True,
                True,
                True,
                False,
            ],
            [
                True,
                True,
                False,
                False,
                True,
                False,
                True,
                False,
                False,
                False,
                True,
                True,
            ],
            [
                False,
                True,
                False,
                True,
                True,
                False,
                False,
                True,
                False,
                True,
                False,
                False,
            ],
            [
                True,
                False,
                True,
                False,
                False,
                True,
                True,
                False,
                False,
                True,
                False,
                False,
            ],
            [
                False,
                False,
                False,
                False,
                True,
                False,
                True,
                False,
                False,
                True,
                False,
                False,
            ],
            [
                True,
                True,
                False,
                False,
                True,
                True,
                True,
                True,
                False,
                False,
                False,
                True,
            ],
            [
                True,
                True,
                False,
                False,
                False,
                False,
                True,
                False,
                False,
                True,
                True,
                True,
            ],
            [
                True,
                True,
                True,
                False,
                False,
                True,
                False,
                False,
                False,
                False,
                False,
                True,
            ],
            [
                True,
                True,
                False,
                True,
                True,
                False,
                True,
                False,
                False,
                True,
                True,
                True,
            ],
            [
                True,
                True,
                False,
                True,
                False,
                False,
                False,
                True,
                True,
                False,
                True,
                True,
            ],
            [
                True,
                False,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
                False,
            ],
            [
                True,
                True,
                True,
                False,
                True,
                True,
                False,
                False,
                False,
                False,
                True,
                False,
            ],
            [
                True,
                False,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
                False,
                True,
                True,
            ],
        ]
    ),
]

_coeffs_restricted = [
    np.array(
        [
            0.02488553 + 0.00000000j,
            -0.06629236 + 0.02010957j,
            -0.03631694 + 0.11972092j,
            0.17653251 + 0.14487649j,
            -0.07449865 - 0.07449865j,
            0.25091815 - 0.37552555j,
            -0.10082037 + 0.33236022j,
            0.30032356 - 0.02957929j,
            -0.12526091 - 0.41292989j,
            -0.24785907 - 0.46371171j,
            0.07395457 + 0.06069295j,
            0.09754516 - 0.09754516j,
            0.08437416 + 0.04509893j,
        ]
    ),
    np.array(
        [
            0.01785846 - 0.03341083j,
            -0.07504034 + 0.37725327j,
            -0.02678813 - 0.02678813j,
            -0.25427587 + 0.16990170j,
            -0.08983268 - 0.13444411j,
            -0.07504034 + 0.37725327j,
            0.14416019 - 0.07705522j,
            0.03826248 + 0.38848547j,
            -0.10007110 + 0.06686537j,
            -0.22408317 - 0.02207027j,
            -0.00000000 + 0.28742058j,
            -0.07552674 - 0.09202960j,
            0.32356386 + 0.13402454j,
            0.14227969 - 0.02830119j,
            -0.05952675 - 0.01184061j,
            -0.23586409 - 0.19356866j,
        ]
    ),
]

_coeffs_unrestricted = [
    np.array(
        [
            0.02408507 + 0.0j,
            -0.06416 + 0.01946272j,
            -0.03514877 + 0.11586997j,
            0.16495142 + 0.13537213j,
            -0.0625 - 0.0625j,
            0.24764505 - 0.37062701j,
            -0.10521148 + 0.34683576j,
            0.2960165 - 0.02915508j,
            -0.1293942 - 0.4265555j,
            -0.24865176 - 0.46519472j,
            0.06853901 + 0.05624851j,
            0.08869675 - 0.08869675j,
            0.0781956 + 0.04179642j,
        ]
    ),
    np.array(
        [
            1.78584586e-02 - 0.03341083j,
            -7.50403410e-02 + 0.37725327j,
            -2.67881302e-02 - 0.02678813j,
            -2.54275866e-01 + 0.1699017j,
            -8.98326818e-02 - 0.13444411j,
            -7.50403410e-02 + 0.37725327j,
            1.44160185e-01 - 0.07705522j,
            3.82624795e-02 + 0.38848547j,
            -1.00071102e-01 + 0.06686537j,
            -2.24083174e-01 - 0.02207027j,
            -6.30508529e-19 + 0.29770586j,
            -7.55267432e-02 - 0.0920296j,
            3.35142510e-01 + 0.13882057j,
            1.28990386e-01 - 0.02565778j,
            -5.34295671e-02 - 0.0106278j,
            -2.22179115e-01 - 0.18233769j,
        ]
    ),
]

_data = [
    [_coeffs_restricted[0], _states[0], True],
    [_coeffs_restricted[1], _states[1], True],
    [_coeffs_unrestricted[0], _states[0], False],
    [_coeffs_unrestricted[1], _states[1], False],
]
# Need to choose different coefficients since the bijection differs, leading to different approximations.


@pytest.mark.parametrize("max_k", [None, 0, 2, 4])
@pytest.mark.parametrize("coeffs, states, uncompute_in_isometry", _data)
def test_sparse_state_preparation_fake_meas_complex(
    uncompute_in_isometry: bool,
    max_k: int | None,
    coeffs: np.ndarray,
    states: np.ndarray,
):
    phase_bitsize = 6
    prep = SparseStatePreparation(
        states,
        coeffs,
        QFxp(phase_bitsize, phase_bitsize),
        max_k,
        uncompute_in_isometry,
        tensor_simulation=True,
    )

    bb = BloqBuilder()
    phase_gradient = bb.add(PhaseGradientState(phase_bitsize))
    state, phase_gradient = bb.add(prep, phase_gradient=phase_gradient)
    bb.add(
        PhaseGradientState(bitsize=phase_bitsize).adjoint(), phase_grad=phase_gradient
    )
    bloq = bb.finalize(state=state)
    assert np.allclose(
        bloq.tensor_contract(), state_and_coeffs_to_tensor(states, coeffs)
    )


@pytest.mark.parametrize("max_k", [None, 0, 2, 4])
@pytest.mark.parametrize("coeffs, states, add_real_phase_in_isometry", _data)
def test_sparse_state_preparation_fake_meas_real(
    add_real_phase_in_isometry: bool,
    max_k: int | None,
    coeffs: np.ndarray,
    states: np.ndarray,
):
    phase_bitsize = 6
    coeffs = np.abs(coeffs)
    uncompute_in_isometry = add_real_phase_in_isometry
    prep = SparseStatePreparation(
        states,
        coeffs,
        QFxp(phase_bitsize, phase_bitsize),
        max_k,
        uncompute_in_isometry,
        add_real_phase_in_isometry,
        tensor_simulation=True,
    )

    bb = BloqBuilder()
    phase_gradient = bb.add(PhaseGradientState(phase_bitsize))
    state, phase_gradient = bb.add(prep, phase_gradient=phase_gradient)
    bb.add(
        PhaseGradientState(bitsize=phase_bitsize).adjoint(), phase_grad=phase_gradient
    )
    bloq = bb.finalize(state=state)
    assert np.allclose(
        bloq.tensor_contract(), state_and_coeffs_to_tensor(states, coeffs)
    )


def state_and_coeffs_to_tensor(state: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    num_bits = state.shape[1]
    statevector = np.zeros(2**num_bits, dtype=complex)

    for coeff, bits in zip(coeffs, state):
        index = int("".join(str(int(b)) for b in bits), 2)
        statevector[index] = coeff

    return statevector
