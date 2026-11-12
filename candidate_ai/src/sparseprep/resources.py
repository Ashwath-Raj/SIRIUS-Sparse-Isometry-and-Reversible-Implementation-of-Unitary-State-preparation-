"""Transparent emitted-gate histogram; analytical cost models are separate."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable
from .gates import CMX, CX, MCX, NegativeControlToffoli, PUIMacro, InversePUIMacro, SWAP, Toffoli, X


@dataclass(frozen=True, slots=True)
class ResourceCounts:
    x: int = 0
    cx: int = 0
    swap: int = 0
    toffoli: int = 0
    negative_control_toffoli: int = 0
    cmx_macros: int = 0
    mcx_macros: int = 0
    restricted_pui_macros: int = 0
    unrestricted_pui_macros: int = 0
    decomposed_toffoli: int | None = None  # None means no decomposition was supplied.


def count_emitted_resources(gates: Iterable) -> ResourceCounts:
    counts = {name: 0 for name in ResourceCounts.__dataclass_fields__ if name != "decomposed_toffoli"}
    for gate in gates:
        if isinstance(gate, X): counts["x"] += 1
        elif isinstance(gate, CX): counts["cx"] += 1
        elif isinstance(gate, SWAP): counts["swap"] += 1
        elif isinstance(gate, Toffoli): counts["toffoli"] += 1
        elif isinstance(gate, NegativeControlToffoli): counts["negative_control_toffoli"] += 1
        elif isinstance(gate, CMX): counts["cmx_macros"] += 1
        elif isinstance(gate, MCX): counts["mcx_macros"] += 1
        elif isinstance(gate, (PUIMacro, InversePUIMacro)):
            kind = gate.kind if isinstance(gate, PUIMacro) else gate.original.kind
            if kind.value == "restricted": counts["restricted_pui_macros"] += 1
            else: counts["unrestricted_pui_macros"] += 1
        else: raise TypeError(f"unsupported gate type: {type(gate).__name__}")
    return ResourceCounts(**counts)
