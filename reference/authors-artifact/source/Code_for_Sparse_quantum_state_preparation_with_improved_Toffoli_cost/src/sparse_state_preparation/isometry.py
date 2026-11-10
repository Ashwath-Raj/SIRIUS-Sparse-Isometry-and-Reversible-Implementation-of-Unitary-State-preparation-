# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

from functools import cached_property

import numpy as np
from attrs import field, frozen
from qualtran import (
    Bloq,
    BloqBuilder,
    QBit,
    QUInt,
    Register,
    Side,
    Signature,
    SoquetT,
    bloq_example,
)
from qualtran.bloqs.basic_gates import CNOT, Toffoli, TwoBitSwap, XGate, ZGate, OneState
from qualtran.bloqs.bookkeeping import Partition
from qualtran.bloqs.mcmt import MultiTargetCNOT

from ._isometry_algorithms import (
    BatchCreationData,
    BatchZeroingData,
    ColumnFix,
    PrepareRowData,
    find_bijection_and_circuit,
)
from .partial_unary_iteration import PartialUnaryIteration


def data_to_tuple(data: np.ndarray | None) -> tuple | None:
    """
    Convert a NumPy array (or ``None``) into a hash-able tuple.
    This is used for comparing/hashing.
    """
    if data is None:
        return None
    return tuple(data.flatten()) + tuple(data.shape)


@frozen
class PrepareRow(Bloq):
    r"""
    Prepare a single row of a batch.

    Registers
    ----------
    - state : ``QBit`` register of shape ``(bitsize,)``
        The full computational-basis register that holds the current state.

    - extra : ``QBit`` (optional)
        Present only when ``extra_qubit`` is ``True``. It stores the auxiliary
        extra qubit used for phase-flip handling.
    """

    data: PrepareRowData
    """Classical description of the row preparation. It contains
        - ``target_column`` - the column that will become the control for the
        rest of the row.
        - ``column_fix`` - an optional :class:`ColumnFix` that must be applied
        before the target column contains a ``1``. The fix can be a
        ``Swap``, a ``Toffoli`` or an ``ExtraCX`` sequence.
        - ``toggles`` - a list of column indices that have to be flipped
        (X-gate) controlled on the target column to obtain the exact row
        pattern."""

    bitsize: int
    """Width of the ``state`` register."""

    extra_qubit: bool
    """``True`` if a separate ``extra`` qubit is present.
        The extra qubit is accessed via the ``extra`` register."""

    @property
    def signature(self) -> Signature:
        registers = [
            Register("state", QBit(), shape=self.bitsize),
        ]
        if self.extra_qubit:
            registers.append(Register("extra", QBit()))
        return Signature(registers)

    def build_composite_bloq(
        self, bb: BloqBuilder, state: SoquetT, **soqs
    ) -> dict[str, SoquetT]:
        fix = self.data.column_fix

        # see Rust code for further description.
        if isinstance(fix, ColumnFix.Toffoli):
            if not fix.control1[1]:
                state[fix.control1[0]] = bb.add(XGate(), q=state[fix.control1[0]])

            (
                [state[fix.control0], state[fix.control1[0]]],
                state[self.data.target_column],
            ) = bb.add(
                Toffoli(),
                ctrl=[state[fix.control0], state[fix.control1[0]]],
                target=state[self.data.target_column],
            )

            if not fix.control1[1]:
                state[fix.control1[0]] = bb.add(XGate(), q=state[fix.control1[0]])

        elif isinstance(fix, ColumnFix.ExtraCX):
            soqs["extra"], state[self.data.target_column] = bb.add(
                CNOT(), ctrl=soqs.pop("extra"), target=state[self.data.target_column]
            )
            for control in fix[0]:
                state[control], state[self.data.target_column] = bb.add(
                    CNOT(), ctrl=state[control], target=state[self.data.target_column]
                )

        elif isinstance(fix, ColumnFix.Swap):
            state[fix[0]], state[self.data.target_column] = bb.add(
                TwoBitSwap(), x=state[fix[0]], y=state[self.data.target_column]
            )

        if len(self.data.toggles) > 0:
            state[self.data.target_column], state[self.data.toggles] = bb.add(
                MultiTargetCNOTShaped(len(self.data.toggles)),
                control=state[self.data.target_column],
                targets=state[self.data.toggles],
            )
        soqs["state"] = state
        return soqs


