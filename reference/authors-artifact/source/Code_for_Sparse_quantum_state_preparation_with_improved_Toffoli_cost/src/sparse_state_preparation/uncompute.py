# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np
import quimb.tensor as qtn
from attrs import frozen
from qualtran import (
    Bloq,
    BloqBuilder,
    CBit,
    ConnectionT,
    CtrlSpec,
    QBit,
    QDType,
    QUInt,
    Register,
    Side,
    Signature,
    SoquetT,
    bloq_example,
)
from qualtran.bloqs.basic_gates import (
    CNOT,
    CZ,
    Discard,
    Hadamard,
    MeasureX,
    TwoBitCSwap,
    XGate,
    ZGate,
    ZeroEffect,
    OneEffect,
    OneState,
)
from qualtran.bloqs.bookkeeping import Partition
from qualtran.bloqs.data_loading import QROM


@frozen
class FakeMeas(Bloq):
    r"""
    Fake measurement bloq used for tensor simulations.

    Unphysical fake X-measurement that is independent of the state.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - q : ``QBit``
        Qubit to measure.
    """

    random: bool = False
    """If ``False``, each X-measurement result is assumed
        to be deterministically ``|+>``.
        If ``True`` randomly measure ``|+>`` or ``|->``,
        each result occuring with probability ``0.5`` independent
        of the actual state. At the end it is assumend that
        the qubit it ``|+>``, e.g. by classicaly controlled operation."""

    @property
    def signature(self) -> Signature:
        return Signature(
            [
                Register("q", QBit()),
            ]
        )

    def my_tensors(
        self, incoming: dict[str, ConnectionT], outgoing: dict[str, ConnectionT]
    ) -> list[qtn.Tensor]:
        # Define fake measurement operator: measurement + classical controlled
        # operation resulting in |0> potentially with a sign.
        if self.random:
            sign = np.random.choice([1, -1])
            fake_meas = np.array([[1, sign], [0, 0]], dtype=np.complex128)
        else:
            fake_meas = np.array([[1, 1], [0, 0]], dtype=np.complex128)

        return [
            qtn.Tensor(
                data=fake_meas,
                inds=[(outgoing["q"], 0), (incoming["q"], 0)],
                tags=[str(self)],
            )
        ]


@frozen
class MeasureInX(Bloq):
    r"""
    X-basis measurement of a register.

    The classical measurement result is discarded.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - to_measure : ``self.qdtype`` (LEFT side)
        The register that is measured.
    """

    qdtype: QDType
    """Data type of the register that will be measured."""

    fake_random: None | bool = None
    """If ``None`` (default) a real X-basis measurement is performed using
        :class:`qualtran.bloqs.basic_gates.MeasureX`.  If a boolean is supplied
        the measurement is replaced by a fake measurement:
        If ``False``, each X-measurement result is assumed
        to be deterministically ``|+>``.
        If ``True`` randomly measure ``|+>`` or ``|->``,
        each result occuring with probability ``0.5`` independent
        of the actual state. At the end the qubit is discarded."""

    @property
    def is_symbolic(self) -> bool:
        return False

    @property
    def signature(self) -> Signature:
        return Signature(
            [
                Register("to_measure", self.qdtype, side=Side.LEFT),
            ]
        )

    def build_composite_bloq(
        self, bb: BloqBuilder, to_measure: SoquetT
    ) -> dict[str, SoquetT]:
        for q in bb.split(to_measure):
            if self.fake_random is not None:
                q = bb.add(FakeMeas(self.fake_random), q=q)
                q = bb.add(ZeroEffect(), q=q)
            else:
                meas_result = bb.add(MeasureX(), q=q)
                bb.add(Discard(), c=meas_result)
                # We discard the measurement value for now.
                # Later use it to apply correct SignFixUp
        return {}


