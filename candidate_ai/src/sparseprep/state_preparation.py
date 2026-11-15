"""End-to-end sparse quantum-state preparation (Phase 8.2).

The module composes four exact stages:

1. prepare |c_i| on Algorithm-3 compact labels with a recursive controlled-RY tree;
2. encode coefficient arguments with basis-selective controlled-phase blocks;
3. apply the Phase-8.1 real-sign oracle for independent +/- metadata;
4. apply the inverse Phase-7 Algorithm-3 isometry and clear its marker.

The emitted circuit uses logical H/X/Z/RY/PHASE/CX/Toffoli/SWAP gates. It is
an exact logical reference circuit; physical backend transpilation and hardware
benchmarking are intentionally Phase 9 work.
"""
from __future__ import annotations

from dataclasses import dataclass
import cmath
import math
from typing import Iterable, Sequence

from .algorithm3 import Algorithm3Result, run_algorithm3
from .gates import CMX, CX, MCX, NegativeControlToffoli, SWAP, Toffoli, X
from .model import SparseStateProblem
from .phase_synthesis import (
    PhaseOracleCircuit,
    QuantumOperation,
    compile_real_sign_phase_oracle,
    apply_operations,
)


class StatePreparationError(ValueError):
    """Invalid sparse-state target or violated end-to-end circuit invariant."""


@dataclass(frozen=True, slots=True)
class StageCounts:
    operations: int
    h: int = 0
    x: int = 0
    z: int = 0
    ry: int = 0
    phase: int = 0
    cx: int = 0
    toffoli: int = 0
    swap: int = 0
    global_phase: int = 0


def _counts(operations: Sequence[QuantumOperation]) -> StageCounts:
    values = {name: 0 for name in ("H", "X", "Z", "RY", "PHASE", "CX", "TOFFOLI", "SWAP", "GLOBAL_PHASE")}
    for operation in operations:
        values[operation.kind] += 1
    return StageCounts(
        operations=len(operations), h=values["H"], x=values["X"], z=values["Z"],
        ry=values["RY"], phase=values["PHASE"], cx=values["CX"],
        toffoli=values["TOFFOLI"], swap=values["SWAP"],
        global_phase=values["GLOBAL_PHASE"],
    )


def _and_compute(
    operations: list[QuantumOperation], controls: tuple[int, ...], ancillas: tuple[int, ...]
) -> tuple[int, tuple[tuple[int, int, int], ...]]:
    """Compute the conjunction of >=2 controls into clean ancillas."""
    if len(controls) < 2:
        raise StatePreparationError("AND ladder requires at least two controls")
    required = len(controls) - 1
    if len(ancillas) < required:
        raise StatePreparationError(
            f"{len(controls)} controls require {required} clean ancillas; got {len(ancillas)}"
        )
    records: list[tuple[int, int, int]] = []
    operations.append(QuantumOperation("TOFFOLI", target=ancillas[0], controls=(controls[0], controls[1])))
    records.append((controls[0], controls[1], ancillas[0]))
    for index in range(2, len(controls)):
        previous = ancillas[index - 2]
        target = ancillas[index - 1]
        operations.append(QuantumOperation("TOFFOLI", target=target, controls=(previous, controls[index])))
        records.append((previous, controls[index], target))
    return ancillas[required - 1], tuple(records)


def _and_uncompute(
    operations: list[QuantumOperation], records: tuple[tuple[int, int, int], ...]
) -> None:
    for control_a, control_b, target in reversed(records):
        operations.append(QuantumOperation("TOFFOLI", target=target, controls=(control_a, control_b)))


