from itertools import product

import pytest

from sparseprep.pui import (
    PUIValidationError,
    build_pui_plan,
    compile_mcx_coherent,
    mcx_ladder_cost,
)
from sparseprep.simulator import simulate_basis_state


def test_unrestricted_pui_figure7_left_interval_tracks_upper_half_extras():
    plan = build_pui_plan(
        address_width=3,
        interval=(0, 3),
        target_by_address={i: (3 + i,) for i in range(4)},
        kind="unrestricted",
    )
    assert plan.extra_map == {4: 0, 5: 1, 6: 2, 7: 3}
    assert plan.address_map == {0: 0, 1: 1, 2: 2, 3: 3, 4: 0, 5: 1, 6: 2, 7: 3}
    assert any(node.branch == "left_free" for node in plan.tree)


def test_restricted_pui_does_not_create_extra_addresses():
    plan = build_pui_plan(
        address_width=3,
        interval=(0, 3),
        target_by_address={i: (3 + i,) for i in range(4)},
        kind="restricted",
    )
    assert plan.extra_map == {}
    assert set(plan.address_map) == {0, 1, 2, 3}


def test_unrestricted_pui_right_interval_maps_address_seven_to_six():
    plan = build_pui_plan(
        address_width=3,
        interval=(4, 6),
        target_by_address={4: (3,), 5: (4,), 6: (5,)},
        kind="unrestricted",
    )
    assert plan.extra_map == {7: 6}
    assert plan.address_map[7] == 6


def test_restricted_right_interval_leaves_address_seven_untouched():
    plan = build_pui_plan(
        address_width=3,
        interval=(4, 6),
        target_by_address={4: (3,), 5: (4,), 6: (5,)},
        kind="restricted",
    )
    assert plan.extra_map == {}
    assert 7 not in plan.address_map


def test_pui_exact_basis_action_for_all_addresses_and_target_values():
    plan = build_pui_plan(
        address_width=3,
        interval=(0, 3),
        target_by_address={0: (3,), 1: (4,), 2: (5,), 3: (3, 5)},
        kind="unrestricted",
    )
    for address in range(8):
        unitary = plan.address_map.get(address)
        for target in range(8):
            state = format(address, "03b") + format(target, "03b")
            actual = simulate_basis_state(state, plan.gates)
            expected_target = target
            if unitary is not None:
                for wire in dict(plan.target_map)[unitary]:
                    target_bit = wire - 3
                    expected_target ^= 1 << (2 - target_bit)
            expected = format(address, "03b") + format(expected_target, "03b")
            assert actual == expected


def test_pui_address_register_is_never_changed():
    plan = build_pui_plan(
        address_width=3,
        interval=(2, 5),
        target_by_address={i: (3,) for i in range(2, 6)},
        kind="unrestricted",
    )
    for state in map("".join, product("01", repeat=5)):
        assert plan.apply(state)[:3] == state[:3]


def test_pui_inverse_round_trip_on_full_basis_space():
    plan = build_pui_plan(
        address_width=3,
        interval=(4, 6),
        target_by_address={4: (3,), 5: (4,), 6: (5,)},
        kind="unrestricted",
    )
    for state in map("".join, product("01", repeat=6)):
        forward = simulate_basis_state(state, plan.gates)
        backward = simulate_basis_state(forward, plan.inverse_gates())
        assert backward == state


def test_paper_maximum_pui_ancilla_count_is_w_minus_one():
    for width in range(1, 8):
        plan = build_pui_plan(
            address_width=width,
            interval=(0, 0),
            target_by_address={0: (width,)},
            kind="restricted",
        )
        assert plan.paper_max_ancillas == width - 1
        assert plan.semantic_auxiliary_wires == 0


@pytest.mark.parametrize(
    "controls,expected_paper,expected_ancillas,expected_coherent",
    [(1, 0, 0, 0), (2, 1, 0, 1), (3, 2, 1, 3), (4, 3, 2, 5), (5, 4, 3, 7)],
)
def test_mcx_ladder_cost_models(controls, expected_paper, expected_ancillas, expected_coherent):
    cost = mcx_ladder_cost(controls)
    assert cost.paper_accounted_toffolis == expected_paper
    assert cost.clean_ancillas == expected_ancillas
    assert cost.coherent_toffolis == expected_coherent


