"""Small immutable reversible gate IR.

Wire numbering is big-endian: wire 0 is the leftmost/most-significant bit.
The elementary gates are classical reversible permutations and are simulated
exactly on computational-basis strings. PUI macros are retained symbolically
until their paper-specific expansion is implemented in Phase 5.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


class GateValidationError(ValueError):
    pass


class UnsupportedGateError(NotImplementedError):
    pass


def _wire(wire: int) -> None:
    if isinstance(wire, bool) or not isinstance(wire, int) or wire < 0:
        raise GateValidationError("wire indices must be non-negative integers")


@dataclass(frozen=True, slots=True)
class X:
    target: int
    def __post_init__(self): _wire(self.target)
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class CX:
    control: int
    target: int
    def __post_init__(self):
        _wire(self.control); _wire(self.target)
        if self.control == self.target: raise GateValidationError("CX control and target must differ")
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class SWAP:
    a: int
    b: int
    def __post_init__(self):
        _wire(self.a); _wire(self.b)
        if self.a == self.b: raise GateValidationError("SWAP wires must differ")
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class Toffoli:
    control_a: int
    control_b: int
    target: int
    def __post_init__(self):
        wires = (self.control_a, self.control_b, self.target)
        for wire in wires: _wire(wire)
        if len(set(wires)) != 3: raise GateValidationError("Toffoli wires must be distinct")
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class NegativeControlToffoli:
    controls: tuple[int, int]
    target: int
    control_values: tuple[int, int] = (0, 1)
    def __post_init__(self):
        if len(self.controls) != 2 or len(self.control_values) != 2:
            raise GateValidationError("negative-control Toffoli requires two controls and two values")
        for wire in (*self.controls, self.target): _wire(wire)
        if len(set((*self.controls, self.target))) != 3:
            raise GateValidationError("negative-control Toffoli wires must be distinct")
        if any(v not in (0, 1) for v in self.control_values):
            raise GateValidationError("control values must be 0 or 1")
        if self.control_values == (1, 1):
            raise GateValidationError("use Toffoli for two positive controls")
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class CMX:
    control: int
    targets: tuple[int, ...]
    def __post_init__(self):
        _wire(self.control)
        targets = tuple(self.targets)
        if not targets: raise GateValidationError("CMX requires at least one target")
        for wire in targets: _wire(wire)
        if len(set(targets)) != len(targets) or self.control in targets:
            raise GateValidationError("CMX wires must be distinct")
        object.__setattr__(self, "targets", targets)
    def inverse(self): return self


@dataclass(frozen=True, slots=True)
class MCX:
    controls: tuple[int, ...]
    target: int
    control_values: tuple[int, ...] | None = None
    def __post_init__(self):
        controls = tuple(self.controls)
        if not controls: raise GateValidationError("MCX requires at least one control")
        for wire in (*controls, self.target): _wire(wire)
        if len(set((*controls, self.target))) != len(controls) + 1:
            raise GateValidationError("MCX wires must be distinct")
        values = (1,) * len(controls) if self.control_values is None else tuple(self.control_values)
        if len(values) != len(controls) or any(v not in (0, 1) for v in values):
            raise GateValidationError("MCX control_values must contain one 0/1 value per control")
        object.__setattr__(self, "controls", controls)
        object.__setattr__(self, "control_values", values)
    def inverse(self): return self


class PUIKind(str, Enum):
    RESTRICTED = "restricted"
    UNRESTRICTED = "unrestricted"


@dataclass(frozen=True, slots=True)
class PUIMacro:
    """Symbolic PUI operation; expansion and basis simulation land in Phase 5."""
    kind: PUIKind
    interval: tuple[int, int]
    L: int
    g: int
    address_wires: tuple[int, ...]
    unary_wires: tuple[int, ...]
    def __post_init__(self):
        if not isinstance(self.kind, PUIKind): object.__setattr__(self, "kind", PUIKind(self.kind))
        if len(self.interval) != 2 or self.interval[0] < 0 or self.interval[1] <= self.interval[0]:
            raise GateValidationError("PUI interval must be a non-empty half-open interval")
        if self.L < 1 or self.g < 0:
            raise GateValidationError("PUI metadata requires L >= 1 and g >= 0")
        for wire in (*self.address_wires, *self.unary_wires): _wire(wire)
        all_wires = (*self.address_wires, *self.unary_wires)
        if len(set(all_wires)) != len(all_wires):
            raise GateValidationError("PUI address and unary wires must be distinct")
    def inverse(self): return InversePUIMacro(self)


@dataclass(frozen=True, slots=True)
class InversePUIMacro:
    original: PUIMacro
    def inverse(self): return self.original


PrimitiveGate: TypeAlias = X | CX | SWAP | Toffoli | NegativeControlToffoli | CMX | MCX
Gate: TypeAlias = PrimitiveGate | PUIMacro | InversePUIMacro


def invert_sequence(gates: tuple[Gate, ...] | list[Gate]) -> tuple[Gate, ...]:
    return tuple(g.inverse() for g in reversed(gates))