def _append_controlled_ry(
    operations: list[QuantumOperation], *, target: int, controls: tuple[int, ...],
    control_values: tuple[int, ...], angle: float, ancillas: tuple[int, ...],
) -> None:
    """Compile a pattern-controlled RY using a clean conjunction ladder.

    A one-control RY is decomposed as RY(theta/2)-CX-RY(-theta/2)-CX.
    For two or more controls, a reversible AND ladder provides that single
    control and is uncomputed immediately afterwards.
    """
    if not controls:
        operations.append(QuantumOperation("RY", target=target, angle=angle))
        return
    if len(control_values) != len(controls):
        raise StatePreparationError("controlled-RY control pattern has the wrong width")
    for wire, value in zip(controls, control_values):
        if value == 0:
            operations.append(QuantumOperation("X", target=wire))
    records: tuple[tuple[int, int, int], ...] = ()
    if len(controls) == 1:
        control = controls[0]
    else:
        control, records = _and_compute(operations, controls, ancillas)
    operations.extend((
        QuantumOperation("RY", target=target, angle=angle / 2.0),
        QuantumOperation("CX", target=target, controls=(control,)),
        QuantumOperation("RY", target=target, angle=-angle / 2.0),
        QuantumOperation("CX", target=target, controls=(control,)),
    ))
    _and_uncompute(operations, records)
    for wire, value in reversed(tuple(zip(controls, control_values))):
        if value == 0:
            operations.append(QuantumOperation("X", target=wire))


def _append_controlled_phase(
    operations: list[QuantumOperation], *, target: int, target_value: int,
    controls: tuple[int, ...], control_values: tuple[int, ...],
    angle: float, ancillas: tuple[int, ...],
) -> None:
    """Apply exp(i*angle) only to one selected computational-basis pattern."""
    if not controls:
        if target_value == 0:
            operations.append(QuantumOperation("X", target=target))
        operations.append(QuantumOperation("PHASE", target=target, angle=angle))
        if target_value == 0:
            operations.append(QuantumOperation("X", target=target))
        return
    if len(control_values) != len(controls):
        raise StatePreparationError("controlled-phase control pattern has the wrong width")
    for wire, value in zip(controls, control_values):
        if value == 0:
            operations.append(QuantumOperation("X", target=wire))
    if target_value == 0:
        operations.append(QuantumOperation("X", target=target))
    records: tuple[tuple[int, int, int], ...] = ()
    if len(controls) == 1:
        control = controls[0]
    else:
        control, records = _and_compute(operations, controls, ancillas)
    # Exact decomposition of controlled-P(angle):
    # P_c(a/2) P_t(a/2) CX P_t(-a/2) CX.
    operations.extend((
        QuantumOperation("PHASE", target=control, angle=angle / 2.0),
        QuantumOperation("PHASE", target=target, angle=angle / 2.0),
        QuantumOperation("CX", target=target, controls=(control,)),
        QuantumOperation("PHASE", target=target, angle=-angle / 2.0),
        QuantumOperation("CX", target=target, controls=(control,)),
    ))
    _and_uncompute(operations, records)
    if target_value == 0:
        operations.append(QuantumOperation("X", target=target))
    for wire, value in reversed(tuple(zip(controls, control_values))):
        if value == 0:
            operations.append(QuantumOperation("X", target=wire))


