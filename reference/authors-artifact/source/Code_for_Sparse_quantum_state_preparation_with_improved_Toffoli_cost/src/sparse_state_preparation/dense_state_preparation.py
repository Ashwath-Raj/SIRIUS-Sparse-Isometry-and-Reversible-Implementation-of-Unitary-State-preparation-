# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

from functools import cached_property

import numpy as np
from attrs import field, frozen
from qualtran import (
    Bloq,
    BloqBuilder,
    CtrlSpec,
    QDType,
    QFxp,
    QUInt,
    Register,
    Side,
    Signature,
    SoquetT,
    bloq_example,
)
from qualtran.bloqs.arithmetic import XorK
from qualtran.bloqs.basic_gates import Hadamard, SGate, CSwap, OneState, OneEffect
from qualtran.bloqs.bookkeeping import Partition
from qualtran.bloqs.data_loading import QROAMClean
from qualtran.bloqs.rotations import RzViaPhaseGradient
from qualtran.bloqs.swap_network import SwapWithZero

from .uncompute import MeasureInX, SignFixUp
from .utils import random_signs


@frozen
class DenseStatePreparationViaQROAM(Bloq):
    r"""
    Prepare a dense quantum state using a Grover-Rudolph style algorithm.

    The basis construction follows the reference with modifications mainly in the
    way uncomputation is treated.

    As Qualtrans capabilities for processing classical measurement results are just
    starting to grow, the Bloq does not implement the classical logic of calculating
    the sign-flips for the individual basis states caused by X-measuring the target
    registers of QRO(A)Ms. The measurement results are simply discarded.
    See ``tensor_simulation_random`` for how those measurements can be treated in
    simulations.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - state : ``self.state_dtype`` (RIGHT side):
        The output register that will contain the prepared quantum state.

    - phase_gradient : ``self.phase_gradient_dtype``:
        An auxiliary register used to apply rotations.  It is passed through
        unchanged.

    References
    ----------
        Trading T-gates for dirty qubits in state preparation and unitary synthesis
        Low, Kliuchnikov, Schaeffer. 2018.
        (https://arxiv.org/abs/1812.00954).
    """

    coefficients: np.ndarray = field(eq=lambda x: tuple(x))
    """Classical vector (complex/real) containing the target amplitudes."""

    state_dtype: QDType
    """Data type of the output register containing the state."""

    phase_gradient_dtype: QFxp
    """Datatype used for the phase-gradient register determining the accuracy
        of the rotations."""

    prepare_only_amplitudes: bool = False
    """If ``True`` stop after the amplitude-preparation. The phase information
        must then be encoded outside of the bloq. Defaults to ``False``."""

    uncompute: bool = True
    """If ``True`` uncompute the signs introduced by the mesurements used for
        clearing the registers that are targets of QROAM. If ``False`` this must
        be done outside of the bloq.  Defaults to ``True``."""

    max_k: int | None = None
    """Maximum value for k used in QROAM, i.e. use ``b*2**k`` ancilla qubits for
        reducing the Toffoli cost of data loading where ``b`` is the number of bits
        of the phase-gradient register. If ``None`` compute the optimal value.
        If ``0`` use QROM."""

    tensor_simulation_random: bool | None = None
    """If not ``None`` (default) make the Bloq (and sub-Bloqs) suitable for 
        (non-superoperator) tensor simulation. This resplaces the X-measurements by 
        unphysical fake X-measurements that are independent of the state that is measured 
        and avoid classical controlled operations. If ``False`` each X-measurement result 
        is assumed to be deterministically |+>, i.e. no phase flips are applied. If ``True`` 
        with probability 0.5 measure |+> or |->, independet of the actual state. Do not use
        when doing ressource estimates!"""

    @property
    def signature(self) -> Signature:
        """@private"""
        return Signature(
            [
                Register("state", self.state_dtype, side=Side.RIGHT),
                Register("phase_gradient", self.phase_gradient_dtype),
            ]
        )

    def __attrs_post_init__(self):
        assert len(self.coefficients) == 1 << self.state_dtype.num_bits
        assert not (
            self.uncompute and self.prepare_only_amplitudes
        )  # doesn't make sense to do just one
        assert np.isclose(np.linalg.norm(self.coefficients), 1)

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    @cached_property
    def _phase_angles(self):
        with np.errstate(divide="ignore", invalid="ignore"):
            phases = np.where(
                self.coefficients != 0,
                self.coefficients / np.abs(self.coefficients),
                0,
            )  # safe division

        # Get x from a=e^(ix) with x in [0, 2*pi]
        angle_in_0_2pi = (np.angle(phases) + 2 * np.pi) % (2 * np.pi)

        # Transform x/2*pi into binary representation
        angle_as_phase_gradient_integer = np.round(
            (1 << self.phase_gradient_dtype.num_bits) * angle_in_0_2pi / (2 * np.pi)
        ) % (1 << self.phase_gradient_dtype.num_bits)

        return angle_as_phase_gradient_integer.astype(int)

    @cached_property
    def _amplitude_angles(self):
        # Get |a|^2 for all coefficients a.
        coeff_probabilities = np.abs(self.coefficients) ** 2

        coeff_probabilities = np.concatenate(
            (np.zeros(coeff_probabilities.shape), coeff_probabilities)
        )

        # Fill left half with p_y's in eq (9) in the reference.
        for i in range((1 << self.state_dtype.num_bits) - 1, 0, -1):
            coeff_probabilities[i] = (
                coeff_probabilities[i << 1] + coeff_probabilities[(i << 1) | 1]
            )

        angles = coeff_probabilities
        for q in range(self.state_dtype.num_bits):
            for el in range(1 << q, 1 << (q + 1)):
                # Get coefficient from equ. (9) and calculate angle.
                angle = np.arccos(
                    np.sqrt(angles[el << 1] / angles[el] if angles[el] != 0 else 0)
                )
                # Transform it to a value x in [0, 2*pi]
                angle_value_decimal = (
                    (1 << self.phase_gradient_dtype.num_bits) * angle / (2 * np.pi)
                )
                # Transform x/2*pi into binary representation
                angles[el] = round(angle_value_decimal) % (
                    1 << self.phase_gradient_dtype.num_bits
                )

        return angles[: 1 << self.state_dtype.num_bits].astype(int)

    def prepare_amplitudes_bloq(self) -> Bloq:
        """Bloq encoding the amplitudes of the state"""
        angle_bitsize = self.phase_gradient_dtype.num_bits

        bb = BloqBuilder()
        state = bb.add_register_from_dtype("state", self.state_dtype)
        phase_gradient = bb.add_register_from_dtype(
            "phase_gradient", self.phase_gradient_dtype
        )

        # See Figure 8 in our Paper.
        for i in range(self.state_dtype.num_bits):
            if i == 0:
                angles = bb.allocate(dtype=self.phase_gradient_dtype)
                angles = bb.add(
                    XorK(self.phase_gradient_dtype, self._amplitude_angles[1]),
                    x=angles,
                )
            else:
                partition = Partition(
                    n=self.state_dtype.num_bits,
                    regs=(
                        Register("active", QUInt(i)),
                        Register("passive", QUInt(self.state_dtype.num_bits - i)),
                    ),
                )
                active, passive = bb.add(partition, x=state)

                qroam = QROAMCleanExactCSwap.build_from_data(
                    self._amplitude_angles[1 << i : 1 << (i + 1)],
                    target_bitsizes=(angle_bitsize,),
                )

                # Don't let k in QROAM be bigger than max_k
                if self.max_k is not None and qroam.log_block_sizes[0] > self.max_k:
                    qroam = qroam.with_log_block_sizes(self.max_k)

                soqs = bb.add_d(qroam, selection=active)

                active, angles = soqs.pop("selection"), soqs.pop("target0_")

                # Free the junk qubits used in the QROAM. This introduces phase flips.
                if qroam.log_block_sizes[0] > 0:
                    for junk in soqs.pop("junk_target0_"):
                        bb.add(
                            MeasureInX(
                                self.phase_gradient_dtype, self.tensor_simulation_random
                            ),
                            to_measure=junk,
                        )

                state = bb.add(partition.adjoint(), active=active, passive=passive)

            # Ry rotation
            state = bb.split(state)
            state[i] = bb.add(SGate().adjoint(), q=state[i])
            state[i] = bb.add(Hadamard(), q=state[i])

            state[i], angles, phase_gradient = bb.add(
                RzViaPhaseGradient(
                    self.phase_gradient_dtype,
                    self.phase_gradient_dtype,
                ),
                q=state[i],
                angle=angles,
                phase_grad=phase_gradient,
            )
            state[i] = bb.add(Hadamard(), q=state[i])
            state[i] = bb.add(SGate(), q=state[i])

            state = bb.join(state)
            bb.add(
                MeasureInX(self.phase_gradient_dtype, self.tensor_simulation_random),
                to_measure=angles,
            )

        return bb.finalize(state=state, phase_gradient=phase_gradient)

    def prepare_phases_bloq(
        self,
    ) -> Bloq:
        """Bloq encoding the the phase information of the state"""
        angle_bitsize = self.phase_gradient_dtype.num_bits

        bb = BloqBuilder()
        state = bb.add_register_from_dtype("state", self.state_dtype)
        phase_gradient = bb.add_register_from_dtype(
            "phase_gradient", self.phase_gradient_dtype
        )

        if self.state_dtype.num_bits == 1:
            angles = bb.allocate(dtype=self.phase_gradient_dtype)
            state, angles = bb.add(
                XorK(self.phase_gradient_dtype, self._phase_angles[1]).controlled(
                    ctrl_spec=CtrlSpec(cvs=1)
                ),
                ctrl=state,
                x=angles,
            )

            state, angles = bb.add(
                XorK(self.phase_gradient_dtype, self._phase_angles[0]).controlled(
                    ctrl_spec=CtrlSpec(cvs=0)
                ),
                ctrl=state,
                x=angles,
            )
        else:
            qroam = QROAMCleanExactCSwap.build_from_data(
                self._phase_angles,
                target_bitsizes=(angle_bitsize,),
            )
            if self.max_k is not None and qroam.log_block_sizes[0] > self.max_k:
                qroam = qroam.with_log_block_sizes(self.max_k)

            soqs = bb.add_d(qroam, selection=state)

            state, angles = soqs.pop("selection"), soqs.pop("target0_")

            if qroam.log_block_sizes[0] > 0:
                for junk in soqs.pop("junk_target0_"):
                    bb.add(
                        MeasureInX(
                            self.phase_gradient_dtype, self.tensor_simulation_random
                        ),
                        to_measure=junk,
                    )

        anc = bb.add(OneState())
        anc, angles, phase_gradient = bb.add(
            RzViaPhaseGradient(
                self.phase_gradient_dtype,
                self.phase_gradient_dtype,
            ),
            q=anc,
            angle=angles,
            phase_grad=phase_gradient,
        )
        bb.add(OneEffect(), q=anc)

        bb.add(
            MeasureInX(self.phase_gradient_dtype, self.tensor_simulation_random),
            to_measure=angles,
        )

        return bb.finalize(state=state, phase_gradient=phase_gradient)

    @property
    def sign_flips(self) -> tuple[bool, ...]:
        """Get random sign flips, imitating the flips caused by X-measurements."""
        if self.tensor_simulation_random is not None:
            return (0,) * (1 << self.state_dtype.num_bits)
        # TODO: Replace with actual values.
        return tuple(random_signs(1 << self.state_dtype.num_bits, seed=1999999))

    def uncompute_bloq(self) -> SignFixUp:
        """Bloq that uncomputes the sign-flips of the X-Measurements used
        for deleting QRO(A)M target registers."""

        return SignFixUp(
            self.sign_flips,
            self.state_dtype,
            self.max_k,
            tensor_simulation=self.tensor_simulation_random is not None,
        )

    def build_composite_bloq(
        self, bb: BloqBuilder, phase_gradient: SoquetT
    ) -> dict[str, SoquetT]:
        """@private"""

        state = bb.allocate(dtype=self.state_dtype)
        state, phase_gradient = bb.add(
            self.prepare_amplitudes_bloq(), state=state, phase_gradient=phase_gradient
        )

        if not self.prepare_only_amplitudes:
            state, phase_gradient = bb.add(
                self.prepare_phases_bloq(), state=state, phase_gradient=phase_gradient
            )

        if self.uncompute:
            state = bb.add(
                self.uncompute_bloq(),
                address=state,
            )

        return {"state": state, "phase_gradient": phase_gradient}


