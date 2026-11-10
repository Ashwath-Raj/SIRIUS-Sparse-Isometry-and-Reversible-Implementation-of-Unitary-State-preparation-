# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
from attrs import field, frozen
from qualtran import (
    Bloq,
    BloqBuilder,
    QFxp,
    QUInt,
    Register,
    Side,
    Signature,
    SoquetT,
    bloq_example,
)

from .dense_state_preparation import DenseStatePreparationViaQROAM
from .isometry import (
    IsometryToSubspaceViaBatching,
    data_to_tuple,
)
from .utils import random_signs


@frozen
class SparseStatePreparation(Bloq):
    r"""
    Prepare a $d$-sparse quantum state on $n$ qubits.

    The state is defined by a Boolean matrix ``states`` (shape ``d x n``) and a
    vector of amplitudes ``coefficients`` (length ``d``).  The Bloq first loads
    the amplitudes onto a compact register using a dense-state-preparation
    routine and then maps that register to the full ``n``-qubit space with an
    isometry.

    As Qualtrans capabilities for processing classical measurement results are just
    starting to grow, the Bloq does not implement the classical logic of calculating
    the sign-flips for the individual basis states caused by X-measuring the target
    registers of QRO(A)Ms. The measurement results are simply discarded.
    See ``tensor_simulation`` for how those measurements can be treated in simulations.

    Note that no symbolic version of the bloq is provided as the ressource count
    depends on the concrete input states and may only be upper bounded symbolically.

    Registers
    ----------
    - state : ``QUInt(self.state_bitsize)`` (RIGHT side)
        The output register that holds the prepared ``n``-qubit state.

    - phase_gradient : ``self.phase_gradient_dtype``
        An auxiliary register used by the dense-state-preparation to apply
        rotations.  It is passed through unchanged.
    """

    states: np.ndarray = field(eq=lambda x: data_to_tuple(x))
    """Boolean matrix whose rows are the computational-basis vectors that have
        non-zero amplitude.  Row ``i`` corresponds to the basis state
        ``|states[i]⟩`` (the ``j``-th column is the value of qubit ``j``)."""

    coefficients: np.ndarray = field(eq=lambda x: tuple(x))
    """Amplitudes associated with each row of ``states``.  The Bloq does not
        normalise the vector; the caller must ensure that it is normalized."""

    phase_gradient_dtype: QFxp
    """Datatype used for the phase-gradient register determining the accuracy
        of the rotations within the dense state preparation step."""

    max_k: int | None = None
    """Maximum value for k used in QROAM, i.e. use ``b*2k`` ancilla qubits for
        reducing the cost of data loading where ``b`` is the number of bits of the
        phase-gradient register. If ``None`` compute the optimal value.
        If ``0`` use QROM."""

    uncompute_in_isometry: bool = False
    """If ``True`` the uncomputation of the QROAM used in the dense state
        preparation step is done within the isometry step. Defaults to ``False``."""

    add_real_phase_in_isometry: bool = False
    """When ``True`` the phase information of the dense state is encoded within
        the isometryinstead of the dense-preparation step. This flag can only be
        used when the coefficients are real as then the phases are just signs."""

    tensor_simulation: bool = False
    """If ``True`` make the Bloq (and sub-Bloqs) suitable for (non-superoperator) tensor 
        simulation. This replaces the X-measurements by unphysical fake X-measurements 
        with deterministic result |+> that are independent of the state that is measured 
        and avoid classical controlled operations. Defaults to ``False``. Do not use
        when doing ressource estimates!"""

    @property
    def signature(self) -> Signature:
        """@private"""
        return Signature(
            [
                Register("state", QUInt(self.state_bitsize), side=Side.RIGHT),
                Register("phase_gradient", self.phase_gradient_dtype),
            ]
        )

    def __attrs_post_init__(self):
        assert len(self.coefficients) == self.states.shape[0]
        if self.add_real_phase_in_isometry:
            assert self.is_real and self.uncompute_in_isometry

    @property
    def is_real(self) -> bool:
        """Shows wheter all coefficients are real or not."""
        return np.isrealobj(self.coefficients)

    @property
    def state_bitsize(self) -> int:
        """Width of the full state"""
        return self.states.shape[1]

    @property
    def subspace_bitsize(self) -> int:
        """Width of the subspace"""
        return self.isometry.subspace_bitsize

    @property
    def is_symbolic(self) -> bool:
        """@private"""
        return False

    @property
    def isometry(self) -> IsometryToSubspaceViaBatching:
        """Isometry circuit mapping from the subspace to the full space."""

        signs_phase = self.coefficients < 0 if self.add_real_phase_in_isometry else None
        if self.uncompute_in_isometry:
            signs_meas = (
                np.zeros((self.states.shape[0],), dtype=bool)
                if self.tensor_simulation
                else random_signs(self.states.shape[0], seed=1999999)
            )
        else:
            signs_meas = None

        if signs_phase is not None and signs_meas is not None:
            signs = np.logical_xor(signs_meas, signs_phase)
        elif signs_phase is not None:
            signs = signs_phase
        else:
            signs = signs_meas
        return IsometryToSubspaceViaBatching(self.states, signs)

    @property
    def _permuted_coefficients(self) -> np.ndarray:
        coefficients = np.zeros(
            shape=(1 << self.subspace_bitsize), dtype=self.coefficients.dtype
        )
        coefficients[self.isometry.bijection[:, 0]] = self.coefficients[
            self.isometry.bijection[:, 1]
        ]
        return coefficients

    @property
    def dense_state_prep(self) -> DenseStatePreparationViaQROAM:
        """Circuit preparing the dense state in the subspace."""
        return DenseStatePreparationViaQROAM(
            coefficients=self._permuted_coefficients,
            state_dtype=QUInt(self.subspace_bitsize),
            phase_gradient_dtype=self.phase_gradient_dtype,
            prepare_only_amplitudes=self.add_real_phase_in_isometry,
            uncompute=not self.uncompute_in_isometry,
            max_k=self.max_k,
            tensor_simulation_random=False if self.tensor_simulation else None,
        )

    def build_composite_bloq(
        self, bb: BloqBuilder, phase_gradient: SoquetT
    ) -> dict[str, SoquetT]:
        """@private"""
        subspace, phase_gradient = bb.add(
            self.dense_state_prep,
            phase_gradient=phase_gradient,
        )
        state = bb.add(self.isometry.adjoint(), subspace=subspace)

        return {"state": state, "phase_gradient": phase_gradient}