def compile_dense_compact_preparation(
    coefficients: Sequence[complex], compact_labels: Sequence[int], *,
    data_qubits: int, work_ancillas: Sequence[int] = (),
) -> tuple[QuantumOperation, ...]:
    """Compile normalized complex coefficients onto arbitrary compact labels.

    Magnitudes are prepared by a recursive conditional-RY tree. Each prefix
    rotation splits the norm of its subtree between the next bit's 0 and 1
    branches. Coefficient arguments are then applied with basis-selective
    diagonal phase blocks. All conjunction ancillas are clean on return.
    """
    if isinstance(data_qubits, bool) or not isinstance(data_qubits, int) or data_qubits < 0:
        raise StatePreparationError("data_qubits must be a non-negative integer")
    coeffs = tuple(complex(value) for value in coefficients)
    labels = tuple(compact_labels)
    if not coeffs or len(coeffs) != len(labels):
        raise StatePreparationError("coefficients and compact_labels must have equal non-zero length")
    if len(set(labels)) != len(labels):
        raise StatePreparationError("compact labels must be distinct")
    dimension = 1 << data_qubits
    if any(type(label) is not int or not 0 <= label < dimension for label in labels):
        raise StatePreparationError("compact label outside data-register range")
    if not all(math.isfinite(value.real) and math.isfinite(value.imag) for value in coeffs):
        raise StatePreparationError("coefficients must be finite")
    norm_sq = sum(abs(value) ** 2 for value in coeffs)
    if not math.isclose(norm_sq, 1.0, rel_tol=1e-10, abs_tol=1e-12):
        raise StatePreparationError(f"coefficients must be normalized; squared norm is {norm_sq:.16g}")
    ancillas = tuple(work_ancillas)
    if len(set(ancillas)) != len(ancillas) or any(type(w) is not int or w < data_qubits for w in ancillas):
        raise StatePreparationError("work ancillas must be distinct wires after the compact register")
    amplitudes = [0j] * dimension
    for label, value in zip(labels, coeffs):
        amplitudes[label] = value
    magnitudes_sq = [abs(value) ** 2 for value in amplitudes]
    operations: list[QuantumOperation] = []

    # Build every subtree norm once, bottom-up. This is O(2**ell), rather than
    # rescanning every suffix for every prefix at every level.
    subtree_norm_sq: list[list[float]] = [ [] for _ in range(data_qubits + 1) ]
    subtree_norm_sq[data_qubits] = magnitudes_sq
    for depth in range(data_qubits - 1, -1, -1):
        children = subtree_norm_sq[depth + 1]
        subtree_norm_sq[depth] = [
            children[2 * prefix] + children[2 * prefix + 1]
            for prefix in range(1 << depth)
        ]

    # The amplitude already on a prefix is the norm of its entire subtree. A
    # conditional RY splits that norm into the two child norms exactly.
    for depth in range(data_qubits):
        children = subtree_norm_sq[depth + 1]
        for prefix in range(1 << depth):
            left_norm = math.sqrt(children[2 * prefix])
            right_norm = math.sqrt(children[2 * prefix + 1])
            if left_norm + right_norm <= 1e-15:
                continue
            angle = 2.0 * math.atan2(right_norm, left_norm)
            if abs(angle) <= 1e-15:
                continue
            controls = tuple(range(depth))
            values = tuple(int(bit) for bit in format(prefix, f"0{depth}b")) if depth else ()
            _append_controlled_ry(
                operations, target=depth, controls=controls, control_values=values,
                angle=angle, ancillas=ancillas,
            )

    # Apply each nonzero coefficient's argument at its assigned compact label.
    # The argument of the first coefficient is retained (not discarded as a
    # physically irrelevant global phase) so exact statevector comparisons work.
    if data_qubits == 0:
        operations.append(QuantumOperation("GLOBAL_PHASE", phase=coeffs[0] / abs(coeffs[0])))
    else:
        target = data_qubits - 1
        controls = tuple(range(data_qubits - 1))
        for label, value in zip(labels, coeffs):
            if abs(value) <= 1e-15:
                continue
            angle = cmath.phase(value)
            if abs(angle) <= 1e-15:
                continue
            bits = format(label, f"0{data_qubits}b")
            values = tuple(int(bit) for bit in bits[:-1])
            _append_controlled_phase(
                operations, target=target, target_value=int(bits[-1]),
                controls=controls, control_values=values, angle=angle,
                ancillas=ancillas,
            )
    return tuple(operations)


def _map_phase_ancillas(
    operations: Sequence[QuantumOperation], *, data_qubits: int,
    phase_ancillas: tuple[int, ...],
) -> tuple[QuantumOperation, ...]:
    mapped: list[QuantumOperation] = []
    for op in operations:
        def wire(value: int) -> int:
            if value < data_qubits:
                return value
            offset = value - data_qubits
            if offset >= len(phase_ancillas):
                raise StatePreparationError("phase oracle references an unallocated work ancilla")
            return phase_ancillas[offset]
        target = None if op.target is None else wire(op.target)
        controls = tuple(wire(control) for control in op.controls)
        mapped.append(QuantumOperation(
            op.kind, target=target, controls=controls,
            control_values=op.control_values, phase=op.phase, angle=op.angle,
        ))
    return tuple(mapped)


