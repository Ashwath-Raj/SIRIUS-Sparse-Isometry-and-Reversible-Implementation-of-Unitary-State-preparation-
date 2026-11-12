"""Stable-row tableau for support transformations; phase metadata stays separate."""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable
from .gates import Gate, invert_sequence
from .simulator import apply_gate


@dataclass(frozen=True, slots=True)
class TableauRow:
    row_id: int
    original: str
    current: str
    phase: int = 1
    def __post_init__(self):
        if isinstance(self.row_id, bool) or not isinstance(self.row_id, int) or self.row_id < 0:
            raise ValueError("row_id must be a non-negative integer")
        for name, bits in (("original", self.original), ("current", self.current)):
            if not isinstance(bits, str) or not bits or any(c not in "01" for c in bits):
                raise ValueError(f"{name} must be a non-empty bitstring")
        if len(self.original) != len(self.current):
            raise ValueError("original and current bitstrings must have equal width")
        if self.phase not in (-1, 1) or isinstance(self.phase, bool):
            raise ValueError("phase must be +1 or -1")


@dataclass(frozen=True, slots=True)
class Tableau:
    rows: tuple[TableauRow, ...]
    def __post_init__(self):
        rows = tuple(self.rows)
        if not rows: raise ValueError("tableau must contain at least one row")
        ids = [r.row_id for r in rows]
        if len(set(ids)) != len(ids): raise ValueError("row IDs must be unique and stable")
        widths = {len(r.current) for r in rows}
        if len(widths) != 1: raise ValueError("all tableau rows must have the same width")
        originals = [r.original for r in rows]
        currents = [r.current for r in rows]
        if len(set(originals)) != len(originals): raise ValueError("original support rows must be unique")
        if len(set(currents)) != len(currents):
            raise ValueError("current rows must remain distinct under reversible transformations")
        object.__setattr__(self, "rows", rows)

    @classmethod
    def from_support(cls, support: Iterable[str], signs: Iterable[int] | None = None) -> "Tableau":
        support = tuple(support)
        phase_values = (1,) * len(support) if signs is None else tuple(signs)
        if len(phase_values) != len(support): raise ValueError("sign count must equal support size")
        return cls(tuple(TableauRow(i, bits, bits, phase_values[i]) for i, bits in enumerate(support)))

    @property
    def n(self) -> int:
        return len(self.rows[0].current)

    @property
    def support(self) -> tuple[str, ...]:
        return tuple(row.current for row in self.rows)

    def row(self, row_id: int) -> TableauRow:
        for row in self.rows:
            if row.row_id == row_id: return row
        raise KeyError(row_id)

    def apply(self, gate: Gate) -> "Tableau":
        updated = tuple(
            TableauRow(r.row_id, r.original, apply_gate(r.current, gate), r.phase)
            for r in self.rows
        )
        return Tableau(updated)

    def apply_sequence(self, gates: Iterable[Gate]) -> "Tableau":
        result = self
        for gate in gates: result = result.apply(gate)
        return result

    def with_phases(self, phases: Iterable[int]) -> "Tableau":
        phases = tuple(phases)
        if len(phases) != len(self.rows): raise ValueError("phase count must equal row count")
        return Tableau(tuple(
            TableauRow(r.row_id, r.original, r.current, phases[i])
            for i, r in enumerate(self.rows)
        ))

    def inverse_round_trip(self, gates: Iterable[Gate]) -> "Tableau":
        gate_seq = tuple(gates)
        return self.apply_sequence(gate_seq).apply_sequence(invert_sequence(gate_seq))
