from sparseprep.model import make_problem
from sparseprep.malvetti_baseline import run_malvetti_baseline
from sparseprep.simulator import simulate_basis_state


def test_compresses_rupprecht_wolk_figure_3_input_tableau():
    # Seven-row input tableau from Rupprecht & Wölk (2026), Figure 3.
    # The paper permits any subspace label not already occupied; therefore
    # the valid output bijection need not match the figure's illustrated labels.
    support = (
        "0111011",
        "1110111",
        "1001010",
        "0110110",
        "1011101",
        "1001111",
        "1111010",
    )
    result = run_malvetti_baseline(make_problem(7, support))

    assert result.ell == 3
    assert result.residual_width == 4
    assert all(row[3:] == "0000" for row in result.final_tableau)
    assert tuple(int(row[:3], 2) for row in result.final_tableau) == result.f
    assert len(set(result.f)) == len(support)
    assert result.resources.zeroing_mcx_count == 7
    assert result.resources.toffolis_per_zeroing_mcx == 2
    assert result.resources.toffoli_count == 14
    assert result.resources.worst_case_toffoli_count == 14
    assert result.resources.clean_ancillas == 1


def test_rows_already_in_subspace_need_no_zeroing_mcx():
    problem = make_problem(3, ("000", "010", "110"))
    result = run_malvetti_baseline(problem)

    assert result.final_tableau == problem.support
    assert result.f == (0, 1, 3)
    assert result.resources.zeroing_mcx_count == 0
    assert result.resources.toffoli_count == 0
    assert result.resources.clean_ancillas == 0
    assert result.forward_gates == ()


def test_one_control_is_a_cx_and_has_zero_toffoli_cost():
    problem = make_problem(3, ("010", "110"))
    result = run_malvetti_baseline(problem)

    assert result.ell == 1
    assert result.final_tableau == ("000", "100")
    assert result.f == (0, 1)
    assert result.resources.zeroing_mcx_count == 2
    assert result.resources.toffolis_per_zeroing_mcx == 0
    assert result.resources.toffoli_count == 0
    assert result.resources.clean_ancillas == 0


def test_single_row_boundary_is_direct_x_mapping():
    problem = make_problem(5, ("10110",))
    result = run_malvetti_baseline(problem)

    assert result.ell == 0
    assert result.f == (0,)
    assert result.final_tableau == ("00000",)
    assert result.resources.zeroing_mcx_count == 0
    assert result.resources.toffoli_count == 0
    assert simulate_basis_state("00000", result.inverse_gates) == "10110"


def test_dense_subspace_boundary_has_no_isometry_work():
    # n=ell=2, so the non-subspace register is empty.
    problem = make_problem(2, ("00", "01", "10"))
    result = run_malvetti_baseline(problem)

    assert result.residual_width == 0
    assert result.final_tableau == problem.support
    assert result.resources.zeroing_mcx_count == 0
    assert result.resources.toffoli_count == 0
    assert result.resources.clean_ancillas == 0


def test_gate_sequence_updates_the_whole_tableau_and_inverse_recovers_inputs():
    problem = make_problem(
        6,
        ("010101", "110011", "000111", "011010", "111100"),
    )
    result = run_malvetti_baseline(problem)

    assert len(set(result.final_tableau)) == problem.s
    for original, compacted in zip(problem.support, result.final_tableau):
        assert simulate_basis_state(original, result.forward_gates) == compacted
        assert simulate_basis_state(compacted, result.inverse_gates) == original


def test_actual_toffoli_cost_never_exceeds_paper_worst_case():
    problem = make_problem(
        8,
        ("10101010", "00110101", "11100011", "01011100", "10011010", "01101001"),
    )
    result = run_malvetti_baseline(problem)

    assert result.resources.toffoli_count == (
        result.resources.zeroing_mcx_count * max(result.ell - 1, 0)
    )
    assert result.resources.toffoli_count <= result.resources.worst_case_toffoli_count
    assert result.resources.worst_case_toffoli_count == problem.s * max(problem.ell - 1, 0)


def test_randomized_small_tableaux_are_compressed_and_reversible():
    import random

    rng = random.Random(20261114)
    for n in range(2, 8):
        universe = [format(i, f"0{n}b") for i in range(1 << n)]
        for s in range(2, min(10, 1 << n) + 1):
            support = tuple(rng.sample(universe, s))
            result = run_malvetti_baseline(make_problem(n, support))
            result.verify()
            assert len(set(result.f)) == s
            assert all(row[result.ell:] == "0" * result.residual_width for row in result.final_tableau)
            assert result.resources.toffoli_count <= result.resources.worst_case_toffoli_count