def _compile_inverse_isometry(
    algorithm3: Algorithm3Result,
) -> tuple[QuantumOperation, ...]:
    """Lower Phase-7 reversible gates to the Phase-8 logical operation IR."""
    operations: list[QuantumOperation] = []
    ancillas = tuple(algorithm3.ancilla_wires)
    for gate in algorithm3.inverse_gates:
        if isinstance(gate, X):
            operations.append(QuantumOperation("X", target=gate.target))
        elif isinstance(gate, CX):
            operations.append(QuantumOperation("CX", target=gate.target, controls=(gate.control,)))
        elif isinstance(gate, SWAP):
            operations.append(QuantumOperation("SWAP", target=gate.a, controls=(gate.b,)))
        elif isinstance(gate, Toffoli):
            operations.append(QuantumOperation("TOFFOLI", target=gate.target, controls=(gate.control_a, gate.control_b)))
        elif isinstance(gate, NegativeControlToffoli):
            zero_controls = tuple(w for w, value in zip(gate.controls, gate.control_values) if value == 0)
            for wire in zero_controls:
                operations.append(QuantumOperation("X", target=wire))
            operations.append(QuantumOperation("TOFFOLI", target=gate.target, controls=gate.controls))
            for wire in reversed(zero_controls):
                operations.append(QuantumOperation("X", target=wire))
        elif isinstance(gate, CMX):
            for target in gate.targets:
                operations.append(QuantumOperation("CX", target=target, controls=(gate.control,)))
        elif isinstance(gate, MCX):
            controls = tuple(gate.controls)
            values = tuple(gate.control_values or (1,) * len(controls))
            zero_controls = tuple(w for w, value in zip(controls, values) if value == 0)
            for wire in zero_controls:
                operations.append(QuantumOperation("X", target=wire))
            if len(controls) == 1:
                operations.append(QuantumOperation("CX", target=gate.target, controls=controls))
            elif len(controls) == 2:
                operations.append(QuantumOperation("TOFFOLI", target=gate.target, controls=controls))
            else:
                control, records = _and_compute(operations, controls, ancillas)
                operations.append(QuantumOperation("CX", target=gate.target, controls=(control,)))
                _and_uncompute(operations, records)
            for wire in reversed(zero_controls):
                operations.append(QuantumOperation("X", target=wire))
        else:  # pragma: no cover - protects against a future unsupported gate
            raise StatePreparationError(f"unsupported Algorithm-3 inverse gate: {type(gate).__name__}")
    return tuple(operations)


@dataclass(frozen=True, slots=True)
class StatePreparationMetrics:
    fidelity: float
    maximum_amplitude_error: float
    workspace_leakage_probability: float
    outside_support_probability: float
    output_norm: float
    inverse_round_trip_error: float


@dataclass(frozen=True, slots=True)
class SparseStatePreparationResources:
    total_qubits: int
    data_qubits: int
    compact_qubits: int
    algorithm3_marker_qubits: int
    algorithm3_clean_ancillas: int
    phase_clean_ancillas: int
    dense_loader: StageCounts
    sign_oracle: StageCounts
    inverse_isometry: StageCounts
    marker_cleanup: StageCounts
    total_operations: int
    total_toffolis: int
    algorithm3_paper_accounted_toffolis: int
    algorithm3_coherent_toffolis: int


