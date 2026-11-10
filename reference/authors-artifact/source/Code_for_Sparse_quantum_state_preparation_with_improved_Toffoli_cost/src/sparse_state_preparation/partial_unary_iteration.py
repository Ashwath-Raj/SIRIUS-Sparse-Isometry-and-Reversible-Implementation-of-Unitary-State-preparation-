# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

from functools import cached_property

from attrs import frozen
from qualtran import (
    Bloq,
    BloqBuilder,
    QBit,
    QDType,
    Register,
    Signature,
    SoquetT,
    bloq_example,
)
from qualtran.bloqs.basic_gates import CNOT, XGate
from qualtran.bloqs.mcmt import And

import numpy as np


def intersects(interval1: tuple[int, int], interval2: tuple[int, int]) -> bool:
    """
    Checks if `interval1` intersects `interval2`.
    The upper limits of the intervals are excluded.
    """
    assert interval1[0] < interval1[1] and interval2[0] < interval2[1]
    return not ((interval1[1] <= interval2[0]) or (interval2[1] <= interval1[0]))


def half_interval(interval: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Half the `interval` in the middle, returning the left and right half-intervals.
    """
    width_intervals = (interval[1] - interval[0]) // 2
    return (
        interval[0],
        interval[0] + width_intervals,
    ), (interval[0] + width_intervals, interval[1])


@frozen
class PartialUnaryIteration(Bloq):
    r"""
    Partial unary iteration (PUI).

    The Bloq applies a tuple of sub-Bloqs ``bloqs`` to an operation register,
    controlled on the value of an address register only for those address
    values that lie inside a given half-open ``interval`` $[a, b)$.

    The address register is interpreted in big-endian order, i.e. qubit zero is the
    most-significant bit.  The Bloq can be instantiated in two modes:

    Registers
    ----------
    - address : ``address_dtype``

    - operation : see `operation_register`
        The registers required by the sub-Bloqs.  All sub-Bloqs share the same
        signature.

    - control : ``QBit`` (optional)
        Present only when ``control`` is ``True``.
    """

    interval: tuple[int, int]
    """The half-open interval ``[a, b)`` on which the iteration is active."""

    address_dtype: QDType
    """The address register that selects which sub-Bloq to apply."""

    bloqs: tuple[Bloq | None, ...]
    """A tuple of Bloqs (or ``None`` placeholders) of length ``b-a``.  All
    non-``None`` Bloqs must have identical signatures. The i-th
    integer in the interval (counted from ``a``) corresponds to the i-th Bloq in
    ``bloqs`` """

    restricted: bool
    """    * ``True`` - the control logic guarantees that no operation is
    applied to address values right of the interval.
    * ``False`` - the control logic does not forbid application of
    operation for address values on the right side; this version is cheaper but may a
    apply the sub-Bloqs to a superset of the intended addresses."""

    control: bool | None = None
    """If ``True`` a global control qubit named ``control`` is added to the
    signature. If ``None`` (default) no extra control is added."""

    @property
    def operation_registers(self):
        """
        List of registers that constitute the operation register.
        """
        return [bloq for bloq in self.bloqs if bloq][0].signature

    @property
    def signature(self) -> Signature:
        """@private"""
        regs = [
            Register("address", self.address_dtype),
            *self.operation_registers,
        ]
        if self.control:
            regs.append(Register("control", QBit()))
        return Signature(regs)

    def __attrs_post_init__(self):
        assert len(self.bloqs) == (self.interval[1] - self.interval[0])
        assert (
            0
            <= self.interval[0]
            < self.interval[1]
            <= (1 << self.address_dtype.num_bits)
        )
        assert all(bloq.signature == self.bloqs[0].signature for bloq in self.bloqs)

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    @cached_property
    def mapping(self) -> list[list[int]]:
        """
        Compute, for each of the Bloqs, the list of address values for which
        the Bloq is executed.
        """
        return [
            bit_variants(address_value, fixed_indices, self.address_dtype.num_bits)
            for fixed_indices, address_value in zip(
                self._control_indices((0, 1 << self.address_dtype.num_bits), []),
                range(*self.interval),
            )
        ]

    def _control_indices(
        self,
        current_interval: tuple[int, int],
        control_indices: list[int],
        depth=0,
    ) -> list[list[int]]:
        if current_interval[1] - current_interval[0] == 1:
            return [control_indices]

        interval_left, interval_right = half_interval(current_interval)

        match (
            intersects(self.interval, interval_left),
            intersects(self.interval, interval_right),
        ):
            case (True, False):
                if self.restricted:
                    indices = self._control_indices(
                        interval_left, control_indices + [depth], depth + 1
                    )
                else:
                    indices = self._control_indices(
                        interval_left, control_indices, depth + 1
                    )
            case (True, True):
                indices = self._control_indices(
                    interval_left, control_indices + [depth], depth + 1
                ) + self._control_indices(
                    interval_right, control_indices + [depth], depth + 1
                )
            case (False, True):
                indices = self._control_indices(
                    interval_right, control_indices + [depth], depth + 1
                )
            case (False, False):
                raise ValueError("Should intersects at least one interval.")
        return indices

    def _partial_unary_iteration(
        self,
        bb: BloqBuilder,
        current_interval: tuple[int, int],
        address: SoquetT,
        control: None | SoquetT,
        **soqs,
    ) -> tuple[SoquetT, SoquetT, SoquetT]:
        if current_interval[1] - current_interval[0] == 1:
            if bloq := self.bloqs[current_interval[0] - self.interval[0]]:
                if control:
                    soqs = bb.add_d(
                        bloq.controlled(),
                        ctrl=control,
                        **soqs,
                    )
                    control = soqs.pop("ctrl")
                else:
                    soqs = bb.add_d(bloq, **soqs)

            return (
                address,
                control,
                soqs,
            )

        interval_left, interval_right = half_interval(current_interval)
        match (
            intersects(self.interval, interval_left),
            intersects(self.interval, interval_right),
        ):
            case (True, False):
                bb, address, control, soqs = self._left(
                    bb, address, control, interval_left, **soqs
                )
            case (True, True):
                bb, address, control, soqs = self._both(
                    bb, address, control, interval_left, interval_right, **soqs
                )
            case (False, True):
                bb, address, control, soqs = self._right(
                    bb, address, control, interval_right, **soqs
                )
            case (False, False):
                raise ValueError("Should intersects at least one interval.")

        return address, control, soqs

    def _left(
        self,
        bb: BloqBuilder,
        address: SoquetT,
        control: None | SoquetT,
        interval_left: tuple[int, int],
        **soqs,
    ) -> tuple[BloqBuilder, SoquetT, None | SoquetT, dict[str, SoquetT]]:
        if self.restricted:
            if control:
                [control, address[0]], ancilla = bb.add(
                    And(1, 0), ctrl=[control, address[0]]
                )
                address[1:], ancilla, soqs = self._partial_unary_iteration(
                    bb, interval_left, address[1:], ancilla, **soqs
                )
                [control, address[0]] = bb.add(
                    And(1, 0).adjoint(),
                    ctrl=[control, address[0]],
                    target=ancilla,
                )
            else:
                address[0] = bb.add(XGate(), q=address[0])
                address[1:], address[0], soqs = self._partial_unary_iteration(
                    bb, interval_left, address[1:], address[0], **soqs
                )
                address[0] = bb.add(XGate(), q=address[0])
        else:
            # In unrestricted-mode we don't mind if actions on the left
            # branch changes the right branch.
            address[1:], control, soqs = self._partial_unary_iteration(
                bb, interval_left, address[1:], control, **soqs
            )
        return bb, address, control, soqs

    def _both(
        self,
        bb: BloqBuilder,
        address: SoquetT,
        control: None | SoquetT,
        interval_left: tuple[int, int],
        interval_right: tuple[int, int],
        **soqs,
    ) -> tuple[BloqBuilder, SoquetT, None | SoquetT, dict[str, SoquetT]]:
        if control:
            [control, address[0]], ancilla = bb.add(
                And(1, 0), ctrl=[control, address[0]]
            )
            address[1:], ancilla, soqs = self._partial_unary_iteration(
                bb, interval_left, address[1:], ancilla, **soqs
            )
            control, ancilla = bb.add(CNOT(), ctrl=control, target=ancilla)
            address[1:], ancilla, soqs = self._partial_unary_iteration(
                bb, interval_right, address[1:], ancilla, **soqs
            )
            control, ancilla = bb.add(CNOT(), ctrl=control, target=ancilla)
            [control, address[0]] = bb.add(
                And(1, 0).adjoint(),
                ctrl=[control, address[0]],
                target=ancilla,
            )
        else:
            address[0] = bb.add(XGate(), q=address[0])
            address[1:], address[0], soqs = self._partial_unary_iteration(
                bb, interval_left, address[1:], address[0], **soqs
            )
            address[0] = bb.add(XGate().adjoint(), q=address[0])
            address[1:], address[0], soqs = self._partial_unary_iteration(
                bb, interval_right, address[1:], address[0], **soqs
            )
        return bb, address, control, soqs

    def _right(
        self,
        bb: BloqBuilder,
        address: SoquetT,
        control: None | SoquetT,
        interval_right: tuple[int, int],
        **soqs,
    ) -> tuple[BloqBuilder, SoquetT, None | SoquetT, dict[str, SoquetT]]:
        # Left branch has been visited before, must ensure it is turned off.
        if control:
            [control, address[0]], ancilla = bb.add(
                And(1, 1), ctrl=[control, address[0]]
            )
            address[1:], ancilla, soqs = self._partial_unary_iteration(
                bb, interval_right, address[1:], ancilla, **soqs
            )
            [control, address[0]] = bb.add(
                And(1, 1).adjoint(),
                ctrl=[control, address[0]],
                target=ancilla,
            )
        else:
            address[1:], address[0], soqs = self._partial_unary_iteration(
                bb, interval_right, address[1:], address[0], **soqs
            )
        return bb, address, control, soqs

    def build_composite_bloq(
        self, bb: BloqBuilder, address: SoquetT, **soqs
    ) -> dict[str, SoquetT]:
        """@private"""
        control = soqs.pop("control") if self.control else None

        address, control, soqs = self._partial_unary_iteration(
            bb,
            current_interval=(0, 1 << self.address_dtype.num_bits),
            address=bb.split(address),
            control=control,
            **soqs,
        )

        soqs["address"] = bb.join(address, dtype=self.address_dtype)
        if self.control:
            soqs["control"] = control

        return soqs


def bit_variants(val: int, fixed_bits: list[int], length: int) -> list[int]:
    """
    Given a integer value ``val`` fix the bits in its binary representation
    at the positions in ``fixed_bits`` where bit 0 is the most significant bit.
    Then give all posible numbers that can be produced by varying all other bits.
    All binary strings have ``length`` bits.
    """

    val_bits = np.frombuffer(val.to_bytes((length + 7) // 8, "big"), dtype=np.uint8)
    val_bits = np.unpackbits(val_bits)[-length:]  # shape (n,)

    free_bits = np.setdiff1d(np.arange(length), np.array(fixed_bits))

    if len(free_bits) == 0:
        return [val]

    m = len(free_bits)
    combos = np.unpackbits(
        np.arange(1 << m, dtype=np.uint64).view(np.uint8), bitorder="little"
    ).reshape(1 << m, 64)[:, ::-1][:, -m:]  # (2**m, m)

    all_bits = np.broadcast_to(val_bits, (1 << m, length)).copy()
    all_bits[:, free_bits] = combos

    weights = 1 << np.arange(length - 1, -1, -1, dtype=np.uint64)  # 2**(n‑1‑j)
    return all_bits.dot(weights).tolist()


@bloq_example()
def _partial_unary_iteration_restricted() -> PartialUnaryIteration:
    from qualtran import QUInt
    from .isometry import ToggleWithPhase

    return PartialUnaryIteration(
        (7, 15),
        QUInt(4),
        tuple(ToggleWithPhase(16, i, False, False) for i in range(7, 15)),
        restricted=True,
    )


@bloq_example()
def _partial_unary_iteration_unrestricted() -> PartialUnaryIteration:
    from qualtran import QUInt
    from .isometry import ToggleWithPhase

    return PartialUnaryIteration(
        (7, 15),
        QUInt(4),
        tuple(ToggleWithPhase(16, i, False, False) for i in range(7, 15)),
        restricted=False,
    )
