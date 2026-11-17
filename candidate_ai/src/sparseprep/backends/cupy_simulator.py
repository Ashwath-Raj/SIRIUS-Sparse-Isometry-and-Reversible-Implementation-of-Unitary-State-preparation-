"""Optional CuPy vectorized basis-state simulator for n <= 63 qubits.

This backend is deliberately optional. CPU simulation remains the correctness
oracle. Each row is encoded as uint64; wire 0 is the most-significant bit.
"""
from __future__ import annotations
import numpy as np
from ..gates import CMX, CX, MCX, NegativeControlToffoli, PUIMacro, InversePUIMacro, SWAP, Toffoli, X
from ..simulator import UnsupportedGateError


def _cupy():
    try:
        import cupy as cp
    except Exception as exc:  # pragma: no cover - depends on local CUDA install
        raise RuntimeError("CuPy/CUDA backend is unavailable in this Python environment") from exc
    if cp.cuda.runtime.getDeviceCount() < 1:
        raise RuntimeError("CuPy found no CUDA device")
    return cp


def simulate_int_states_cupy(states, n: int, gates):
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 63:
        raise ValueError("CuPy uint64 backend supports 1 <= n <= 63")
    def validate_wire(wire: int) -> None:
        if isinstance(wire, bool) or not isinstance(wire, int) or not 0 <= wire < n:
            raise ValueError(f"wire index must lie in [0, {n})")

    supported = (X, SWAP, CX, Toffoli, NegativeControlToffoli, CMX, MCX)
    for gate in gates:
        if isinstance(gate, (PUIMacro, InversePUIMacro)):
            raise UnsupportedGateError("PUI macro simulation is deferred to Phase 5")
        if not isinstance(gate, supported):
            raise UnsupportedGateError(f"unsupported gate type: {type(gate).__name__}")
        if isinstance(gate, X): wires = (gate.target,)
        elif isinstance(gate, SWAP): wires = (gate.a, gate.b)
        elif isinstance(gate, CX): wires = (gate.control, gate.target)
        elif isinstance(gate, Toffoli): wires = (gate.control_a, gate.control_b, gate.target)
        elif isinstance(gate, NegativeControlToffoli): wires = (*gate.controls, gate.target)
        elif isinstance(gate, CMX): wires = (gate.control, *gate.targets)
        else: wires = (*gate.controls, gate.target)
        for wire in wires:
            validate_wire(wire)

    cp = _cupy()
    values = cp.asarray(states, dtype=cp.uint64).copy()
    limit = cp.uint64(1 << n)
    if values.size and bool(cp.any(values >= limit).get()):
        raise ValueError("basis-state integer does not fit in n bits")

    def mask(wire: int) -> cp.uint64:
        validate_wire(wire)
        return cp.uint64(1 << (n - 1 - wire))

    for gate in gates:
        if isinstance(gate, X):
            values ^= mask(gate.target)
        elif isinstance(gate, SWAP):
            ma, mb = mask(gate.a), mask(gate.b)
            diff = ((values & ma) != 0) ^ ((values & mb) != 0)
            values ^= cp.where(diff, ma | mb, cp.uint64(0))
        elif isinstance(gate, CX):
            values ^= cp.where((values & mask(gate.control)) != 0, mask(gate.target), cp.uint64(0))
        elif isinstance(gate, Toffoli):
            active = ((values & mask(gate.control_a)) != 0) & ((values & mask(gate.control_b)) != 0)
            values ^= cp.where(active, mask(gate.target), cp.uint64(0))
        elif isinstance(gate, NegativeControlToffoli):
            active = cp.ones(values.shape, dtype=cp.bool_)
            for wire, bit in zip(gate.controls, gate.control_values):
                observed = (values & mask(wire)) != 0
                active &= observed if bit else ~observed
            values ^= cp.where(active, mask(gate.target), cp.uint64(0))
        elif isinstance(gate, CMX):
            active = (values & mask(gate.control)) != 0
            for target in gate.targets:
                values ^= cp.where(active, mask(target), cp.uint64(0))
        elif isinstance(gate, MCX):
            active = cp.ones(values.shape, dtype=cp.bool_)
            for wire, bit in zip(gate.controls, gate.control_values):
                observed = (values & mask(wire)) != 0
                active &= observed if bit else ~observed
            values ^= cp.where(active, mask(gate.target), cp.uint64(0))
    return values


def simulate_bitstrings_cupy(states, n: int, gates) -> tuple[str, ...]:
    from ..model import int_to_bitstring
    from ..model import bitstring_to_int
    output = simulate_int_states_cupy([bitstring_to_int(x) for x in states], n, gates)
    host = cp_asnumpy(output)
    return tuple(int_to_bitstring(int(x), n) for x in host)


def cp_asnumpy(array):
    cp = _cupy()
    return cp.asnumpy(array)
