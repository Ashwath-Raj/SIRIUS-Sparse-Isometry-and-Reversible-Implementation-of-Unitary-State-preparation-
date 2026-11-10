# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

import numpy as np

def find_bijection_and_circuit(
    state: np.ndarray,
    signs: np.ndarray | None,
    sub_problem_size: int | None,
) -> tuple[
    list[tuple[int, int]],
    list[tuple["BatchCreationData", "BatchZeroingData"]],
]:
    """
    Find the bijection and the circuit mapping the ``state`` into a
    logarithmically sized subspace and fixing the ``signs`` if there are any.

    Parameters
    ----------
    state : np.ndarray
        A 2-D ``numpy`` array of ``bool`` representing the tableau
        (rows x columns).
    signs : np.ndarray | None
        Optional 1-D ``numpy`` array of ``bool`` containing the
        sign information for each row.
    sub_problem_size : int | None
        Optional integer controlling the sizes of the sub-problems used by the
        underlying classical algorithm.  When omitted the algorithm runs in a
        single pass.

    Returns
    -------
    tuple[list[int], list[Tuple[BatchCreationData, BatchZeroingData]]]
        * bijection - a list of pairs ``(subspace_content, row)``
        where ``subspace_content`` is the content ``|subspabe_content>``
        of the subspace at the end of the algorithm and ``row`` is the
        index of the original basis vector in the tableau.
        * circuit - a list of batches.  Each batch is a tuple
        ``(BatchCreationData, BatchZeroingData)`` describing how to create
        and subsequently zero the batch.
    """
    ...

def fast_toffoli_counter(
    circuit: list[tuple[BatchCreationData, BatchZeroingData]],
) -> int:
    """Return an upper-bound estimate of the total number of Toffoli gates needed.

    The function walks through a quantum-circuit description (a list of
    ``(create_batch, zero_batch)`` tuples) and adds together the Toffoli-gate
    counts reported by each batch.  The result is **only an upper bound**.

    Parameters
    ----------
    circuit : list[tuple[BatchCreationData, BatchZeroingData]]
        A list representing the quantum circuit.  Each element is a two-item
        tuple:

        * ``create_batch`` - an instance of :class:`BatchCreationData` that
        knows how many Toffoli gates are required to create the batch.
        * ``zero_batch`` - an instance of :class:`BatchZeroingData` that knows
        how many Toffoli gates are required to reset (zero) the batch.

    Returns
    -------
    int
        The summed upper-bound count of Toffoli gates for the whole circuit.
    """

class ColumnFix(Enum):
    """
    Types of fixes that may be applied to create a target column that has a
    non-zero element.

    Variants
    --------
    Swap(target: int)
        Swap the target column with a non-trivial column.

    Toffoli(control0: int, control1: tuple[int, bool])
        Apply a Toffoli with the target column as target and one column with
        positive control and another column with positive or negative control.

    ExtraCX(controls: list[int])
        Apply first a CX gate controlled on the extra column on the target
        column.  Then fix potential bit flips in batch columns by applying
        CX gates with controls on the respective target columns of those
        batch elements on the target column.
    """

    # The concrete enum members are created by the Rust side; they are only
    # listed here for type-checking purposes.
    Swap = ...
    Toffoli = ...
    ExtraCX = ...

    def __repr__(self) -> str: ...

class PrepareRowData:
    """
    Store data for preparing a row.

    Attributes
    ----------
    target_column : int
        Target column, i.e. a column with a non-zero element we can use as the
        control to write the desired row content.
    column_fix : ColumnFix | None
        A potentially needed fix to create the target column.
    toggles : list[int]
        Rows we need to toggle controlled on ``target_column`` such that we
        get the correct row content.
    """

    target_column: int
    column_fix: ColumnFix | None
    toggles: list[int]

    def __repr__(self) -> str: ...

class BatchCreationData:
    """
    Store data for creating a batch.

    Attributes
    ----------
    rows_preparations : list[None | PrepareRowData]
        Row preparations needed for creating a batch.  If for a row we do
        not need to do anything store ``None``.
    """

    rows_preparations: list[None | PrepareRowData]

    def __repr__(self) -> str: ...

class BatchZeroingData:
    """
    Store data for zeroing a batch.

    Attributes
    ----------
    interval_start : int
        Starting address value for the partial unary iteration.
    fixed : list[tuple[int, bool]]
        Control qubits and control values that are fixed for all elements in
        the batch.
    operations : list[tuple[int, bool, bool]]
        Operations to apply controls on the remaining control qubits.
        * First element - the qubit to toggle.
        * Second element - whether to apply a sign-flip.
        * Third element - whether to toggle the extra qubit.
    restricted: bool
        Indicates whether the PUI is restricted or not.
    """

    interval_start: int
    fixed: list[tuple[int, bool]]
    operations: list[tuple[int, bool, bool]]
    restricted: bool

    def __repr__(self) -> str: ...