def test_coherent_mcx_ladder_computes_correct_function_and_cleans_ancillas():
    controls = (0, 1, 2, 3)
    target = 4
    ancillas = (5, 6)
    gates = compile_mcx_coherent(controls, target, ancillas)
    for ctrl in product("01", repeat=4):
        for tgt in "01":
            state = "".join(ctrl) + tgt + "00"
            output = simulate_basis_state(state, gates)
            expected_target = str(int(tgt) ^ int(all(x == "1" for x in ctrl)))
            assert output == "".join(ctrl) + expected_target + "00"


def test_coherent_mcx_ladder_supports_negative_controls():
    gates = compile_mcx_coherent((0, 1), 2, (), control_values=(0, 1))
    for bits in product("01", repeat=3):
        state = "".join(bits)
        output = simulate_basis_state(state, gates)
        expected = bits[2]
        if bits[0] == "0" and bits[1] == "1":
            expected = "1" if expected == "0" else "0"
        assert output == bits[0] + bits[1] + expected


def test_coherent_mcx_is_self_inverse_as_compiled_sequence():
    gates = compile_mcx_coherent((0, 1, 2), 3, (4,))
    inverse = tuple(g.inverse() for g in reversed(gates))
    for state in map("".join, product("01", repeat=5)):
        assert simulate_basis_state(simulate_basis_state(state, gates), inverse) == state


def test_coherent_mcx_rejects_insufficient_or_overlapping_ancillas():
    with pytest.raises(PUIValidationError):
        compile_mcx_coherent((0, 1, 2, 3), 4, (5,))
    with pytest.raises(PUIValidationError):
        compile_mcx_coherent((0, 1, 2), 3, (2,))


def test_invalid_pui_intervals_and_targets_are_rejected():
    with pytest.raises(PUIValidationError):
        build_pui_plan(address_width=2, interval=(0, 4), target_by_address={})
    with pytest.raises(PUIValidationError):
        build_pui_plan(address_width=2, interval=(2, 1), target_by_address={})
    with pytest.raises(PUIValidationError):
        build_pui_plan(address_width=2, interval=(0, 1), target_by_address={0: (1,)})


def test_pui_uses_big_endian_address_wire_order():
    plan = build_pui_plan(
        address_width=3,
        interval=(4, 4),
        target_by_address={4: (3,)},
        address_wires=(2, 0, 1),
        kind="restricted",
    )
    # Address 4 is 100; the control values follow address_wires in that order.
    gate = plan.gates[0]
    assert gate.controls == (2, 0, 1)
    assert gate.control_values == (1, 0, 0)


def test_unrestricted_extra_address_is_always_greater_than_interval_end():
    for width in range(1, 6):
        limit = 1 << width
        for lo in range(limit):
            for hi in range(lo, min(limit, lo + 3)):
                plan = build_pui_plan(
                    address_width=width,
                    interval=(lo, hi),
                    target_by_address={i: (width,) for i in range(lo, hi + 1)},
                    kind="unrestricted",
                )
                assert all(addr > hi for addr in plan.extra_map)
                assert all(lo <= source <= hi for source in plan.extra_map.values())


def test_repeated_unrestricted_pui_bound_matches_equation_7():
    from sparseprep.pui import repeated_pui_cost_bound

    bound = repeated_pui_cost_bound(
        sparse_size=7, address_width=3, interval_size=4, kind="unrestricted"
    )
    assert bound.interval_count == 2
    assert bound.toffoli_bound == 5
    assert bound.max_ancillas == 2


def test_repeated_restricted_pui_bound_matches_equation_8():
    from sparseprep.pui import repeated_pui_cost_bound

    bound = repeated_pui_cost_bound(
        sparse_size=7, address_width=3, interval_size=4, kind="restricted"
    )
    assert bound.interval_count == 2
    assert bound.toffoli_bound == 6
    assert bound.max_ancillas == 2


def test_repeated_pui_bounds_reject_out_of_domain_parameters():
    from sparseprep.pui import repeated_pui_cost_bound

    with pytest.raises(PUIValidationError):
        repeated_pui_cost_bound(sparse_size=4, address_width=3, interval_size=4, kind="unrestricted")
    with pytest.raises(PUIValidationError):
        repeated_pui_cost_bound(sparse_size=7, address_width=3, interval_size=3, kind="restricted")
