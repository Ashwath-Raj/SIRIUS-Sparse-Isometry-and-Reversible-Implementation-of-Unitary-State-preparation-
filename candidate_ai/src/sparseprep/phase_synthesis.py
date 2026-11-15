"""Exact gate synthesis for the real-sign phase oracle used after Phase 7.

Logical wire order is big-endian: wire 0 is the most-significant compact-label
bit.  Multi-controlled phase flips are lowered to H/X/Z/CX/Toffoli operations
using a clean-ancilla conjunction ladder.  This module intentionally does not
prepare arbitrary magnitudes; that is Phase 8.2.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Sequence


class PhaseSynthesisError(ValueError):
    """Invalid phase-oracle input or violated circuit invariant."""


@dataclass(frozen=True, slots=True)
class QuantumOperation:
    """Exact logical gate IR used by the Phase-8 statevector verifier.

    ``angle`` is used by RY/PHASE gates (radians); ``phase`` is reserved for
    GLOBAL_PHASE. Wire order is big-endian throughout.
    """

    kind: str
    target: int | None = None
    controls: tuple[int, ...] = ()
    control_values: tuple[int, ...] = ()
    phase: complex = 1 + 0j
    angle: float = 0.0

    def __post_init__(self) -> None:
        valid = {"H", "X", "Z", "RY", "PHASE", "CX", "TOFFOLI", "SWAP", "GLOBAL_PHASE"}
        if self.kind not in valid:
            raise PhaseSynthesisError(f"unsupported operation kind: {self.kind}")
        if self.kind == "GLOBAL_PHASE":
            if self.target is not None or self.controls:
                raise PhaseSynthesisError("GLOBAL_PHASE has no target or controls")
            if abs(abs(self.phase) - 1.0) > 1e-12:
                raise PhaseSynthesisError("global phase must have unit magnitude")
            return
        if (self.target is None or isinstance(self.target, bool)
                or not isinstance(self.target, int) or self.target < 0):
            raise PhaseSynthesisError("operation target must be a non-negative integer")
        if any(isinstance(w, bool) or not isinstance(w, int) or w < 0 for w in self.controls):
            raise PhaseSynthesisError("control wires must be non-negative integers")
        if self.target in self.controls or len(set(self.controls)) != len(self.controls):
            raise PhaseSynthesisError("control and target wires must be distinct")
        if self.kind in {"H", "X", "Z", "RY", "PHASE"} and self.controls:
            raise PhaseSynthesisError(f"{self.kind} cannot have controls")
        if self.kind == "CX" and len(self.controls) != 1:
            raise PhaseSynthesisError("CX requires exactly one control")
        if self.kind == "TOFFOLI" and len(self.controls) != 2:
            raise PhaseSynthesisError("TOFFOLI requires exactly two controls")
        if self.kind == "SWAP" and len(self.controls) != 1:
            raise PhaseSynthesisError("SWAP requires the second wire in controls")
        if self.control_values:
            raise PhaseSynthesisError(f"{self.kind} does not accept control_values in this lowered IR")
        if self.kind in {"RY", "PHASE"}:
            import math
            if isinstance(self.angle, bool) or not isinstance(self.angle, (int, float)) or not math.isfinite(float(self.angle)):
                raise PhaseSynthesisError("rotation/phase angle must be a finite real number")
        elif self.angle != 0.0:
            raise PhaseSynthesisError(f"{self.kind} does not use an angle")


@dataclass(frozen=True, slots=True)
class PhaseOracleResources:
    data_qubits: int
    clean_ancillas: int
    phase_flips: int
    h: int
    x: int
    z: int
    cx: int
    toffoli: int
    global_phase: int
    total_operations: int


@dataclass(frozen=True, slots=True)
class PhaseOracleCircuit:
    """Gate-level real-sign phase oracle on compact labels."""

    data_qubits: int
    clean_ancillas: int
    negative_labels: tuple[int, ...]
    operations: tuple[QuantumOperation, ...]
    resources: PhaseOracleResources

    @property
    def total_qubits(self) -> int:
        return self.data_qubits + self.clean_ancillas

    def apply(self, data_state: Sequence[complex]) -> tuple[complex, ...]:
        """Apply the oracle to a compact-register vector; ancillas start at zero."""
        expected = 1 << self.data_qubits
        if len(data_state) != expected:
            raise PhaseSynthesisError(
                f"data_state must have {expected} amplitudes for {self.data_qubits} qubits"
            )
        full_size = 1 << self.total_qubits
        ancilla_suffix = self.clean_ancillas
        state = [0j] * full_size
        for label, amplitude in enumerate(data_state):
            state[label << ancilla_suffix] = complex(amplitude)
        state = apply_operations(state, self.total_qubits, self.operations)
        # Verify all work ancillas were returned to |0> for every component.
        result = []
        for label in range(expected):
            result.append(state[label << ancilla_suffix])
        leaked = sum(
            abs(amplitude) ** 2
            for index, amplitude in enumerate(state)
            if index & ((1 << ancilla_suffix) - 1)
        )
        if leaked > 1e-20:
            raise PhaseSynthesisError(f"phase oracle left {leaked:.3e} probability in work ancillas")
        return tuple(result)

    def verify(self, *, atol: float = 1e-11) -> None:
        """Exhaustively verify every compact basis label and clean ancillas."""
        dim = 1 << self.data_qubits
        negative = set(self.negative_labels)
        for label in range(dim):
            basis = [0j] * dim
            basis[label] = 1 + 0j
            got = self.apply(basis)
            expected = [0j] * dim
            expected[label] = -1 + 0j if label in negative else 1 + 0j
            if any(abs(a - b) > atol for a, b in zip(got, expected)):
                raise PhaseSynthesisError(
                    f"phase oracle mismatch at label {label}: got {got[label]}, expected {expected[label]}"
                )


def _append_mcx_ladder(
    operations: list[QuantumOperation], controls: tuple[int, ...], target: int,
    ancilla_wires: tuple[int, ...],
) -> None:
    """Append MCX with positive controls and clean ancillas, then uncompute them."""
    count = len(controls)
    if count == 0:
        operations.append(QuantumOperation("X", target=target))
        return
    if count == 1:
        operations.append(QuantumOperation("CX", controls=controls, target=target))
        return
    if count == 2:
        operations.append(QuantumOperation("TOFFOLI", controls=controls, target=target))
        return
    required = count - 2
    if len(ancilla_wires) < required:
        raise PhaseSynthesisError(
            f"MCX with {count} controls requires {required} clean ancillas"
        )
    # Compute prefix conjunctions into a clean v-chain.
    operations.append(QuantumOperation("TOFFOLI", controls=(controls[0], controls[1]), target=ancilla_wires[0]))
    for index in range(2, count - 1):
        operations.append(
            QuantumOperation("TOFFOLI", controls=(ancilla_wires[index - 2], controls[index]), target=ancilla_wires[index - 1])
        )
    operations.append(
        QuantumOperation("TOFFOLI", controls=(ancilla_wires[required - 1], controls[-1]), target=target)
    )
    # Reverse the conjunction chain.  Ancillas are clean again immediately.
    for index in range(count - 2, 1, -1):
        operations.append(
            QuantumOperation("TOFFOLI", controls=(ancilla_wires[index - 2], controls[index]), target=ancilla_wires[index - 1])
        )
    operations.append(QuantumOperation("TOFFOLI", controls=(controls[0], controls[1]), target=ancilla_wires[0]))


def _compile_one_basis_phase_flip(
    label: int, data_qubits: int, ancilla_wires: tuple[int, ...]
) -> tuple[QuantumOperation, ...]:
    """Compile diag(1,...,-1_at_label,...,1) exactly."""
    if data_qubits == 0:
        if label != 0:
            raise PhaseSynthesisError("zero-qubit register has only label 0")
        return (QuantumOperation("GLOBAL_PHASE", phase=-1 + 0j),)

    bits = format(label, f"0{data_qubits}b")
    if data_qubits == 1:
        # Avoid an unnecessary H-X-H decomposition when the entire register
        # is one qubit: Z flips |1>, and X-Z-X flips |0>.
        if bits == "1":
            return (QuantumOperation("Z", target=0),)
        return (
            QuantumOperation("X", target=0),
            QuantumOperation("Z", target=0),
            QuantumOperation("X", target=0),
        )
    operations: list[QuantumOperation] = []
    target = data_qubits - 1
    controls = tuple(range(data_qubits - 1))

    # Conjugate zero-valued controls/target by X to turn the selected pattern
    # into the all-ones pattern.  H-MCX-H is a multi-controlled Z on |1...1>.
    for wire, bit in enumerate(bits[:-1]):
        if bit == "0":
            operations.append(QuantumOperation("X", target=wire))
    target_was_zero = bits[-1] == "0"
    if target_was_zero:
        operations.append(QuantumOperation("X", target=target))

    operations.append(QuantumOperation("H", target=target))
    _append_mcx_ladder(operations, controls, target, ancilla_wires)
    operations.append(QuantumOperation("H", target=target))

    if target_was_zero:
        operations.append(QuantumOperation("X", target=target))
    for wire, bit in reversed(tuple(enumerate(bits[:-1]))):
        if bit == "0":
            operations.append(QuantumOperation("X", target=wire))
    return tuple(operations)


def compile_real_sign_phase_oracle(algorithm3_result) -> PhaseOracleCircuit:
    """Compile Phase-7's ``signs`` onto its unique ``compact_labels``.

    The operation is a diagonal unitary ``P`` satisfying
    ``P|compact_labels[i]> = signs[i] |compact_labels[i]>``.  The input object
    is duck-typed to avoid a module import cycle, but must expose ``ell``,
    ``signs`` and ``compact_labels`` (normally an ``Algorithm3Result``).
    """
    try:
        data_qubits = algorithm3_result.ell
        labels = tuple(algorithm3_result.compact_labels)
        signs = tuple(algorithm3_result.signs)
    except AttributeError as exc:
        raise TypeError("expected an Algorithm3Result-like object with ell, signs, compact_labels") from exc
    if isinstance(data_qubits, bool) or not isinstance(data_qubits, int) or data_qubits < 0:
        raise PhaseSynthesisError("ell must be a non-negative integer")
    if not labels or len(labels) != len(signs):
        raise PhaseSynthesisError("compact_labels and signs must have equal non-zero length")
    if any(type(sign) is not int or sign not in (-1, 1) for sign in signs):
        raise PhaseSynthesisError("signs must contain only exact integer +1/-1 values")
    if len(set(labels)) != len(labels):
        raise PhaseSynthesisError("compact_labels must be pairwise distinct")
    if any(type(label) is not int or not 0 <= label < (1 << data_qubits) for label in labels):
        raise PhaseSynthesisError("compact label outside the declared register range")

    negative_labels = tuple(label for label, sign in zip(labels, signs) if sign == -1)
    mcx_controls = max(0, data_qubits - 1)
    clean_ancillas = max(0, mcx_controls - 2) if negative_labels and data_qubits >= 4 else 0
    ancilla_wires = tuple(range(data_qubits, data_qubits + clean_ancillas))
    operations: list[QuantumOperation] = []
    for label in negative_labels:
        operations.extend(_compile_one_basis_phase_flip(label, data_qubits, ancilla_wires))

    counts = {kind: 0 for kind in ("H", "X", "Z", "CX", "TOFFOLI", "GLOBAL_PHASE")}
    for operation in operations:
        counts[operation.kind] += 1
    resources = PhaseOracleResources(
        data_qubits=data_qubits,
        clean_ancillas=clean_ancillas,
        phase_flips=len(negative_labels),
        h=counts["H"], x=counts["X"], z=counts["Z"],
        cx=counts["CX"], toffoli=counts["TOFFOLI"],
        global_phase=counts["GLOBAL_PHASE"], total_operations=len(operations),
    )
    circuit = PhaseOracleCircuit(
        data_qubits=data_qubits,
        clean_ancillas=clean_ancillas,
        negative_labels=negative_labels,
        operations=tuple(operations),
        resources=resources,
    )
    circuit.verify()
    return circuit


def apply_operations(
    state: Sequence[complex], n_qubits: int, operations: Iterable[QuantumOperation]
) -> tuple[complex, ...]:
    """Apply the exact logical gate IR to a statevector (big-endian wires)."""
    if isinstance(n_qubits, bool) or not isinstance(n_qubits, int) or n_qubits < 0:
        raise PhaseSynthesisError("n_qubits must be a non-negative integer")
    amplitudes = [complex(value) for value in state]
    if len(amplitudes) != (1 << n_qubits):
        raise PhaseSynthesisError(f"statevector length must be 2**{n_qubits}")
    for operation in operations:
        if operation.kind == "GLOBAL_PHASE":
            amplitudes = [operation.phase * amp for amp in amplitudes]
            continue
        assert operation.target is not None
        wires = (operation.target, *operation.controls)
        if any(wire >= n_qubits for wire in wires):
            raise PhaseSynthesisError("operation references a wire outside the statevector")
        target_mask = 1 << (n_qubits - 1 - operation.target)
        control_masks = tuple(1 << (n_qubits - 1 - wire) for wire in operation.controls)
        if operation.kind == "H":
            scale = 1.0 / sqrt(2.0)
            for index in range(len(amplitudes)):
                if not index & target_mask:
                    partner = index | target_mask
                    a, b = amplitudes[index], amplitudes[partner]
                    amplitudes[index] = (a + b) * scale
                    amplitudes[partner] = (a - b) * scale
        elif operation.kind == "X":
            for index in range(len(amplitudes)):
                if not index & target_mask:
                    partner = index | target_mask
                    amplitudes[index], amplitudes[partner] = amplitudes[partner], amplitudes[index]
        elif operation.kind == "Z":
            for index in range(len(amplitudes)):
                if index & target_mask:
                    amplitudes[index] = -amplitudes[index]
        elif operation.kind == "RY":
            from math import cos, sin
            c, ss = cos(operation.angle / 2.0), sin(operation.angle / 2.0)
            for index in range(len(amplitudes)):
                if not index & target_mask:
                    partner = index | target_mask
                    a, b = amplitudes[index], amplitudes[partner]
                    amplitudes[index] = c * a - ss * b
                    amplitudes[partner] = ss * a + c * b
        elif operation.kind == "PHASE":
            import cmath
            factor = cmath.exp(1j * operation.angle)
            for index in range(len(amplitudes)):
                if index & target_mask:
                    amplitudes[index] *= factor
        elif operation.kind in {"CX", "TOFFOLI"}:
            for index in range(len(amplitudes)):
                if not index & target_mask and all(index & mask for mask in control_masks):
                    partner = index | target_mask
                    amplitudes[index], amplitudes[partner] = amplitudes[partner], amplitudes[index]
        elif operation.kind == "SWAP":
            other_mask = control_masks[0]
            for index in range(len(amplitudes)):
                if not index & target_mask and index & other_mask:
                    partner = index ^ target_mask ^ other_mask
                    amplitudes[index], amplitudes[partner] = amplitudes[partner], amplitudes[index]
        else:  # pragma: no cover - guarded by QuantumOperation validation
            raise PhaseSynthesisError(f"unsupported operation {operation.kind}")
    return tuple(amplitudes)


def direct_sign_phase(
    data_state: Sequence[complex], signs_by_label: dict[int, int]
) -> tuple[complex, ...]:
    """Reference diagonal action, independent of the emitted circuit."""
    out = []
    for label, amplitude in enumerate(data_state):
        sign = signs_by_label.get(label, 1)
        if type(sign) is not int or sign not in (-1, 1):
            raise PhaseSynthesisError("reference signs must be exact integers +1/-1")
        out.append(sign * complex(amplitude))
    return tuple(out)
