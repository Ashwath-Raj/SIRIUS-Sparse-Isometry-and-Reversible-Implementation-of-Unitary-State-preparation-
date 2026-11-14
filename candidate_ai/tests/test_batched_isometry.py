from __future__ import annotations

import random

import pytest

from sparseprep.batched_isometry import run_batched_isometry
from sparseprep.model import SparseStateProblem
from sparseprep.simulator import simulate_basis_state


# Figure 4, Rupprecht & Wölk (2026): seven 7-bit input rows written as
# 3-bit subspace register followed by 4-bit residual register.
FIGURE_4_SUPPORT = (
    "0111011",
    "1110111",
    "1001010",
    "0110110",
    "1011101",
    "1001111",
    "1111010",
)


def test_figure_4_tableau_is_compressed_and_reversible() -> None:
    result = run_batched_isometry(SparseStateProblem(7, FIGURE_4_SUPPORT))

    assert result.ell == 3
    assert result.residual_width == 4
    assert result.batch_size_limit == 4
    assert len(set(result.f)) == 7
    assert all(row[3:] == "0000" for row in result.final_tableau)
    result.verify()

    for row_id, initial in enumerate(FIGURE_4_SUPPORT):
        assert simulate_basis_state(initial + "00", result.forward_gates) == (
            result.final_tableau[row_id] + "00"
        )
        assert simulate_basis_state(
            result.final_tableau[row_id] + "00", result.inverse_gates
        ) == initial + "00"


def test_algorithm_uses_direct_swap_and_distinguishing_toffoli_paths() -> None:
    result = run_batched_isometry(SparseStateProblem(7, FIGURE_4_SUPPORT))
    methods = {step.method for step in result.batch_steps}

    assert methods == {"direct", "swap", "toffoli"}
    assert result.resources.batch_fallback_toffolis == 1
    assert result.resources.batch_swap_count == 3
    assert result.resources.batch_cmx_count > 0
    assert any(step.toffoli_controls is not None for step in result.batch_steps)
    assert all(step.state_after.startswith(format(step.label, "03b")) for step in result.batch_steps)

    swap_step = next(step for step in result.batch_steps if step.method == "swap")
    assert swap_step.swap_wires is not None
    swapped = list(swap_step.state_before)
    a, b = swap_step.swap_wires
    swapped[a], swapped[b] = swapped[b], swapped[a]
    assert "".join(swapped) == swap_step.state_after_activation

    toffoli_step = next(step for step in result.batch_steps if step.method == "toffoli")
    assert toffoli_step.toffoli_controls is not None
    assert toffoli_step.state_before != toffoli_step.state_after_activation
    changed = [i for i, (a, b) in enumerate(zip(
        toffoli_step.state_before, toffoli_step.state_after_activation
    )) if a != b]
    assert changed == [toffoli_step.cmx_control]


def test_unrestricted_pui_records_extra_address_side_effect_map() -> None:
    result = run_batched_isometry(SparseStateProblem(7, FIGURE_4_SUPPORT))
    first_event = result.pui_events[0]

    assert first_event.kind == "unrestricted"
    assert first_event.interval == (0, 3)
    assert first_event.extra_address_map == ((4, 0), (5, 1), (6, 2), (7, 3))
    assert first_event.gate_count > 0
    # verify() replays G on every support row, including rows outside the batch
    # that may be transformed by unrestricted-PUI extra-address mappings.
    result.verify()


def test_final_restricted_pui_collision_is_repaired_even_at_nonterminal_label() -> None:
    # The already-in-subspace row at prefix 00 is hit by the restricted PUI
    # on the first address of the final [0,1] interval. This exercises the
    # implementation's explicitly documented generalized one-hot repair.
    support = ("000000", "011101", "100110")
    result = run_batched_isometry(SparseStateProblem(6, support))

    assert result.resources.final_collision_repair_count == 1
    assert result.resources.equation_3_bound_applicable
    assert result.correction_row_ids == (0,)
    assert result.correction_labels == (2,)
    assert result.final_tableau[0] == "100000"
    assert all(row[2:] == "0000" for row in result.final_tableau)
    result.verify()


def test_resource_accounting_separates_paper_and_coherent_uncomputation() -> None:
    result = run_batched_isometry(SparseStateProblem(7, FIGURE_4_SUPPORT))
    resources = result.resources

    assert resources.pui_coherent_toffolis >= resources.pui_paper_accounted_toffolis
    assert resources.total_paper_accounted_toffolis == (
        resources.pui_paper_accounted_toffolis
        + resources.batch_fallback_toffolis
        + resources.correction_mcx_paper_toffolis
    )
    assert resources.total_coherent_toffolis == (
        resources.pui_coherent_toffolis
        + resources.batch_fallback_toffolis
        + resources.correction_mcx_coherent_toffolis
    )
    assert resources.clean_ancilla_pool_size == result.ell - 1
    assert resources.max_clean_ancillas_used <= result.ell - 1
    assert resources.equation_1_isometry_upper_bound is not None
    assert resources.total_paper_accounted_toffolis <= (
        resources.equation_1_isometry_upper_bound + 1e-9
    )


def test_single_support_row_is_normalized_to_zero_state() -> None:
    for initial in ("00000", "10101", "11111"):
        result = run_batched_isometry(SparseStateProblem(5, (initial,)))
        assert result.final_tableau == ("00000",)
        assert result.f == (0,)
        assert simulate_basis_state(initial, result.forward_gates) == "00000"
        assert simulate_basis_state("00000", result.inverse_gates) == initial


def test_zero_residual_width_is_identity_embedding() -> None:
    support = ("000", "001", "010", "011", "100")
    result = run_batched_isometry(SparseStateProblem(3, support))

    assert result.ell == 3
    assert result.residual_width == 0
    assert result.final_tableau == support
    assert result.f == tuple(int(row, 2) for row in support)
    assert result.forward_gates == ()
    result.verify()


def test_m_one_boundary_does_not_report_invalid_equation_1_value() -> None:
    result = run_batched_isometry(SparseStateProblem(2, ("01", "11")))
    assert result.batch_size_limit == 1
    assert result.resources.equation_1_isometry_upper_bound is None
    assert "m=1" in result.resources.equation_1_bound_note
    result.verify()


def test_seeded_random_small_tableaux_are_compressed_and_reversible() -> None:
    rng = random.Random(20261114)
    cases = 0
    for n in range(2, 8):
        max_s = min(8, 1 << n)
        for s in range(1, max_s + 1):
            values = rng.sample(range(1 << n), s)
            support = tuple(format(value, f"0{n}b") for value in values)
            result = run_batched_isometry(SparseStateProblem(n, support))
            result.verify()
            assert len(set(result.f)) == s
            assert all(row[result.ell:] == "0" * result.residual_width for row in result.final_tableau)
            cases += 1
    assert cases >= 44


def test_invalid_problem_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="SparseStateProblem"):
        run_batched_isometry(("000", "111"))  # type: ignore[arg-type]
