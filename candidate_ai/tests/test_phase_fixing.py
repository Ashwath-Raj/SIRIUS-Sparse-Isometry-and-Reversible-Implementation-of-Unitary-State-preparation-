from __future__ import annotations

import random

import pytest

from sparseprep.algorithms.phase_fixing import PhaseFixingError, PhaseFixingTableau


def make_tableau(signs=(1, -1, 1, -1)):
    return PhaseFixingTableau.from_support(
        ["0000", "0011", "1100", "1111"], list(signs)
    )


def test_marker_column_is_initialized_to_one_and_is_extra_to_data_width():
    tableau = make_tableau()
    assert tableau.n_qubits == 4
    assert tableau.markers == (1, 1, 1, 1)
    assert tableau.accumulated_phases == (1, 1, 1, 1)
    assert tableau.visit_counts == (0, 0, 0, 0)


def test_sign_input_accepts_only_exact_plus_minus_one():
    for bad in (0, 2, -2, True, False, 1.0, -1.0, 1j):
        with pytest.raises((PhaseFixingError, TypeError)):
            PhaseFixingTableau(["00"], [bad])


def test_rejects_empty_duplicate_or_malformed_support():
    with pytest.raises(PhaseFixingError):
        PhaseFixingTableau([], [])
    with pytest.raises(PhaseFixingError):
        PhaseFixingTableau(["00", "00"], [1, -1])
    with pytest.raises(PhaseFixingError):
        PhaseFixingTableau(["0x"], [1])
    with pytest.raises(PhaseFixingError):
        PhaseFixingTableau(["0"], [1, -1])


def test_basis_permutation_gates_preserve_row_identity_and_sign_ledger():
    tableau = make_tableau()
    original = tableau.current_tableau
    tableau.apply_x(0)
    tableau.apply_cx(0, 2)
    tableau.apply_swap(1, 3)
    tableau.apply_toffoli(0, 1, 2)
    tableau.apply_cmx(0, (1, 3))
    assert len(set(tableau.current_tableau)) == tableau.support_size
    assert tableau.initial_tableau == original
    assert tableau.signs == (1, -1, 1, -1)
    assert tableau.accumulated_phases == (1, 1, 1, 1)
    assert tableau.markers == (1, 1, 1, 1)
    assert [e.kind for e in tableau.trace] == ["X", "CX", "SWAP", "TOFFOLI", "CMX"]


def test_marker_controlled_cx_only_changes_rows_whose_marker_is_still_one():
    tableau = make_tableau()
    tableau.record_restricted_pui_visit(
        {0: "0000"}, affected_row_ids={0}, interval=(0, 0)
    )
    before = tableau.current_tableau
    tableau.apply_marker_cx(3)
    after = tableau.current_tableau
    assert after[0] == before[0]
    assert after[1][3] != before[1][3]
    assert after[2][3] != before[2][3]
    assert after[3][3] != before[3][3]
    assert tableau.markers == (0, 1, 1, 1)



def test_counter_effect_cx_requires_marked_batch_row_and_is_global():
    tableau = PhaseFixingTableau(["10", "11", "00", "01"], [1, -1, 1, -1])
    assert tableau.marked_unvisited_rows() == (0, 1, 2, 3)
    tableau.apply_counter_effect_cx(batch_row_id=0, control=0, target=1)
    assert tableau.current_tableau == ("11", "10", "00", "01")
    assert tableau.marked_unvisited_rows() == (0, 1, 2, 3)
    assert tableau.trace[-1].detail == "Algorithm 3 counter-effect CX for batch row 0"


def test_counter_effect_cx_rejects_unmarked_or_nonmatching_control_row():
    tableau = PhaseFixingTableau(["10", "01"], [1, -1])
    with pytest.raises(PhaseFixingError, match="control wire"):
        tableau.apply_counter_effect_cx(batch_row_id=1, control=0, target=1)
    tableau.record_restricted_pui_visit(
        {0: "10"}, affected_row_ids={0}, interval=(0, 0)
    )
    with pytest.raises(PhaseFixingError, match="marker 1"):
        tableau.apply_counter_effect_cx(batch_row_id=0, control=0, target=1)

def test_restricted_pui_visit_applies_sign_and_clears_marker_once():
    tableau = make_tableau()
    tableau.record_restricted_pui_visit(
        {0: "0100", 1: "0111"},
        affected_row_ids={0, 1},
        interval=(0, 1),
    )
    assert tableau.current_tableau == ("0100", "0111", "1100", "1111")
    assert tableau.markers == (0, 0, 1, 1)
    assert tableau.accumulated_phases == (1, -1, 1, 1)
    assert tableau.visit_counts == (1, 1, 0, 0)
    event = tableau.trace[-1]
    assert event.kind == "RESTRICTED_PUI_SIGN_FIX"
    assert event.row_ids == (0, 1)
    assert event.phase_multipliers == ((0, 1), (1, -1))