@frozen
class BatchCreation(Bloq):
    r"""
    Create a batch of rows.

    Registers
    ----------
    - state : ``QBit`` register of shape ``(bitsize,)``
        The full computational-basis register that holds the current state.

    - extra : ``QBit`` (optional)
        Present only when ``extra_qubit`` is ``True``. It stores the auxiliary
        extra qubit used for phase-flip handling.
    """

    data: BatchCreationData
    """Classical description of the whole batch. It stores a list
        ``rows_preparations`` where each entry is either ``None`` (the row is
        already in the correct form) or a :class:`PrepareRowData` instance that
        must be executed."""

    bitsize: int
    """Width of the ``state`` register."""

    extra_qubit: bool
    """``True`` if a separate ``extra`` qubit is present.
        The extra qubit is accessed via the ``extra`` register."""

    @property
    def signature(self) -> Signature:
        registers = [
            Register("state", QBit(), shape=self.bitsize),
        ]
        if self.extra_qubit:
            registers.append(Register("extra", QBit()))
        return Signature(registers)

    def build_composite_bloq(self, bb: BloqBuilder, **soqs) -> dict[str, SoquetT]:
        for row_prep in self.data.rows_preparations:
            if row_prep is not None:
                soqs = bb.add_d(
                    PrepareRow(row_prep, self.bitsize, self.extra_qubit), **soqs
                )

        return soqs


@frozen
class BatchZeroing(Bloq):
    r"""
    Zero the non-subspace part of a batch using a Partial Unary Iteration
    (PUI) circuit.

    Registers
    ----------
    - state : ``QBit`` register of shape ``(bitsize,)``
        The full register that is split into an address part (the future
        ``subspace`` register) and an ``operation`` part that is processed by the PUI.

    - extra : ``QBit`` (optional)
        Present only when ``extra_qubit`` is ``True``. It stores the auxiliary
        extra qubit used for phase-flip handling.
    """

    data: BatchZeroingData
    """Classical description of the zero-ing phase.  It contains

        * ``interval_start`` - the address value of the first element in the batch.
        * ``operations`` - a list of triples ``(target, sign_flip, toggle_extra)``.
        For each entry a controlled X is applied to ``target``; if
        ``sign_flip`` is ``True`` a ``-1`` phase is introduced; if
        ``toggle_extra`` is ``True`` the extra qubit is also flipped.
        * ``restricted`` - whether the PUI is the restricted variant
        (fewer controls)."""

    bitsize: int
    """Width of the full ``state`` register."""

    extra_qubit: bool
    """``True`` if a separate ``extra`` qubit is present.
        The extra qubit is accessed via the ``extra`` register."""

    subspace_bitsize: int
    """Number of qubits that will finally hold the compact sub-space index."""

    @property
    def signature(self) -> Signature:
        registers = [
            Register("state", QBit(), shape=self.bitsize),
        ]
        if self.extra_qubit:
            registers.append(Register("extra", QBit()))
        return Signature(registers)

    def build_composite_bloq(
        self, bb: BloqBuilder, state: SoquetT, **soqs
    ) -> dict[str, SoquetT]:
        operation_bitsize = self.bitsize - self.subspace_bitsize

        partition = Partition(
            self.bitsize,
            [
                Register(
                    "address",
                    QUInt(self.subspace_bitsize),
                ),
                Register("operation", QBit(), shape=(operation_bitsize,)),
            ],
        )

        address, operation = bb.add(partition, x=bb.join(state))

        soqs = bb.add_d(
            PartialUnaryIteration(
                interval=(
                    self.data.interval_start,
                    self.data.interval_start + len(self.data.operations),
                ),
                bloqs=tuple(
                    ToggleWithPhase(
                        operation_bitsize, *op[:2], op[2] if self.extra_qubit else None
                    )
                    for op in self.data.operations
                ),
                address_dtype=QUInt(self.subspace_bitsize),
                restricted=self.data.restricted,
            ),
            address=address,
            operation=operation,
            **soqs,
        )

        soqs["state"] = bb.split(
            bb.add(
                partition.adjoint(),
                address=soqs.pop("address"),
                operation=soqs.pop("operation"),
            )
        )
        return soqs


