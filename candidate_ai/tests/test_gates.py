import itertools
import pytest
from sparseprep.gates import (
    CMX, CX, MCX, NegativeControlToffoli, PUIKind, PUIMacro,
    SWAP, Toffoli, X, invert_sequence, GateValidationError, UnsupportedGateError,
)
from sparseprep.simulator import apply_gate, simulate_basis_state
from sparseprep.resources import count_emitted_resources


@pytest.mark.parametrize("gate", [X(1), CX(0, 2), SWAP(0, 2), Toffoli(0, 1, 2),
    NegativeControlToffoli((0, 1), 2, (0, 1)), CMX(0, (1, 2)), MCX((0, 1), 2)])
def test_each_primitive_is_self_inverse_for_all_three_bit_states(gate):
    for state in map("".join, itertools.product("01", repeat=3)):
        assert apply_gate(apply_gate(state, gate), gate) == state


def test_cx_truth_table():
    assert [apply_gate(x, CX(0, 1)) for x in ("00", "01", "10", "11")] == ["00", "01", "11", "10"]


def test_negative_control_toffoli_truth_table():
    gate = NegativeControlToffoli((0, 1), 2, (0, 1))
    assert apply_gate("010", gate) == "011"
    assert apply_gate("110", gate) == "110"
    assert apply_gate("000", gate) == "000"


def test_cmx_flips_all_targets_only_when_control_one():
    assert apply_gate("1010", CMX(0, (1, 3))) == "1111"
    assert apply_gate("0010", CMX(0, (1, 3))) == "0010"


def test_gate_sequence_inverse_round_trip():
    gates = (X(0), CX(0, 2), Toffoli(0, 1, 3), SWAP(1, 2), MCX((0, 1, 2), 3))
    for state in map("".join, itertools.product("01", repeat=4)):
        assert simulate_basis_state(simulate_basis_state(state, gates), invert_sequence(gates)) == state


def test_pui_macro_is_symbolic_and_has_structural_inverse():
    gate = PUIMacro(PUIKind.RESTRICTED, (2, 6), L=4, g=1, address_wires=(0, 1), unary_wires=(2, 3, 4, 5))
    assert gate.inverse().inverse() == gate
    with pytest.raises(UnsupportedGateError, match="Phase 5"):
        apply_gate("000000", gate)


def test_resource_counter_does_not_miscount_cx_or_cmx_as_toffoli():
    counts = count_emitted_resources((X(0), CX(0, 1), SWAP(1, 2), Toffoli(0, 1, 2),
        NegativeControlToffoli((0, 1), 2), CMX(0, (1, 2)), MCX((0, 1, 2), 3),
        PUIMacro(PUIKind.UNRESTRICTED, (0, 4), 2, 0, (0, 1), (2, 3))))
    assert counts.x == 1
    assert counts.cx == 1
    assert counts.swap == 1
    assert counts.toffoli == 1
    assert counts.negative_control_toffoli == 1
    assert counts.cmx_macros == 1
    assert counts.mcx_macros == 1
    assert counts.unrestricted_pui_macros == 1
    assert counts.decomposed_toffoli is None
