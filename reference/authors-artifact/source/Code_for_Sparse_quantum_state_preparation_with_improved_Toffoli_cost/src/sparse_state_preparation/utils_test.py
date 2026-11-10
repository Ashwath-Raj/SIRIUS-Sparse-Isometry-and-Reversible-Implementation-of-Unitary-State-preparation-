# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import pytest

from .utils import random_tableau

from qualtran.conftest import (
    assert_bloq_example_decompose_for_pytest,
    assert_bloq_example_make_for_pytest,
    assert_bloq_example_qtyping_for_pytest,
)

_TESTFUNCS = [
    ("make", assert_bloq_example_make_for_pytest),
    ("decompose", assert_bloq_example_decompose_for_pytest),
    ("qtyping", assert_bloq_example_qtyping_for_pytest),
]


@pytest.fixture(params=_TESTFUNCS, ids=[name for name, _ in _TESTFUNCS])
def bloq_autotester(request):
    name, func = request.param
    func.check_name = name
    return func


@pytest.mark.parametrize("shape", [(100, 20), (10**3, 100), (10**5, 133), (10**4, 66)])
def test_random_tableau(shape):
    tableau = np.unique(random_tableau(*shape), axis=0)
    assert tableau.shape == shape
