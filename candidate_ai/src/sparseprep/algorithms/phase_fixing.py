"""Phase 7.1 reference model for Algorithm 3 sign/marker bookkeeping.

This module deliberately stops before circuit synthesis.  It provides a small,
explicit classical oracle for the signed tableau state and the reversible
basis-permutation operations used by Algorithm 3.  Phase 7.2 will connect this
oracle to the Phase 5 restricted-PUI tree and Phase 6 batch constructor.

The sign ledger is not a replacement for a quantum circuit: ``global_phase``
records the exact +/-1 phase multiplying a basis row.  The marker is an extra
logical qubit initialized to one and changed to zero when that row is visited
by a restricted PUI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence


class PhaseFixingError(ValueError):
    """Invalid input or a violated Algorithm 3 reference-model invariant."""


def _check_wire(wire: int, width: int, name: str = "wire") -> None:
    if isinstance(wire, bool) or not isinstance(wire, int):
        raise TypeError(f"{name} must be an integer")
    if not 0 <= wire < width:
        raise IndexError(f"{name}={wire} outside [0, {width})")


def _check_sign(sign: int, name: str = "sign") -> None:
    if isinstance(sign, bool) or not isinstance(sign, int) or sign not in (-1, 1):
        raise PhaseFixingError(f"{name} must be exactly +1 or -1; got {sign!r}")


def _validate_bits(bits: str, width: int, name: str = "bitstring") -> None:
    if not isinstance(bits, str):
        raise TypeError(f"{name} must be a string")
    if len(bits) != width or any(bit not in "01" for bit in bits):
        raise PhaseFixingError(
            f"{name} must contain exactly {width} binary characters; got {bits!r}"
        )


@dataclass(slots=True)
class PhaseFixingRow:
    """One support row, retaining identity while its basis label changes."""

    row_id: int
    initial_bits: str
    bits: str
    input_sign: int
    marker: int = 1
    global_phase: int = 1
    restricted_pui_visits: int = 0

    @property
    def expected_phase(self) -> int:
        """Target +/-1 phase supplied to Algorithm 3 for this row."""
        return self.input_sign


@dataclass(frozen=True, slots=True)
class PhaseFixTraceEvent:
    """Compact audit event; no full tableau snapshots are retained."""

    sequence: int
    kind: str
    controls: tuple[int, ...] = ()
    targets: tuple[int, ...] = ()
    row_ids: tuple[int, ...] = ()
    phase_multipliers: tuple[tuple[int, int], ...] = ()
    detail: str = ""


class PhaseFixingTableau:
    """Signed tableau and marker ledger for small-instance Algorithm 3 checks.

    Wire indexing follows the project convention: bit zero is the leftmost
    (most-significant) character of each big-endian row string.  The marker is
    stored separately from the ``n`` data bits and is therefore not counted in
    ``n_qubits``.

    ``record_restricted_pui_visit`` accepts an explicit set of every tableau
    row affected by a restricted-PUI interval, plus each row's resulting data
    word. Requiring ``affected_row_ids`` to match the update keys prevents a
    caller from silently omitting a row that shares a visited address.
    """

    def __init__(self, support: Sequence[str], signs: Sequence[int]):
        if not support:
            raise PhaseFixingError("support must contain at least one row")
        if len(support) != len(signs):
            raise PhaseFixingError("support and signs must have equal lengths")
        first = support[0]
        if not isinstance(first, str) or len(first) == 0:
            raise PhaseFixingError("support rows must be non-empty bitstrings")
        width = len(first)
        rows: list[PhaseFixingRow] = []
        for row_id, (bits, sign) in enumerate(zip(support, signs)):
            _validate_bits(bits, width, f"support[{row_id}]")
            _check_sign(sign, f"signs[{row_id}]")
            rows.append(
                PhaseFixingRow(
                    row_id=row_id,
                    initial_bits=bits,
                    bits=bits,
                    input_sign=sign,
                    marker=1,
                    global_phase=1,
                    restricted_pui_visits=0,
                )
            )
        if len({row.bits for row in rows}) != len(rows):
            raise PhaseFixingError("support rows must be pairwise distinct")
        self.n_qubits = width
        self.rows = rows
        self.trace: list[PhaseFixTraceEvent] = []
        self._assert_invariants()

    @classmethod
    def from_support(cls, support: Sequence[str], signs: Sequence[int]) -> "PhaseFixingTableau":
        """Named constructor matching the other project model APIs."""
        return cls(support, signs)

    @property
    def support_size(self) -> int:
        return len(self.rows)

    @property
    def current_tableau(self) -> tuple[str, ...]:
        return tuple(row.bits for row in self.rows)

    @property
    def initial_tableau(self) -> tuple[str, ...]:
        return tuple(row.initial_bits for row in self.rows)

    @property
    def markers(self) -> tuple[int, ...]:
        return tuple(row.marker for row in self.rows)

    @property
    def signs(self) -> tuple[int, ...]:
        return tuple(row.input_sign for row in self.rows)

    @property
    def accumulated_phases(self) -> tuple[int, ...]:
        return tuple(row.global_phase for row in self.rows)

    @property
    def visit_counts(self) -> tuple[int, ...]:
        return tuple(row.restricted_pui_visits for row in self.rows)

    def row(self, row_id: int) -> PhaseFixingRow:
        if isinstance(row_id, bool) or not isinstance(row_id, int):
            raise TypeError("row_id must be an integer")
        if not 0 <= row_id < self.support_size:
            raise IndexError(f"row_id must be in [0, {self.support_size})")
        return self.rows[row_id]

    def _assert_invariants(self) -> None:
        if len(self.rows) != self.support_size:
            raise PhaseFixingError("row count changed")
        if len(set(self.current_tableau)) != self.support_size:
            raise PhaseFixingError("a reversible tableau operation collapsed distinct rows")
        for row in self.rows:
            _validate_bits(row.bits, self.n_qubits, f"row[{row.row_id}].bits")
            _check_sign(row.input_sign, f"row[{row.row_id}].input_sign")
            _check_sign(row.global_phase, f"row[{row.row_id}].global_phase")
            if row.marker not in (0, 1):
                raise PhaseFixingError(f"row {row.row_id} marker must be 0 or 1")
            if row.restricted_pui_visits not in (0, 1):
                raise PhaseFixingError(
                    f"row {row.row_id} must be visited at most once; "
                    f"got {row.restricted_pui_visits} visits"
                )
            if row.marker != 1 - row.restricted_pui_visits:
                raise PhaseFixingError(
                    f"row {row.row_id} marker/visit mismatch: marker={row.marker}, "
                    f"visits={row.restricted_pui_visits}"
                )

    def _record_gate(
        self,
        kind: str,
        transform: Callable[[str, int], str],
        *,
        controls: Iterable[int] = (),
        targets: Iterable[int] = (),
        detail: str = "",
    ) -> None:
        before = self.current_tableau
        after = tuple(transform(bits, row.marker) for bits, row in zip(before, self.rows))
        for row_id, bits in enumerate(after):
            _validate_bits(bits, self.n_qubits, f"gate output row {row_id}")
        if len(set(after)) != self.support_size:
            raise PhaseFixingError(f"{kind} unexpectedly collapsed distinct tableau rows")
        for row, bits in zip(self.rows, after):
            row.bits = bits
        self.trace.append(
            PhaseFixTraceEvent(
                sequence=len(self.trace),
                kind=kind,
                controls=tuple(controls),
                targets=tuple(targets),
                row_ids=tuple(range(self.support_size)),
                detail=detail,
            )
        )
        self._assert_invariants()

    def apply_x(self, target: int, *, detail: str = "") -> None:
        _check_wire(target, self.n_qubits, "target")
        self._record_gate(
            "X",
            lambda bits, _marker: bits[:target] + str(1 - int(bits[target])) + bits[target + 1 :],
            targets=(target,),
            detail=detail,
        )

    def apply_cx(self, control: int, target: int, *, detail: str = "") -> None:
        _check_wire(control, self.n_qubits, "control")
        _check_wire(target, self.n_qubits, "target")
        if control == target:
            raise PhaseFixingError("CX control and target must be different wires")

        def transform(bits: str, _marker: int) -> str:
            if bits[control] != "1":
                return bits
            return bits[:target] + str(1 - int(bits[target])) + bits[target + 1 :]

        self._record_gate("CX", transform, controls=(control,), targets=(target,), detail=detail)

    def marked_unvisited_rows(self) -> tuple[int, ...]:
        """Return stable row IDs whose Algorithm 3 marker is still one."""
        return tuple(row.row_id for row in self.rows if row.marker == 1)

    def apply_counter_effect_cx(
        self, batch_row_id: int, control: int, target: int
    ) -> None:
        """Apply Algorithm 3's counter-effect CX for one still-marked batch row.

        The selected batch row must still have marker 1 and value 1 on the
        specified residual control wire. The CX itself is global, as a circuit
        gate must be: it is applied to every tableau row whose control bit is 1.
        """
        row = self.row(batch_row_id)
        _check_wire(control, self.n_qubits, "control")
        _check_wire(target, self.n_qubits, "target")
        if row.marker != 1:
            raise PhaseFixingError(
                f"counter-effect correction requires marker 1 on row {batch_row_id}"
            )
        if row.bits[control] != "1":
            raise PhaseFixingError(
                f"counter-effect correction control wire {control} is not 1 on row {batch_row_id}"
            )
        self.apply_cx(
            control,
            target,
            detail=f"Algorithm 3 counter-effect CX for batch row {batch_row_id}",
        )

    def apply_marker_cx(self, target: int, *, detail: str = "Algorithm 3 marker-controlled CX") -> None:
        """Apply CX with the extra marker qubit as control, across all rows."""
        _check_wire(target, self.n_qubits, "target")

        def transform(bits: str, marker: int) -> str:
            if marker != 1:
                return bits
            return bits[:target] + str(1 - int(bits[target])) + bits[target + 1 :]

        self._record_gate(
            "MARKER_CX", transform, controls=(self.n_qubits,), targets=(target,), detail=detail
        )

    def apply_swap(self, left: int, right: int, *, detail: str = "") -> None:
        _check_wire(left, self.n_qubits, "left")
        _check_wire(right, self.n_qubits, "right")
        if left == right:
            return

        def transform(bits: str, _marker: int) -> str:
            values = list(bits)
            values[left], values[right] = values[right], values[left]
            return "".join(values)

        self._record_gate("SWAP", transform, targets=(left, right), detail=detail)

    def apply_toffoli(
        self, control_a: int, control_b: int, target: int, *, detail: str = ""
    ) -> None:
        for name, wire in (("control_a", control_a), ("control_b", control_b), ("target", target)):
            _check_wire(wire, self.n_qubits, name)
        if len({control_a, control_b, target}) != 3:
            raise PhaseFixingError("Toffoli controls and target must be distinct")

        def transform(bits: str, _marker: int) -> str:
            if bits[control_a] == "1" and bits[control_b] == "1":
                return bits[:target] + str(1 - int(bits[target])) + bits[target + 1 :]
            return bits

        self._record_gate(
            "TOFFOLI", transform, controls=(control_a, control_b), targets=(target,), detail=detail
        )

    def apply_cmx(self, control: int, targets: Sequence[int], *, detail: str = "") -> None:
        _check_wire(control, self.n_qubits, "control")
        target_tuple = tuple(targets)
        if len(set(target_tuple)) != len(target_tuple):
            raise PhaseFixingError("CMX targets must be unique")
        for target in target_tuple:
            _check_wire(target, self.n_qubits, "target")
            if target == control:
                raise PhaseFixingError("CMX control cannot also be a target")

        def transform(bits: str, _marker: int) -> str:
            if bits[control] != "1":
                return bits
            values = list(bits)
            for target in target_tuple:
                values[target] = "1" if values[target] == "0" else "0"
            return "".join(values)

        self._record_gate("CMX", transform, controls=(control,), targets=target_tuple, detail=detail)

    def record_restricted_pui_visit(
        self,
        updates: Mapping[int, str],
        *,
        affected_row_ids: Iterable[int],
        interval: tuple[int, int],
        detail: str = "restricted PUI visit with sign fix",
    ) -> None:
        """Record one restricted-PUI visit and apply its per-row sign.

        ``updates`` supplies the post-PUI data word for every affected row.
        ``affected_row_ids`` is independently supplied and must exactly match
        the mapping keys. This makes omitted same-address rows detectable by
        the caller instead of silently assuming only the batch members change.
        The row's input sign is multiplied into its global phase, and its
        marker transitions from 1 to 0.
        """
        if not isinstance(updates, Mapping) or not updates:
            raise PhaseFixingError("updates must be a non-empty row_id -> bitstring mapping")
        lo, hi = interval
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (lo, hi)) or lo > hi:
            raise PhaseFixingError("interval must be an inclusive integer pair (lo, hi)")
        keys = set(updates)
        required = set(affected_row_ids)
        if keys != required:
            missing = sorted(required - keys)
            extra = sorted(keys - required)
            raise PhaseFixingError(
                f"restricted-PUI update coverage mismatch; missing={missing}, extra={extra}"
            )
        row_ids = sorted(keys)
        for row_id in row_ids:
            row = self.row(row_id)
            if row.marker != 1 or row.restricted_pui_visits != 0:
                raise PhaseFixingError(f"row {row_id} has already been visited by restricted PUI")
            _validate_bits(updates[row_id], self.n_qubits, f"updates[{row_id}]")
        candidate = list(self.current_tableau)
        phase_multipliers: list[tuple[int, int]] = []
        for row_id in row_ids:
            candidate[row_id] = updates[row_id]
            phase_multipliers.append((row_id, self.row(row_id).input_sign))
        if len(set(candidate)) != self.support_size:
            raise PhaseFixingError("restricted-PUI update would collapse distinct tableau rows")

        for row_id in row_ids:
            row = self.row(row_id)
            row.bits = updates[row_id]
            row.global_phase *= row.input_sign
            row.marker = 0
            row.restricted_pui_visits = 1
        self.trace.append(
            PhaseFixTraceEvent(
                sequence=len(self.trace),
                kind="RESTRICTED_PUI_SIGN_FIX",
                row_ids=tuple(row_ids),
                phase_multipliers=tuple(phase_multipliers),
                detail=f"interval={interval}; {detail}",
            )
        )
        self._assert_invariants()

    def verify_completed(self, expected_output_by_row: Mapping[int, str]) -> None:
        """Check Algorithm 3's signed basis action for a completed small case.

        This verifies the reference-model postcondition
        ``G|C_i> = a_i |f(i)>_subspace |0>_residual`` at the bitstring/phase
        level. It does not claim that a gate-level circuit has been synthesized.
        """
        expected_ids = set(range(self.support_size))
        if set(expected_output_by_row) != expected_ids:
            raise PhaseFixingError("expected output mapping must contain every row exactly once")
        outputs = [expected_output_by_row[i] for i in range(self.support_size)]
        for row_id, output in enumerate(outputs):
            _validate_bits(output, self.n_qubits, f"expected_output_by_row[{row_id}]")
        if len(set(outputs)) != self.support_size:
            raise PhaseFixingError("expected output mapping must be injective")
        for row in self.rows:
            if row.marker != 0 or row.restricted_pui_visits != 1:
                raise PhaseFixingError(f"row {row.row_id} was not visited exactly once")
            if row.bits != expected_output_by_row[row.row_id]:
                raise PhaseFixingError(
                    f"row {row.row_id} output mismatch: got {row.bits}, "
                    f"expected {expected_output_by_row[row.row_id]}"
                )
            if row.global_phase != row.input_sign:
                raise PhaseFixingError(
                    f"row {row.row_id} phase mismatch: got {row.global_phase}, "
                    f"expected {row.input_sign}"
                )
        self._assert_invariants()

    def summary(self) -> dict[str, object]:
        """Return JSON-serializable state useful in test logs and audit notes."""
        return {
            "n_qubits": self.n_qubits,
            "support_size": self.support_size,
            "initial_tableau": list(self.initial_tableau),
            "current_tableau": list(self.current_tableau),
            "input_signs": list(self.signs),
            "accumulated_phases": list(self.accumulated_phases),
            "markers": list(self.markers),
            "restricted_pui_visits": list(self.visit_counts),
            "trace_event_count": len(self.trace),
            "trace_kinds": [event.kind for event in self.trace],
        }
