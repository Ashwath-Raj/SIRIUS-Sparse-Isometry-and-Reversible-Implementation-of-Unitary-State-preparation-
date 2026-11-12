"""Deterministic exact simulator for the Phase 3 classical reversible gate subset."""
from __future__ import annotations
from collections.abc import Iterable
from .gates import (
    CMX, CX, MCX, NegativeControlToffoli, PrimitiveGate, PUIMacro,
    InversePUIMacro, SWAP, Toffoli, UnsupportedGateError, X,
)


def _check_state(bits: str, n: int | None = None) -> None:
    if not isinstance(bits, str) or not bits or any(c not in "01" for c in bits):
        raise ValueError("state must be a non-empty bitstring")
    if n is not None and len(bits) != n:
        raise ValueError(f"state width {len(bits)} does not match n={n}")


def apply_gate(bits: str, gate) -> str:
    """Apply one primitive reversible gate to a computational-basis bitstring."""
    _check_state(bits)
    n = len(bits)
    if isinstance(gate, (PUIMacro, InversePUIMacro)):
        raise UnsupportedGateError(
            "PUI is a symbolic macro in Phase 3; its reversible expansion is implemented in Phase 5"
        )
    if not isinstance(gate, (X, CX, SWAP, Toffoli, NegativeControlToffoli, CMX, MCX)):
        raise TypeError(f"unsupported gate type: {type(gate).__name__}")

    wires = []
    if isinstance(gate, X): wires = [gate.target]
    elif isinstance(gate, CX): wires = [gate.control, gate.target]
    elif isinstance(gate, SWAP): wires = [gate.a, gate.b]
    elif isinstance(gate, Toffoli): wires = [gate.control_a, gate.control_b, gate.target]
    elif isinstance(gate, NegativeControlToffoli): wires = [*gate.controls, gate.target]
    elif isinstance(gate, CMX): wires = [gate.control, *gate.targets]
    elif isinstance(gate, MCX): wires = [*gate.controls, gate.target]
    if any(w >= n for w in wires):
        raise ValueError(f"gate wire index must be smaller than state width n={n}")

    out = list(bits)
    if isinstance(gate, X):
        out[gate.target] = "1" if out[gate.target] == "0" else "0"
    elif isinstance(gate, CX):
        if out[gate.control] == "1": out[gate.target] = "1" if out[gate.target] == "0" else "0"
    elif isinstance(gate, SWAP):
        out[gate.a], out[gate.b] = out[gate.b], out[gate.a]
    elif isinstance(gate, Toffoli):
        if out[gate.control_a] == out[gate.control_b] == "1":
            out[gate.target] = "1" if out[gate.target] == "0" else "0"
    elif isinstance(gate, NegativeControlToffoli):
        if all(int(out[w]) == value for w, value in zip(gate.controls, gate.control_values)):
            out[gate.target] = "1" if out[gate.target] == "0" else "0"
    elif isinstance(gate, CMX):
        if out[gate.control] == "1":
            for target in gate.targets:
                out[target] = "1" if out[target] == "0" else "0"
    elif isinstance(gate, MCX):
        if all(int(out[w]) == value for w, value in zip(gate.controls, gate.control_values)):
            out[gate.target] = "1" if out[gate.target] == "0" else "0"
    return "".join(out)


def simulate_basis_state(bits: str, gates: Iterable) -> str:
    state = bits
    for gate in gates:
        state = apply_gate(state, gate)
    return state


def simulate_support(support: Iterable[str], gates: Iterable) -> tuple[str, ...]:
    gate_seq = tuple(gates)
    return tuple(simulate_basis_state(state, gate_seq) for state in support)
