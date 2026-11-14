from __future__ import annotations

from itertools import product

import pytest

from sparseprep.pui import build_pui_plan
from sparseprep.pui_tree import compile_pui_tree
from sparseprep.simulator import simulate_basis_state
from sparseprep.gates import MCX, NegativeControlToffoli, Toffoli


def _make_input_state(plan, tree, address: int, target_pattern: int) -> str:
    target_wires = sorted({wire for _, targets in plan.target_map for wire in targets})
    last_wire = max([*plan.address_wires, *target_wires, *tree.ancilla_wires], default=-1)
    bits = ["0"] * (last_wire + 1)
    addr_bits = format(address, f"0{plan.address_width}b")
    for wire, bit in zip(plan.address_wires, addr_bits):
        bits[wire] = bit
    for index, wire in enumerate(target_wires):
        shift = len(target_wires) - 1 - index
        bits[wire] = str((target_pattern >> shift) & 1)
    # Ancillas are explicitly clean at input.
    for wire in tree.ancilla_wires:
        bits[wire] = "0"
    return "".join(bits)


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_optimized_tree_matches_mcx_oracle_for_every_interval(width):
    address_space = 1 << width
    for lo in range(address_space):
        for hi in range(lo, address_space):
            target_by_address = {
                address: (width + (address % 2),)
                for address in range(lo, hi + 1)
            }
            for kind in ("restricted", "unrestricted"):
                plan = build_pui_plan(
                    address_width=width,
                    interval=(lo, hi),
                    target_by_address=target_by_address,
                    kind=kind,
                )
                tree = compile_pui_tree(plan)
                target_count = len({w for _, ts in plan.target_map for w in ts})
                for address in range(address_space):
                    for target_pattern in range(1 << target_count):
                        initial = _make_input_state(plan, tree, address, target_pattern)
                        expected = simulate_basis_state(initial, plan.gates)
                        actual = tree.apply(initial)
                        assert actual == expected, (
                            width, lo, hi, kind, address, target_pattern,
                            plan.extra_address_map, tree.free_bit_positions,
                        )


def test_optimized_tree_reproduces_both_figure7_extra_address_maps():
    left = build_pui_plan(
        address_width=3,
        interval=(0, 3),
        target_by_address={i: (3 + i,) for i in range(4)},
        kind="unrestricted",
    )
    left_tree = compile_pui_tree(left)
    assert dict(left.extra_address_map) == {4: 0, 5: 1, 6: 2, 7: 3}
    assert dict(left_tree.extra_address_map) == dict(left.extra_address_map)

    right = build_pui_plan(
        address_width=3,
        interval=(4, 6),
        target_by_address={i: (3 + i - 4,) for i in range(4, 7)},
        kind="unrestricted",
    )
    right_tree = compile_pui_tree(right)
    assert dict(right.extra_address_map) == {7: 6}
    assert dict(right_tree.extra_address_map) == dict(right.extra_address_map)


def test_full_unary_iteration_matches_paper_2w_minus_2_toffolis():
    for width in range(1, 6):
        plan = build_pui_plan(
            address_width=width,
            interval=(0, (1 << width) - 1),
            target_by_address={i: (width,) for i in range(1 << width)},
            kind="restricted",
        )
        tree = compile_pui_tree(plan)
        expected = (1 << width) - 2
        assert tree.paper_accounted_toffolis == expected
        assert tree.coherent_toffolis == 2 * expected
        assert tree.max_clean_ancillas <= width - 1


def test_repeated_aligned_interval_costs_match_equations_7_and_8():
    from fractions import Fraction

    for width in range(1, 6):
        for suffix_width in range(1, width + 1):
            interval_size = 1 << suffix_width
            prefix_width = width - suffix_width
            block_count = 1 << prefix_width
            restricted_total = 0
            unrestricted_total = 0

            for prefix in range(block_count):
                lo = prefix * interval_size
                hi = lo + interval_size - 1
                targets = {i: (width,) for i in range(lo, hi + 1)}

                restricted = compile_pui_tree(build_pui_plan(
                    address_width=width,
                    interval=(lo, hi),
                    target_by_address=targets,
                    kind="restricted",
                ))
                unrestricted = compile_pui_tree(build_pui_plan(
                    address_width=width,
                    interval=(lo, hi),
                    target_by_address=targets,
                    kind="unrestricted",
                ))

                expected_restricted = interval_size + prefix_width - 2
                if prefix_width == 0 or prefix == 0:
                    expected_unrestricted = interval_size - 2
                else:
                    expected_unrestricted = (
                        interval_size - 1 + max(prefix.bit_count() - 1, 0)
                    )
                assert restricted.paper_accounted_toffolis == expected_restricted
                assert unrestricted.paper_accounted_toffolis == expected_unrestricted
                restricted_total += restricted.paper_accounted_toffolis
                unrestricted_total += unrestricted.paper_accounted_toffolis

            assert restricted_total == block_count * (
                interval_size + prefix_width - 2
            )
            assert unrestricted_total == block_count * (
                interval_size + Fraction(prefix_width, 2) - 2
            )