@dataclass(frozen=True, slots=True)
class SparseStatePreparationCircuit:
    """Complete logical preparation circuit and its independently verified target."""

    n: int
    ell: int
    total_qubits: int
    marker_wire: int
    algorithm3_ancilla_wires: tuple[int, ...]
    phase_ancilla_wires: tuple[int, ...]
    support: tuple[str, ...]
    compact_labels: tuple[int, ...]
    coefficients: tuple[complex, ...]
    signs: tuple[int, ...]
    operations: tuple[QuantumOperation, ...]
    target_state: tuple[complex, ...]
    resources: SparseStatePreparationResources

    @property
    def workspace_qubits(self) -> int:
        return self.total_qubits - self.n

    @property
    def algorithm3_clean_ancillas(self) -> int:
        return len(self.algorithm3_ancilla_wires)

    @property
    def inverse_operations(self) -> tuple[QuantumOperation, ...]:
        """Return the exact reverse circuit, including inverse angles/phases."""
        inverse: list[QuantumOperation] = []
        for op in reversed(self.operations):
            if op.kind == "GLOBAL_PHASE":
                inverse.append(QuantumOperation("GLOBAL_PHASE", phase=op.phase.conjugate()))
            elif op.kind in {"RY", "PHASE"}:
                inverse.append(QuantumOperation(op.kind, target=op.target, angle=-op.angle))
            else:
                inverse.append(op)
        return tuple(inverse)

    def apply(self) -> tuple[complex, ...]:
        """Simulate the circuit from the all-zero state."""
        if self.total_qubits > 24:
            raise StatePreparationError(
                "statevector simulation is capped at 24 qubits; compile-only use is still available"
            )
        initial = [0j] * (1 << self.total_qubits)
        initial[0] = 1 + 0j
        return apply_operations(initial, self.total_qubits, self.operations)

    def verify(self, *, atol: float = 2e-9) -> StatePreparationMetrics:
        """Check full complex amplitudes, support leakage and all workspace wires."""
        actual = self.apply()
        workspace_mask = (1 << self.workspace_qubits) - 1
        support_ints = {int(bits, 2) for bits in self.support}
        expected = [0j] * len(actual)
        for basis, amplitude in enumerate(self.target_state):
            expected[basis << self.workspace_qubits] = amplitude
        max_error = max(abs(a - b) for a, b in zip(actual, expected))
        inner = sum(expected[i].conjugate() * actual[i] for i in range(len(actual)))
        fidelity = abs(inner) ** 2
        leakage = sum(abs(value) ** 2 for index, value in enumerate(actual) if index & workspace_mask)
        outside = sum(
            abs(value) ** 2 for index, value in enumerate(actual)
            if (index >> self.workspace_qubits) not in support_ints
        )
        norm = math.sqrt(sum(abs(value) ** 2 for value in actual))
        initial = [0j] * len(actual)
        initial[0] = 1 + 0j
        returned = apply_operations(actual, self.total_qubits, self.inverse_operations)
        round_trip_error = max(abs(value - expected_value) for value, expected_value in zip(returned, initial))
        metrics = StatePreparationMetrics(
            fidelity=float(fidelity), maximum_amplitude_error=float(max_error),
            workspace_leakage_probability=float(leakage),
            outside_support_probability=float(outside), output_norm=float(norm),
            inverse_round_trip_error=float(round_trip_error),
        )
        if (max_error > atol or fidelity < 1.0 - atol or leakage > atol
                or outside > atol or abs(norm - 1.0) > atol or round_trip_error > atol):
            raise StatePreparationError(f"end-to-end state verification failed: {metrics}")
        return metrics


