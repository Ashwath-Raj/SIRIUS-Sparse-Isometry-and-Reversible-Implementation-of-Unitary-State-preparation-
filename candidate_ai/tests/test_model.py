import math
import pytest
from sparseprep.model import (
    ProblemValidationError, SparseStateProblem, UnsupportedConstructionError,
    bitstring_to_int, ceil_log2_positive, int_to_bitstring,
    largest_power_of_two_at_most,
)


def test_big_endian_conversion():
    assert bitstring_to_int("100") == 4
    assert int_to_bitstring(4, 3) == "100"
    assert [bitstring_to_int(int_to_bitstring(i, 3)) for i in range(8)] == list(range(8))


@pytest.mark.parametrize("s, expected", [(1, 0), (2, 1), (3, 2), (4, 2), (5, 3), (8, 3), (9, 4)])
def test_ceil_log2_exact(s, expected):
    assert ceil_log2_positive(s) == expected


def test_largest_power_of_two():
    assert [largest_power_of_two_at_most(x) for x in (1, 2, 3, 4, 7, 8, 9)] == [1, 2, 2, 4, 4, 8, 8]


def test_problem_derives_integer_safe_parameters():
    p = SparseStateProblem(6, ("000001", "100011", "111111"))
    assert (p.s, p.ell, p.padded_s, p.residual_width, p.batch_width) == (3, 2, 4, 4, 4)


def test_single_state_is_explicit_special_case():
    p = SparseStateProblem(3, ("101",))
    assert p.ell == 0
    with pytest.raises(UnsupportedConstructionError, match="s=1"):
        _ = p.batch_width


@pytest.mark.parametrize("support", [(), ("00", "00"), ("0", "11"), ("0x",), ("000", "001", "010", "011", "100", "101", "110", "111", "000")])
def test_invalid_support_rejected(support):
    n = 2 if support and len(support[0]) != 3 else (3 if support else 2)
    with pytest.raises((ProblemValidationError, TypeError, ValueError)):
        SparseStateProblem(n, support)


def test_coefficients_must_be_normalized():
    with pytest.raises(ProblemValidationError, match="normalized"):
        SparseStateProblem(2, ("00", "11"), coefficients=(1, 1))
    p = SparseStateProblem(2, ("00", "11"), coefficients=(1 / math.sqrt(2), 1j / math.sqrt(2)))
    assert p.coefficients is not None


def test_signs_and_metadata_are_validated():
    p = SparseStateProblem(2, ("00", "11"), signs=(1, -1), metadata=(("case", "edge"),))
    assert p.signs == (1, -1)
    with pytest.raises(ProblemValidationError):
        SparseStateProblem(2, ("00", "11"), signs=(1, 0))