@frozen
class MultiTargetCNOTShaped(Bloq):
    r"""
    Wrapper around :class:`qualtran.bloqs.mcmt.MultiTargetCNOT` that respects a
    shaped target register.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - control : ``QBit``
        The single control qubit for the multi-target CNOT.

    - targets : ``QBit`` register of shape ``(target_len,)``
        The target qubits that will be flipped when ``control`` is ``|1⟩``.
    """

    target_len: int
    """Number of target qubits.  The Bloq expects a register ``targets`` with
        shape ``(target_len,)`` and a single ``control`` qubit."""

    @property
    def signature(self) -> Signature:
        """@private"""
        return Signature(
            [
                Register("control", QBit()),
                Register("targets", QBit(), shape=(self.target_len,)),
            ]
        )

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    def build_composite_bloq(
        self, bb: BloqBuilder, control: SoquetT, targets: SoquetT
    ) -> dict[str, SoquetT]:
        """@private"""

        targets = bb.join(targets)
        control, targets = bb.add(
            MultiTargetCNOT(bitsize=self.target_len), control=control, targets=targets
        )
        targets = bb.split(targets)
        return {"control": control, "targets": targets}


@frozen
class ToggleWithPhase(Bloq):
    r"""
    Apply a controlled X on a single qubit of the ``operation`` register and,
    optionally, a phase flip and/or an X on the extra sign qubit.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - operation : ``QBit`` register of shape ``(bitsize,)``
        The register that holds the ``operation`` qubits.
        The ``index``-th qubit is flipped by an X-gate.

    - extra : ``QBit`` (optional)
        Present only when ``extra_qubit`` is not ``None``.
    """

    bitsize: int
    """Size of the ``operation`` register."""

    index: int
    """Position inside the ``operation`` register that will be toggled."""

    phase_flip: bool
    """If ``True`` a ``-1`` phase is introduced."""

    extra_qubit: bool | None
    """``None`` - the top-level problem has no extra qubit.
        ``True`` - the extra qubit is present and is flipped.
        ``False`` - the extra qubit is present and is not flipped.
        """

    @property
    def signature(self) -> Signature:
        """@private"""
        registers = [
            Register("operation", QBit(), shape=self.bitsize),
        ]
        if self.extra_qubit is not None:
            registers.append(Register("extra", QBit()))
        return Signature(registers)

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    def build_composite_bloq(self, bb: BloqBuilder, **soqs) -> dict[str, SoquetT]:
        """@private"""
        operation = soqs.pop("operation")

        operation[self.index] = bb.add(XGate(), q=operation[self.index])

        soqs["operation"] = operation

        if self.extra_qubit:
            soqs["extra"] = bb.add(XGate(), q=soqs.pop("extra"))

        if self.phase_flip:
            anc = bb.allocate(1)
            anc = bb.add(XGate(), q=anc)
            anc = bb.add(ZGate(), q=anc)
            anc = bb.add(XGate(), q=anc)
            bb.free(anc)

        return soqs