def compile_sparse_state_preparation(problem: SparseStateProblem) -> SparseStatePreparationCircuit:
    """Compile a complete logical circuit for a normalized complex sparse state."""
    if not isinstance(problem, SparseStateProblem):
        raise TypeError("problem must be a SparseStateProblem")
    if problem.coefficients is None:
        raise StatePreparationError("SparseStateProblem.coefficients are required for state preparation")
    coefficients = tuple(problem.coefficients)
    signs = tuple(problem.signs if problem.signs is not None else (1,) * problem.s)
    algorithm3 = run_algorithm3(problem, signs=signs)

    # Algorithm-3 wires are [data n][marker][Algorithm-3 clean ancillas].
    # Phase ancillas are appended after them, avoiding accidental aliasing.
    phase_ancilla_count = max(0, problem.ell - 2)
    phase_start = problem.n + 1 + len(algorithm3.ancilla_wires)
    phase_ancillas = tuple(range(phase_start, phase_start + phase_ancilla_count))
    total_qubits = phase_start + phase_ancilla_count

    dense_ops = compile_dense_compact_preparation(
        coefficients, algorithm3.compact_labels, data_qubits=problem.ell,
        work_ancillas=phase_ancillas,
    )
    sign_oracle: PhaseOracleCircuit = compile_real_sign_phase_oracle(algorithm3)
    sign_ops = _map_phase_ancillas(
        sign_oracle.operations, data_qubits=problem.ell,
        phase_ancillas=phase_ancillas,
    )
    inverse_ops = _compile_inverse_isometry(algorithm3)
    marker_ops = (QuantumOperation("X", target=algorithm3.marker_wire),)
    operations = tuple(dense_ops) + tuple(sign_ops) + tuple(inverse_ops) + marker_ops

    target = [0j] * (1 << problem.n)
    for support, coefficient, sign in zip(problem.support, coefficients, signs):
        target[int(support, 2)] = coefficient * sign
    dense_counts, sign_counts = _counts(dense_ops), _counts(sign_ops)
    inverse_counts, marker_counts = _counts(inverse_ops), _counts(marker_ops)
    resources = SparseStatePreparationResources(
        total_qubits=total_qubits, data_qubits=problem.n, compact_qubits=problem.ell,
        algorithm3_marker_qubits=1,
        algorithm3_clean_ancillas=len(algorithm3.ancilla_wires),
        phase_clean_ancillas=len(phase_ancillas),
        dense_loader=dense_counts, sign_oracle=sign_counts,
        inverse_isometry=inverse_counts, marker_cleanup=marker_counts,
        total_operations=len(operations),
        total_toffolis=sum(_counts(stage).toffoli for stage in (dense_ops, sign_ops, inverse_ops, marker_ops)),
        algorithm3_paper_accounted_toffolis=algorithm3.paper_accounted_toffolis,
        algorithm3_coherent_toffolis=algorithm3.coherent_toffolis,
    )
    return SparseStatePreparationCircuit(
        n=problem.n, ell=problem.ell, total_qubits=total_qubits,
        marker_wire=algorithm3.marker_wire,
        algorithm3_ancilla_wires=tuple(algorithm3.ancilla_wires),
        phase_ancilla_wires=phase_ancillas,
        support=tuple(problem.support), compact_labels=tuple(algorithm3.compact_labels),
        coefficients=coefficients, signs=signs, operations=operations,
        target_state=tuple(target), resources=resources,
    )


def prepare_sparse_state(
    problem: SparseStateProblem, *, atol: float = 2e-9,
    max_statevector_qubits: int = 20,
) -> tuple[SparseStatePreparationCircuit, StatePreparationMetrics]:
    """Compile and verify a sparse-state preparation circuit.

    The configurable cap prevents accidental exponential allocations. For a
    larger instance, call ``compile_sparse_state_preparation`` and leave its
    statevector verification to Phase-9's scalable/backend validation.
    """
    circuit = compile_sparse_state_preparation(problem)
    if isinstance(max_statevector_qubits, bool) or not isinstance(max_statevector_qubits, int) or max_statevector_qubits < 1:
        raise StatePreparationError("max_statevector_qubits must be a positive integer")
    if circuit.total_qubits > max_statevector_qubits:
        raise StatePreparationError(
            f"exact statevector verification needs {circuit.total_qubits} qubits, "
            f"above configured cap {max_statevector_qubits}; use compile_sparse_state_preparation"
        )
    return circuit, circuit.verify(atol=atol)