def test_restricted_pui_requires_explicit_complete_affected_row_set():
    tableau = make_tableau()
    before = tableau.summary()
    with pytest.raises(PhaseFixingError, match="coverage mismatch"):
        tableau.record_restricted_pui_visit(
            {0: "0000"}, affected_row_ids={0, 2}, interval=(0, 1)
        )
    assert tableau.summary() == before


def test_restricted_pui_update_is_transactional_if_it_would_collapse_rows():
    tableau = make_tableau()
    before = tableau.summary()
    with pytest.raises(PhaseFixingError, match="collapse"):
        tableau.record_restricted_pui_visit(
            {0: "0011"}, affected_row_ids={0}, interval=(0, 0)
        )
    assert tableau.summary() == before


def test_a_row_cannot_be_sign_fixed_twice():
    tableau = make_tableau()
    update = {0: "0100"}
    tableau.record_restricted_pui_visit(update, affected_row_ids={0}, interval=(0, 0))
    before = tableau.summary()
    with pytest.raises(PhaseFixingError, match="already been visited"):
        tableau.record_restricted_pui_visit(
            {0: "0000"}, affected_row_ids={0}, interval=(0, 0)
        )
    assert tableau.summary() == before


def test_completed_signed_mapping_checks_output_phase_and_total_coverage():
    tableau = make_tableau()
    targets = {0: "0000", 1: "0001", 2: "0010", 3: "0011"}
    tableau.record_restricted_pui_visit(
        targets, affected_row_ids=set(targets), interval=(0, 3)
    )
    tableau.verify_completed(targets)


def test_completed_mapping_rejects_wrong_phase_or_unvisited_row():
    tableau = make_tableau()
    targets = {0: "0000", 1: "0001", 2: "0010", 3: "0011"}
    tableau.record_restricted_pui_visit(
        targets, affected_row_ids=set(targets), interval=(0, 3)
    )
    tableau.row(1).global_phase = 1
    with pytest.raises(PhaseFixingError, match="phase mismatch"):
        tableau.verify_completed(targets)

    partial = make_tableau()
    partial.record_restricted_pui_visit(
        {0: "0000"}, affected_row_ids={0}, interval=(0, 0)
    )
    with pytest.raises(PhaseFixingError, match="not visited exactly once"):
        partial.verify_completed({0: "0000", 1: "0001", 2: "0010", 3: "0011"})


@pytest.mark.parametrize(
    "signs",
    [
        [1, 1, 1, 1],
        [-1, -1, -1, -1],
        [1, -1, 1, -1],
        [-1, 1, -1, 1],
    ],
)
def test_standard_sign_patterns_reach_exact_requested_phase(signs):
    support = ["000", "011", "101", "110"]
    tableau = PhaseFixingTableau(support, signs)
    outputs = {0: "000", 1: "001", 2: "010", 3: "011"}
    tableau.record_restricted_pui_visit(
        outputs, affected_row_ids={0, 1, 2, 3}, interval=(0, 3)
    )
    tableau.verify_completed(outputs)
    assert tableau.accumulated_phases == tuple(signs)


def test_seeded_random_sign_patterns_and_nontrivial_visit_partition():
    rng = random.Random(20261115)
    support = ["00000", "00101", "01010", "01111", "10011", "11100"]
    signs = [rng.choice((-1, 1)) for _ in support]
    tableau = PhaseFixingTableau(support, signs)
    # The two visits model two restricted intervals; Phase 7.2 will generate
    # these affected-row sets from the actual PUI interval/address semantics.
    first = {0: "00000", 2: "01000", 4: "10001"}
    second = {1: "00100", 3: "01100", 5: "11101"}
    tableau.record_restricted_pui_visit(
        first, affected_row_ids=set(first), interval=(0, 2)
    )
    tableau.record_restricted_pui_visit(
        second, affected_row_ids=set(second), interval=(3, 5)
    )
    expected = {**first, **second}
    tableau.verify_completed(expected)
    assert tableau.accumulated_phases == tuple(signs)


def test_summary_is_json_serializable_and_reports_trace():
    import json

    tableau = make_tableau()
    tableau.apply_cx(0, 1)
    json.dumps(tableau.summary())
    assert tableau.summary()["trace_event_count"] == 1
    assert tableau.summary()["trace_kinds"] == ["CX"]
