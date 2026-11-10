# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from qualtran import QUInt

import numpy as np

from .utils_test import bloq_autotester
from .isometry import ToggleWithPhase
from .partial_unary_iteration import (
    PartialUnaryIteration,
    _partial_unary_iteration_restricted,
    _partial_unary_iteration_unrestricted,
)


@pytest.mark.parametrize(
    "bloq_ex",
    [
        _partial_unary_iteration_unrestricted,
        _partial_unary_iteration_restricted,
    ],
)
def test_examples(bloq_autotester, bloq_ex):
    bloq_autotester(bloq_ex)


@pytest.mark.parametrize("restricted", [True, False])
@pytest.mark.parametrize("interval", [(5, 6), (0, 16), (7, 15), (0, 7), (7, 16)])
def test_pui(restricted: bool, interval: tuple[int, int]):
    pui = PartialUnaryIteration(
        interval,
        QUInt(4),
        tuple(ToggleWithPhase(16, i, False, None) for i in range(*interval)),
        restricted=restricted,
    )

    assert len(pui.mapping) == interval[1] - interval[0]
    if restricted:
        for i, l in enumerate(pui.mapping):
            assert l == [interval[0] + i]

    for i in range(2**4):
        address, operation = pui.call_classically(address=i, operation=(0,) * 16)

        assert address == i
        if interval[0] <= i < interval[1]:
            assert np.allclose(operation, np.eye(16, dtype=int)[i])
        elif i < interval[0]:
            assert np.allclose(operation, np.zeros(16))
        else:
            if restricted:
                assert np.allclose(operation, np.zeros(16))
            else:
                for j, l in enumerate(pui.mapping):
                    if i in l:
                        assert np.allclose(
                            operation, np.eye(16, dtype=int)[interval[0] + j]
                        )