_coeffs = np.array(
    [
        0.02971151 + 0.0j,
        -0.06864128 + 0.02082211j,
        -0.03502327 + 0.11545623j,
        0.17448621 + 0.14319713j,
        -0.06298578 - 0.06298578j,
        0.248791 - 0.37234205j,
        -0.10245455 + 0.33774739j,
        0.28825977 - 0.02839111j,
        -0.12789431 - 0.42161103j,
        -0.25306989 - 0.47346045j,
        0.05932731 + 0.04868866j,
        0.08121976 - 0.08121976j,
        0.08871471 + 0.047419j,
    ]
)

_states = np.array(
    [
        [True, True, False, False, True, True, False],
        [False, True, True, False, True, True, True],
        [True, False, False, True, False, True, False],
        [False, True, True, False, True, False, True],
        [False, False, True, True, True, True, False],
        [False, False, False, True, True, True, False],
        [False, True, False, False, False, True, False],
        [False, True, True, True, True, False, False],
        [True, False, False, False, True, True, False],
        [True, True, False, True, True, True, True],
        [False, True, True, True, True, True, False],
        [True, True, True, False, False, False, False],
        [True, True, True, False, True, True, False],
    ]
)


@bloq_example()
def _sparse_state_preparation_real() -> SparseStatePreparation:
    return SparseStatePreparation(
        _states,
        np.abs(_coeffs).astype(np.float64),
        phase_gradient_dtype=QFxp(6, 6),
        uncompute_in_isometry=True,
        add_real_phase_in_isometry=True,
    )


@bloq_example()
def _sparse_state_preparation_complex() -> SparseStatePreparation:
    return SparseStatePreparation(
        _states,
        _coeffs,
        phase_gradient_dtype=QFxp(6, 6),
    )
