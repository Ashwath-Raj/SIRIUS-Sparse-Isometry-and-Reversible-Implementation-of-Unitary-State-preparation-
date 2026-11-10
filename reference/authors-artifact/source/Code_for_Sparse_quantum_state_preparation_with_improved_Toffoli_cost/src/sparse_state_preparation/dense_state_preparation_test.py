# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import pytest
from qualtran import BloqBuilder, QFxp, QUInt
from qualtran.bloqs.rotations import PhaseGradientState

from .uncompute import SignFixUp
from .dense_state_preparation import (
    DenseStatePreparationViaQROAM,
    _dense_prep,
    _dense_prep_no_phase,
)
from .utils_test import bloq_autotester


@pytest.mark.parametrize(
    "bloq_ex",
    [
        _dense_prep_no_phase,
        _dense_prep,
    ],
)
def test_example(bloq_autotester, bloq_ex):
    bloq_autotester(bloq_ex)


_coeffs = [
    np.array(
        [
            0.51327997 + 0.76817776j,
            -0.14644661 + 0.35355339j,
        ]
    ),
    np.array(
        [
            -0.48732681 + 0.32562136j,
            -0.13487679 + 0.20185737j,
            -0.34870390 + 0.10577817j,
            0.56684140 + 0.37875132j,
        ]
    ),
    np.array(
        [
            0.02696882 + 0.00000000j,
            -0.06230495 + 0.01890000j,
            -0.03179024 + 0.10479837j,
            0.15837925 + 0.12997849j,
            -0.05717151 - 0.05717151j,
            0.22582490 - 0.33797085j,
            -0.09299689 + 0.30656965j,
            0.26165028 - 0.02577030j,
            -0.11608828 - 0.38269177j,
            -0.22970880 - 0.42975493j,
            0.05385076 + 0.04419417j,
            0.07372230 - 0.07372230j,
            0.08052538 + 0.04304171j,
            0.04300455 - 0.21619846j,
            0.30135985 - 0.09141651j,
            0.06441647 + 0.15551513j,
        ]
    ),
]


@pytest.mark.parametrize("max_k", [None, 0, 2, 4])
@pytest.mark.parametrize(
    "coeffs",
    _coeffs,
)
def test_state_preparation_fake_meas(
    max_k: int | None,
    coeffs: np.ndarray,
):
    phase_bitsize = 6
    prep = DenseStatePreparationViaQROAM(
        coeffs,
        QUInt(int(np.log2(len(coeffs)))),
        QFxp(phase_bitsize, phase_bitsize),
        tensor_simulation_random=False,
        max_k=max_k,
    )

    bb = BloqBuilder()
    phase_gradient = bb.add(PhaseGradientState(phase_bitsize))
    state, phase_gradient = bb.add(prep, phase_gradient=phase_gradient)
    bb.add(
        PhaseGradientState(bitsize=phase_bitsize).adjoint(), phase_grad=phase_gradient
    )
    bloq = bb.finalize(state=state)
    assert np.allclose(bloq.tensor_contract(), coeffs)


@pytest.mark.parametrize("max_k", [None, 0, 2, 4])
@pytest.mark.parametrize(
    "coeffs",
    _coeffs,
)
def test_state_preparation_fake_meas_with_uncomputing(
    max_k: int | None,
    coeffs: np.ndarray,
):
    phase_bitsize = 6
    prep = DenseStatePreparationViaQROAM(
        coeffs,
        QUInt(int(np.log2(len(coeffs)))),
        QFxp(phase_bitsize, phase_bitsize),
        tensor_simulation_random=True,
        uncompute=False,
        max_k=max_k,
    )

    bb = BloqBuilder()
    phase_gradient = bb.add(PhaseGradientState(phase_bitsize))
    state, phase_gradient = bb.add(prep, phase_gradient=phase_gradient)
    bb.add(
        PhaseGradientState(bitsize=phase_bitsize).adjoint(), phase_grad=phase_gradient
    )
    bloq = bb.finalize(state=state)
    dense_state = bloq.tensor_contract()

    ratio = dense_state / coeffs
    assert np.all(np.logical_or(np.isclose(ratio, -1), np.isclose(ratio, 1)))

    sign_fix = SignFixUp(
        tuple(np.isclose(ratio, -1)),
        QUInt(int(np.log2(len(coeffs)))),
        max_k=max_k,
        tensor_simulation=True,
    )

    assert np.allclose(coeffs, sign_fix.tensor_contract() @ dense_state)


@pytest.mark.parametrize("max_k", [None, 0, 2, 4])
@pytest.mark.parametrize(
    "coeffs",
    _coeffs,
)
def test_state_preparation_no_phases(
    max_k: int | None,
    coeffs: np.ndarray,
):
    phase_bitsize = 6
    prep = DenseStatePreparationViaQROAM(
        coeffs,
        QUInt(int(np.log2(len(coeffs)))),
        QFxp(phase_bitsize, phase_bitsize),
        prepare_only_amplitudes=True,
        uncompute=False,
        tensor_simulation_random=False,
        max_k=max_k,
    )

    bb = BloqBuilder()
    phase_gradient = bb.add(PhaseGradientState(phase_bitsize))
    state, phase_gradient = bb.add(prep, phase_gradient=phase_gradient)
    bb.add(
        PhaseGradientState(bitsize=phase_bitsize).adjoint(), phase_grad=phase_gradient
    )
    bloq = bb.finalize(state=state)
    assert np.allclose(bloq.tensor_contract(), np.abs(coeffs))