@frozen
class SignFixUp(Bloq):
    r"""
    Given a Boolean vector ``signs`` of length ``2^n`` (where ``n`` is the number of
    bits of ``address_dtype``) the Bloq applies sign flips for for all states ``|i>``
    in the address registre for which ``signs[i]`` is ``True``.

    This is done with the circuits from the reference.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - address : ``self.address_dtype``
        Register that holds the computational basis states.

    References
    ----------
        Qubitization of Arbitrary Basis Quantum Chemistry Leveraging Sparsity and Low Rank Factorization
        Berry, Gidney, Motta, McClean, Babbush. 2019.
        https://arxiv.org/abs/1902.02134
    """

    signs: tuple[bool, ...]
    """Boolean vector of length ``2^n`` indicating which computational basis
        states need a sign-flip."""

    address_dtype: QUInt
    """Data type of the address register in which the basis states live."""

    max_k: int | None = None
    """Maximum value for k used in the QROAM-like construction for used for
        the phase fix, i.e. use ``2**k`` ancilla qubits for reducing the Toffoli
        cost of the fix. If ``None`` compute the optimal value. If ``0`` use the
        QROM variant in the reference for uncomputation."""

    tensor_simulation: bool = False
    """Replace the optimized, measurement-based bloq :class:`BinToUnaryAdjoint` 
        to the automatic automatic adjoint of :class:`BinToUnary` in order to 
        allow (non-superoperator) tensor simulation. Defaults to ``False``. Do
        not use when doing ressource estimates!"""

    def __attrs_post_init__(self):
        assert 1 << self.address_dtype.num_bits == len(self.signs)

    @property
    def is_symbolic(self) -> bool:
        return False

    @property
    def signature(self) -> Signature:
        return Signature(
            [
                Register("address", self.address_dtype),
            ]
        )

    @property
    def k(self) -> int:
        optimal_k = self.address_dtype.num_bits // 2
        return min(optimal_k, self.max_k) if self.max_k is not None else optimal_k

    @property
    def fixup_table(self) -> np.ndarray:
        if self.k == 0:  # eq. 68 in reference
            pairs = np.array(self.signs).reshape(-1, 2)
            return (pairs[:, 0].astype(np.uint8) << 1) | pairs[:, 1].astype(np.uint8)
        else:
            return np.array(
                [
                    np.array(self.signs[j :: 1 << self.k]).astype(np.uint8)
                    for j in range(1 << (self.k))
                ]
            )

    def _single_address_qubit(
        self, bb: BloqBuilder, address: SoquetT
    ) -> dict[str, SoquetT]:
        # Only have a single address qubit.
        anc = bb.add(OneState())

        if self.signs == (True, True):
            anc = bb.add(ZGate(), q=anc)
        elif self.signs == (True, False):
            address = bb.add(XGate(), q=address)
            address, anc = bb.add(CZ(), q1=address, q2=anc)
            address = bb.add(XGate(), q=address)
        elif self.signs == (False, True):
            address, anc = bb.add(CZ(), q1=address, q2=anc)

        bb.add(OneEffect(), q=anc)

        return {"address": address}

    def _uncompute_with_qrom(
        self, bb: BloqBuilder, address: SoquetT
    ) -> dict[str, SoquetT]:
        # Figure 5 in reference.
        partition = Partition(
            self.address_dtype.num_bits,
            regs=(
                Register("selection", QUInt(self.address_dtype.num_bits - 1)),
                Register("q", QBit()),
            ),
        )
        selection, q = bb.add(partition, x=address)
        u = bb.add(OneState())
        q, u = bb.add(CNOT(), ctrl=q, target=u)
        q = bb.add(Hadamard(), q=q)
        u = bb.add(Hadamard(), q=u)

        par = Partition(2, [Register("u", QBit()), Register("q", QBit())])
        target = bb.add(par.adjoint(), u=u, q=q)
        selection, target = bb.add(
            QROM.build_from_data(self.fixup_table, target_bitsizes=(2,)),
            selection=selection,
            target0_=target,
        )

        u, q = bb.add(par, x=target)
        u = bb.add(Hadamard(), q=u)
        q = bb.add(Hadamard(), q=q)
        q, u = bb.add(CNOT(), ctrl=q, target=u)
        bb.add(OneEffect(), q=u)
        address = bb.add(partition.adjoint(), selection=selection, q=q)

        return {"address": address}

    def _uncompute_with_qroam(
        self, bb: BloqBuilder, address: SoquetT
    ) -> dict[str, SoquetT]:
        # Figure 6 in reference.
        num_high_qubits = self.address_dtype.num_bits - self.k

        partition = Partition(
            self.address_dtype.num_bits,
            regs=(
                Register("h", QUInt(num_high_qubits)),
                Register("l", QUInt(self.k)),
            ),
        )
        h, l = bb.add(partition, x=address)

        l, r = bb.add(
            BinToUnary(QUInt(self.k)),
            address=l,
        )
        r = bb.split(r)
        for i in range(1 << self.k):
            r[i] = bb.add(Hadamard(), q=r[i])

        soqs = bb.add_d(
            QROM(
                self.fixup_table,
                selection_bitsizes=(num_high_qubits,),
                target_bitsizes=(1,) * (1 << self.k),
            ),
            selection=h,
            **{f"target{i}_": r[i] for i in range(1 << self.k)},
        )
        h = soqs.pop("selection")
        r = np.array([soqs.pop(f"target{i}_") for i in range(1 << self.k)])

        for i in range(1 << self.k):
            r[i] = bb.add(Hadamard(), q=r[i])
        r = bb.join(r)

        l = bb.add(
            BinToUnaryAdjoint(QUInt(self.k))
            if not self.tensor_simulation
            else BinToUnary(QUInt(self.k)).adjoint(),
            address=l,
            target=r,
        )

        address = bb.add(partition.adjoint(), h=h, l=l)

        return {"address": address}

    def build_composite_bloq(
        self, bb: BloqBuilder, address: SoquetT
    ) -> dict[str, SoquetT]:
        if self.address_dtype.num_bits == 1:
            return self._single_address_qubit(bb, address)

        if self.k == 0:
            return self._uncompute_with_qrom(bb, address)
        else:
            return self._uncompute_with_qroam(bb, address)


