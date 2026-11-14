"""Shared-prefix balanced-tree emitter for restricted/unrestricted PUI.

Paper basis: Rupprecht & Wölk (2026), Section 3, Algorithm 2, Figures 6-7.

The emitter lowers Algorithm 2 into an exact *coherent* reversible gate
sequence using a depth-reused clean-ancilla pool. Each internal tree split
computes the left-child selector into one ancilla, visits the left branch,
XORs the parent selector into that ancilla to select the right child, visits
the right branch, restores the left-child value, and coherently uncomputes.

The paper's Toffoli accounting uses the measurement-based adjoint of the AND
primitive (Appendix A), whose additional Toffoli cost is zero. This module
therefore reports two distinct numbers:

* ``paper_accounted_toffolis``: one Toffoli per selector-AND computation;
* ``coherent_toffolis``: compute plus explicit unitary uncompute in this
  simulator-friendly reversible IR (twice the compute count).

The gate sequence is compared against ``PUIPlan.gates`` (the direct MCX
semantic oracle). It does NOT simulate measurement/feed-forward; the coherent
uncompute is deliberately more expensive but has the same basis action and
returns all clean ancillas to zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from .gates import (
    CX,
    NegativeControlToffoli,
    PrimitiveGate,
    Toffoli,
    X,
    invert_sequence,
)
from .pui import PUIPlan, PUIValidationError
from .simulator import simulate_basis_state


@dataclass(frozen=True, slots=True)
class _Selector:
    wire: int
    value: int


@dataclass(frozen=True, slots=True)
class PUITreeCircuit:
    """An optimized shared-prefix PUI circuit and its resource metadata."""

    kind: str
    address_width: int
    interval: tuple[int, int]
    address_wires: tuple[int, ...]
    target_wires: tuple[int, ...]
    ancilla_wires: tuple[int, ...]
    used_ancilla_wires: tuple[int, ...]
    gates: tuple[PrimitiveGate, ...]
    and_compute_toffolis: int
    target_x_operations: int
    free_bit_positions: tuple[int, ...]
    extra_address_map: tuple[tuple[int, int], ...]

    @property
    def paper_accounted_toffolis(self) -> int:
        """Toffoli cost with Appendix A measurement-based AND adjoints."""
        return self.and_compute_toffolis

    @property
    def coherent_toffolis(self) -> int:
        """Toffoli count in ``gates`` with explicit coherent uncomputation."""
        return sum(isinstance(g, (Toffoli, NegativeControlToffoli)) for g in self.gates)

    @property
    def max_clean_ancillas(self) -> int:
        """Number of distinct ancilla wires actually touched by the circuit."""
        return len(self.used_ancilla_wires)

    @property
    def paper_clean_ancilla_bound(self) -> int:
        return max(0, self.address_width - 1)

    @property
    def cx_count(self) -> int:
        return sum(isinstance(g, CX) for g in self.gates)

    @property
    def x_count(self) -> int:
        return sum(isinstance(g, X) for g in self.gates)

    def inverse_gates(self) -> tuple[PrimitiveGate, ...]:
        return invert_sequence(self.gates)

    def apply(self, state: str) -> str:
        return simulate_basis_state(state, self.gates)


def _emit_conditioned_cx(gates: list[PrimitiveGate], control: _Selector, target: int) -> None:
    """Emit X(target) controlled on one wire equalling control.value."""
    if control.value == 1:
        gates.append(CX(control.wire, target))
    else:
        # Negative-control CX using X conjugation; the address/selector wire
        # is restored immediately and remains valid for subsequent branches.
        gates.extend((X(control.wire), CX(control.wire, target), X(control.wire)))


def _and_compute(control: _Selector, address_wire: int, address_value: int, target: int) -> PrimitiveGate:
    """Return a 2-control AND into a clean target ancilla."""
    values = (control.value, address_value)
    if values == (1, 1):
        return Toffoli(control.wire, address_wire, target)
    return NegativeControlToffoli((control.wire, address_wire), target, values)


def compile_pui_tree(
    plan: PUIPlan,
    *,
    ancilla_wires: Iterable[int] | None = None,
) -> PUITreeCircuit:
    """Compile ``plan`` using the shared-prefix tree of Algorithm 2.

    ``plan`` must come from :func:`build_pui_plan`. Address bits are interpreted
    big-endian, and the input address wires are preserved. If no explicit
    ancilla wires are supplied, ``w-1`` clean wires are allocated immediately
    after the highest address/target wire.

    The returned gate sequence is fully coherent: every AND compute is
    explicitly reversed after its subtree. For resource reporting, count the
    compute half once to match the paper's measurement-based AND-adjoint
    accounting; see ``paper_accounted_toffolis`` versus ``coherent_toffolis``.
    """
    if not isinstance(plan, PUIPlan):
        raise TypeError("plan must be a PUIPlan created by build_pui_plan")

    targets = tuple(sorted({t for _, ts in plan.target_map for t in ts}))
    occupied = set(plan.address_wires) | set(targets)
    slot_count = max(0, plan.address_width - 1)

    if ancilla_wires is None:
        first = max(occupied, default=-1) + 1
        ancillas = tuple(range(first, first + slot_count))
    else:
        ancillas = tuple(ancilla_wires)
        if len(ancillas) < slot_count:
            raise PUIValidationError(
                f"balanced PUI tree requires a pool of up to {slot_count} clean ancilla wires"
            )
        ancillas = ancillas[:slot_count]

    if any(isinstance(w, bool) or not isinstance(w, int) or w < 0 for w in ancillas):
        raise PUIValidationError("ancilla wire indices must be non-negative integers")
    if len(set(ancillas)) != len(ancillas):
        raise PUIValidationError("ancilla wires must be distinct")
    if set(ancillas).intersection(occupied):
        raise PUIValidationError("ancilla wires must be disjoint from address and target wires")

    target_map = plan.unitary_map
    lo, hi = plan.interval
    width = plan.address_width
    address_wires = plan.address_wires
    gates: list[PrimitiveGate] = []
    used_ancillas: set[int] = set()
    free_bits: set[int] = set()
    and_compute_count = 0
    target_x_count = 0

    def emit_leaf(address: int, selector: _Selector | None) -> None:
        nonlocal target_x_count
        for target in target_map.get(address, ()):
            if selector is None:
                gates.append(X(target))
            else:
                _emit_conditioned_cx(gates, selector, target)
            target_x_count += 1

    def emit_node(
        node_lo: int,
        node_hi: int,
        depth: int,
        selector: _Selector | None,
    ) -> None:
        nonlocal and_compute_count

        if node_lo == node_hi:
            emit_leaf(node_lo, selector)
            return

        mid = (node_lo + node_hi) // 2
        left_hit = not (mid < lo or node_lo > hi)
        right_hit = not (node_hi < lo or mid + 1 > hi)
        bit_wire = address_wires[depth]

        if selector is None:
            # The root selector is the identity. Its children are represented
            # directly by the next address wire, so no AND ancilla is needed.
            if left_hit and right_hit:
                emit_node(node_lo, mid, depth + 1, _Selector(bit_wire, 0))
                emit_node(mid + 1, node_hi, depth + 1, _Selector(bit_wire, 1))
            elif left_hit:
                if plan.kind == "unrestricted":
                    # Algorithm 2's unrestricted left-only case drops this bit.
                    free_bits.add(depth)
                    emit_node(node_lo, mid, depth + 1, None)
                else:
                    emit_node(node_lo, mid, depth + 1, _Selector(bit_wire, 0))
            elif right_hit:
                emit_node(mid + 1, node_hi, depth + 1, _Selector(bit_wire, 1))
            return

        if depth < 1 or depth - 1 >= len(ancillas):
            raise PUIValidationError("internal PUI selector depth exceeds the w-1 ancilla pool")
        ancilla = ancillas[depth - 1]
        used_ancillas.add(ancilla)

        if left_hit and right_hit:
            # Compute the left child selector: parent AND NOT(next address bit).
            # After the left subtree, XOR the parent selector to turn it into
            # parent AND next-bit, visit the right subtree, restore, and uncompute.
            compute = _and_compute(selector, bit_wire, 0, ancilla)
            gates.append(compute)
            and_compute_count += 1
            emit_node(node_lo, mid, depth + 1, _Selector(ancilla, 1))

            _emit_conditioned_cx(gates, selector, ancilla)
            emit_node(mid + 1, node_hi, depth + 1, _Selector(ancilla, 1))
            _emit_conditioned_cx(gates, selector, ancilla)

            gates.append(compute)
        elif left_hit:
            if plan.kind == "unrestricted":
                # This is the only relaxed branch in Algorithm 2: the split bit
                # becomes free, so the same parent selector is reused.
                free_bits.add(depth)
                emit_node(node_lo, mid, depth + 1, selector)
            else:
                compute = _and_compute(selector, bit_wire, 0, ancilla)
                gates.append(compute)
                and_compute_count += 1
                emit_node(node_lo, mid, depth + 1, _Selector(ancilla, 1))
                gates.append(compute)
        elif right_hit:
            compute = _and_compute(selector, bit_wire, 1, ancilla)
            gates.append(compute)
            and_compute_count += 1
            emit_node(mid + 1, node_hi, depth + 1, _Selector(ancilla, 1))
            gates.append(compute)

    emit_node(0, (1 << width) - 1, 0, None)

    return PUITreeCircuit(
        kind=plan.kind,
        address_width=width,
        interval=plan.interval,
        address_wires=plan.address_wires,
        target_wires=targets,
        ancilla_wires=ancillas,
        used_ancilla_wires=tuple(sorted(used_ancillas)),
        gates=tuple(gates),
        and_compute_toffolis=and_compute_count,
        target_x_operations=target_x_count,
        free_bit_positions=tuple(sorted(free_bits)),
        extra_address_map=plan.extra_address_map,
    )