@frozen
class IsometryToSubspaceViaBatching(Bloq):
    r"""
    Isometry bloq that maps a set of computational-basis states
    ``states`` (size ``d x n``) to a compact $\lceil \log_2 d\rceil$-qubit sub-space.

    Note that no symbolic version of the bloq is provided as the ressource count
    depends on the concrete input states and may only be upper bounded symbolically.

    Registers
    ----------
    - full : ``QUInt(self.state_bitsize)`` (LEFT side)
        The input register that holds the original ``n``-qubit computational basis
        state.

    - subspace : ``QUInt(self.subspace_bitsize)`` (RIGHT side)
        The output register.

    - extra : ``QBit`` (optional)
        Present only when ``signs`` is not ``None``.  It stores the auxiliary
        extra qubit that is used to implement the optional phase flips.
    """

    states: np.ndarray = field(eq=lambda x: data_to_tuple(x))
    """Binary matrix whose rows are the basis states that must be mapped.
        Each row corresponds to a basis vector ``|v_i>`` on the full ``n``-qubit
        register."""

    signs: np.ndarray | None = field(eq=lambda x: data_to_tuple(x), default=None)
    """Optional vector of length ``d``.  ``True`` indicates that the
        corresponding row should acquire a relative phase ``-1``.  When supplied,
        an additional ``extra`` qubit is allocated and used throughout the
        circuit."""

    sub_problem_size: int | None = None
    """If given, the classical algorithm splits the problem into sub-problems
        of sizes ``sub_problem_size``*256 (see ``Problem::run_via_subproblems`` 
        in the Rust code). This way multithreading may be used to accelerate 
        the runtime of the classical algorithm."""

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    @property
    def subspace_bitsize(self) -> int:
        """Width of the subspace."""
        return int(np.ceil(np.log2(self.states.shape[0])))

    @property
    def state_bitsize(self) -> int:
        """Width of the full state register."""
        return self.states.shape[1]

    @property
    def signature(self) -> Signature:
        """@private"""
        return Signature(
            [
                Register("full", QUInt(self.state_bitsize), side=Side.LEFT),
                Register("subspace", QUInt(self.subspace_bitsize), side=Side.RIGHT),
            ]
        )

    @cached_property
    def _bloq_and_bijection(
        self,
    ) -> tuple[list[tuple[int, int]], list[tuple[BatchCreationData, BatchZeroingData]]]:
        """
        Run the classical algorithm for finding the bijection and circuit.
        """
        return find_bijection_and_circuit(
            self.states, self.signs, self.sub_problem_size
        )

    @property
    def bijection(self) -> np.ndarray:
        """
        Each row ``[subspace_content, row]`` in the array corresponds to the
        row index of the input basis state ``|v_row>`` such that ``|v_row>`` gets
        mapped to ``|subspace_content>`` by the circuit.
        """
        return np.array(self._bloq_and_bijection[0])

    @property
    def circuit(self) -> tuple[tuple[BatchCreationData, BatchZeroingData], ...]:
        """
        Pairs of objects that represent the gates applied for first creating a batch
        and then zeroing the non-subspace element of the states within the batch.
        """
        return tuple(self._bloq_and_bijection[1])

    def build_composite_bloq(
        self, bb: BloqBuilder, full: SoquetT
    ) -> dict[str, SoquetT]:
        """@private"""

        soqs = {"state": bb.split(full)}

        extra_qubit = self.signs is not None
        if extra_qubit:
            soqs["extra"] = bb.add(OneState())

        for batch_creation, batch_zeroing in self.circuit:
            soqs = bb.add_d(
                BatchCreation(batch_creation, self.state_bitsize, extra_qubit), **soqs
            )
            soqs = bb.add_d(
                BatchZeroing(
                    batch_zeroing,
                    self.state_bitsize,
                    extra_qubit,
                    self.subspace_bitsize,
                ),
                **soqs,
            )

        if extra_qubit:
            bb.free(soqs.pop("extra"))

        full = soqs.pop("state")
        soqs["subspace"], rest = (
            bb.join(full[: self.subspace_bitsize], dtype=QUInt(self.subspace_bitsize)),
            bb.join(full[self.subspace_bitsize :]),
        )
        bb.free(rest)

        return soqs


@bloq_example()
def _isometry_to_subspace() -> IsometryToSubspaceViaBatching:
    return IsometryToSubspaceViaBatching(
        np.array(
            [
                [0, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 0, 1, 1, 1],
                [1, 0, 0, 1, 0, 1, 0],
                [0, 1, 1, 0, 1, 1, 0],
                [1, 0, 1, 1, 1, 0, 1],
                [1, 0, 0, 1, 1, 1, 1],
                [1, 1, 1, 1, 0, 1, 0],
            ],
            dtype=bool,
        )
    )


@bloq_example()
def _isometry_to_subspace_with_phase() -> IsometryToSubspaceViaBatching:
    return IsometryToSubspaceViaBatching(
        np.array(
            [
                [0, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 0, 1, 1, 1],
                [1, 0, 0, 1, 0, 1, 0],
                [0, 1, 1, 0, 1, 1, 0],
                [1, 0, 1, 1, 1, 0, 1],
                [1, 0, 0, 1, 1, 1, 1],
                [1, 1, 1, 1, 0, 1, 0],
            ],
            dtype=bool,
        ),
        np.array([0, 1, 1, 0, 1, 0, 1], dtype=bool),
    )