def test_coherent_tree_uncomputes_every_ancilla_and_inverse_round_trips():
    cases = [
        (3, (0, 3), "unrestricted"),
        (3, (4, 6), "unrestricted"),
        (4, (2, 11), "restricted"),
        (4, (3, 9), "unrestricted"),
    ]
    for width, interval, kind in cases:
        lo, hi = interval
        plan = build_pui_plan(
            address_width=width,
            interval=interval,
            target_by_address={i: (width, width + 1) for i in range(lo, hi + 1)},
            kind=kind,
        )
        tree = compile_pui_tree(plan)
        address_space = 1 << width
        for address in range(address_space):
            for target_pattern in range(4):
                initial = _make_input_state(plan, tree, address, target_pattern)
                output = tree.apply(initial)
                assert all(output[wire] == "0" for wire in tree.used_ancilla_wires)
                assert simulate_basis_state(output, tree.inverse_gates()) == initial


def test_tree_uses_at_most_w_minus_one_depth_reused_ancillas():
    for width in range(1, 7):
        address_space = 1 << width
        interval = (0, address_space - 1) if width == 1 else (1, address_space - 2)
        lo, hi = interval
        plan = build_pui_plan(
            address_width=width,
            interval=interval,
            target_by_address={i: (width,) for i in range(lo, hi + 1)},
            kind="unrestricted",
        )
        tree = compile_pui_tree(plan)
        assert tree.max_clean_ancillas <= width - 1
        assert len(tree.ancilla_wires) == width - 1


def test_tree_emits_no_per_address_mcx_oracle_gates():
    plan = build_pui_plan(
        address_width=4,
        interval=(3, 12),
        target_by_address={i: (4,) for i in range(3, 13)},
        kind="unrestricted",
    )
    tree = compile_pui_tree(plan)
    assert not any(isinstance(g, MCX) for g in tree.gates)
    assert tree.coherent_toffolis == sum(
        isinstance(g, (Toffoli, NegativeControlToffoli)) for g in tree.gates
    )
    assert tree.paper_accounted_toffolis * 2 == tree.coherent_toffolis


def test_noncontiguous_address_wires_and_explicit_ancillas_are_supported():
    plan = build_pui_plan(
        address_width=3,
        interval=(1, 5),
        target_by_address={i: (4,) for i in range(1, 6)},
        address_wires=(2, 0, 3),
        kind="unrestricted",
    )
    # Wire 1 is an intentional gap; target is wire 4; reserve wires 5 and 6.
    tree = compile_pui_tree(plan, ancilla_wires=(5, 6))
    assert tree.ancilla_wires == (5, 6)
    for address in range(8):
        initial = _make_input_state(plan, tree, address, 0)
        assert tree.apply(initial) == simulate_basis_state(initial, plan.gates)


def test_ancilla_pool_must_be_disjoint_and_large_enough():
    plan = build_pui_plan(
        address_width=3,
        interval=(0, 7),
        target_by_address={i: (3,) for i in range(8)},
        kind="restricted",
    )
    with pytest.raises(ValueError, match="pool"):
        compile_pui_tree(plan, ancilla_wires=(4,))
    with pytest.raises(ValueError, match="disjoint"):
        compile_pui_tree(plan, ancilla_wires=(0, 4))


def test_restricted_tree_never_records_free_bits():
    plan = build_pui_plan(
        address_width=4,
        interval=(2, 9),
        target_by_address={i: (4,) for i in range(2, 10)},
        kind="restricted",
    )
    tree = compile_pui_tree(plan)
    assert tree.free_bit_positions == ()


def test_unrestricted_tree_records_ignored_left_split_bits():
    plan = build_pui_plan(
        address_width=4,
        interval=(0, 3),
        target_by_address={i: (4,) for i in range(4)},
        kind="unrestricted",
    )
    tree = compile_pui_tree(plan)
    assert tree.free_bit_positions == (0, 1)