@frozen
class QROAMCleanExactCSwap(QROAMClean):
    """
    Wrapper around :class:`qualtran.bloqs.data_loading.QROAMClean`
    that replaces the approximate CSwap with the exact version.
    The approximate version introduces a random sign mistake.
    """

    @cached_property
    def swap_with_zero_bloqs(self) -> list[SwapWithZero]:
        return [
            SwapWithZeroExactCSwap(
                self.log_block_sizes,
                target_bitsize=target_bitsize,
                n_target_registers=self.block_sizes,
            )
            for target_bitsize in self.target_bitsizes
        ]


@frozen
class SwapWithZeroExactCSwap(SwapWithZero):
    """
    Wrapper around :class:`qualtran.bloqs.swap_network.SwapWithZero`
    that replaces the approximate CSwap with the exact version.
    The approximate version introduces a random sign mistake.
    """

    @cached_property
    def cswap_n(self) -> CSwap:
        return CSwap(self.target_bitsize)


_state = np.array(
    [
        -0.06983439 + 0.10294799j,
        0.23564679 + 0.26862708j,
        0.44597159 + 0.01439211j,
        -0.03913393 + 0.02271167j,
        -0.05347711 - 0.04959530j,
        0.16747489 + 0.19496189j,
        0.07018624 - 0.05290770j,
        -0.18050612 + 0.29707594j,
        0.01736172 - 0.22782472j,
        0.05347427 + 0.03384025j,
        0.16316080 + 0.18020173j,
        0.09339864 + 0.20001203j,
        -0.24241623 + 0.15270911j,
        -0.00976748 + 0.17939815j,
        -0.00097635 - 0.36802006j,
        -0.01953336 + 0.20379402j,
    ]
)


@bloq_example
def _dense_prep_no_phase() -> DenseStatePreparationViaQROAM:
    return DenseStatePreparationViaQROAM(
        _state, QUInt(4), QFxp(6, 6), prepare_only_amplitudes=True, uncompute=False
    )


@bloq_example
def _dense_prep() -> DenseStatePreparationViaQROAM:
    return DenseStatePreparationViaQROAM(
        _state,
        QUInt(4),
        QFxp(6, 6),
    )
