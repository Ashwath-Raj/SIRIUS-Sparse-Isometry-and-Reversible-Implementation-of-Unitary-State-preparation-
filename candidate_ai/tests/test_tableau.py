import pytest
from sparseprep.gates import CX, X, SWAP, Toffoli
from sparseprep.tableau import Tableau, TableauRow


def test_stable_row_ids_and_separate_phase_metadata():
    tab = Tableau.from_support(("000", "011", "101"), signs=(1, -1, 1))
    moved = tab.apply(X(0)).apply(CX(0, 2))
    assert [r.row_id for r in moved.rows] == [0, 1, 2]
    assert [r.original for r in moved.rows] == ["000", "011", "101"]
    assert [r.phase for r in moved.rows] == [1, -1, 1]
    assert moved.support == ("101", "110", "001")


def test_tableau_inverse_round_trip():
    tab = Tableau.from_support(("0000", "0011", "1010"), signs=(1, -1, -1))
    gates = (X(0), CX(0, 3), SWAP(1, 2), Toffoli(0, 1, 3))
    restored = tab.inverse_round_trip(gates)
    assert restored == tab


def test_duplicate_current_rows_rejected():
    with pytest.raises(ValueError, match="distinct"):
        Tableau((TableauRow(0, "00", "00"), TableauRow(1, "01", "00")))