@frozen
class BinToUnary(Bloq):
    r"""
    Circuit mapping a binary register to a one-hot unary register, i.e. a state ``|i>`` from the address register
    gets mapped to ``|i>|e_i>`` where ``|e_i>`` is the computational basis state with ``|1>`` at the ``i``-th qubit.

    This is done with the circuits from the reference.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - address : ``self.address_dtype``

    - target : ``QUInt(2**self.address_dtype.num_bits)`` (RIGHT side)
        Output unary register that will contain the one-hot encoding after the Bloq.

    References
    ----------
        Qubitization of Arbitrary Basis Quantum Chemistry Leveraging Sparsity and Low Rank Factorization
        Berry, Gidney, Motta, McClean, Babbush. 2019.
        https://arxiv.org/abs/1902.02134
    """

    address_dtype: QUInt
    """Binary data type of the address register."""

    @property
    def is_symbolic(self) -> bool:
        return False

    @property
    def target_dtype(self) -> QUInt:
        return QUInt(1 << self.address_dtype.num_bits)

    @property
    def signature(self) -> Signature:
        return Signature(
            [
                Register("address", self.address_dtype),
                Register("target", self.target_dtype, side=Side.RIGHT),
            ]
        )

    def build_composite_bloq(
        self, bb: BloqBuilder, address: SoquetT
    ) -> dict[str, SoquetT]:
        # Figure 8 in reference.
        address = bb.split(address)[::-1]
        target = bb.split(bb.allocate(dtype=self.target_dtype))
        target[0] = bb.add(XGate(), q=target[0])
        for i in range(self.address_dtype.num_bits):
            for j in range(1 << i):
                address[i], target[j], target[j + (1 << i)] = bb.add(
                    TwoBitCSwap(), ctrl=address[i], x=target[j], y=target[j + (1 << i)]
                )

        return {
            "address": bb.join(address[::-1], dtype=self.address_dtype),
            "target": bb.join(target, dtype=self.target_dtype),
        }


@frozen
class BinToUnaryAdjoint(Bloq):
    r"""
    Adjoint (inverse) of :class:`BinToUnary` using measurement based uncomputation using
    the circuit from the reference.

    At the moment the Bloq is not symbolic.

    Registers
    ----------
    - address : ``self.address_dtype``

    - target : ``QUInt(2**self.address_dtype.num_bits)`` (LEFT side)
        Unary register containing the one-hot encoding.

    References
    ----------
        Qubitization of Arbitrary Basis Quantum Chemistry Leveraging Sparsity and Low Rank Factorization
        Berry, Gidney, Motta, McClean, Babbush. 2019.
        https://arxiv.org/abs/1902.02134
    """

    address_dtype: QUInt
    """Binary data type of the address register."""

    @property
    def is_symbolic(self) -> bool:
        return False

    @property
    def target_dtype(self) -> QUInt:
        return QUInt(1 << self.address_dtype.num_bits)

    @property
    def signature(self) -> Signature:
        return Signature(
            [
                Register("address", self.address_dtype),
                Register("target", self.target_dtype, side=Side.LEFT),
            ]
        )

    def adjoint(self) -> BinToUnary:
        return BinToUnary(self.address_dtype)

    def build_call_graph(self, ssa):
        # Hack to not get the error: C[CZ] does not declare a decomposition.
        # during ressource estimates
        # We are only interested in Toffolis and therefore return an empty dictionary.
        # TODO: Remove this once this is fixed in qualtran.
        return {}

    def build_composite_bloq(
        self, bb: BloqBuilder, address: SoquetT, target: SoquetT
    ) -> dict[str, SoquetT]:
        # Figure 10 in reference.

        target = bb.split(target)
        address = bb.split(address)[::-1]
        for i in reversed(range(self.address_dtype.num_bits)):
            for j in range(1 << i):
                target[j + (1 << i)], target[j] = bb.add(
                    CNOT(), ctrl=target[j + (1 << i)], target=target[j]
                )
                c = bb.add(MeasureX(), q=target[j + (1 << i)])
                c, address[i], target[j] = bb.add(
                    CZ().controlled(ctrl_spec=CtrlSpec(qdtypes=[CBit()])),
                    ctrl=c,
                    q1=address[i],
                    q2=target[j],
                )
                bb.add(Discard(), c=c)
        bb.add(OneEffect(), q=target[0])

        return {"address": bb.join(address[::-1], dtype=self.address_dtype)}


@bloq_example
def _binary_to_unary() -> BinToUnary:
    return BinToUnary(QUInt(5))


@bloq_example
def _binary_to_unary_adj() -> BinToUnaryAdjoint:
    return BinToUnaryAdjoint(QUInt(5))


@bloq_example
def _sign_fixup_0() -> SignFixUp:
    return SignFixUp((True, False, False, True), QUInt(2), max_k=0)


_signs = (
    True,
    False,
    False,
    True,
    True,
    False,
    False,
    True,
    True,
    False,
    False,
    True,
    True,
    False,
    False,
    True,
)


@bloq_example
def _sign_fixup_none() -> SignFixUp:
    return SignFixUp(
        _signs,
        QUInt(4),
    )


@bloq_example
def _sign_fixup_3() -> SignFixUp:
    return SignFixUp(
        _signs,
        QUInt(4),
        max_k=3,
    )
