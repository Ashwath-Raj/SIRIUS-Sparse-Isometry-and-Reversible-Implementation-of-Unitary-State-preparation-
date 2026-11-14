"""Exact semantic PUI construction and an MCX clean-ancilla reference compiler.

Paper basis: Rupprecht & Wölk (2026), Section 3, Algorithm 2.

This module deliberately separates two levels:

* ``PUIPlan`` is the exact basis-action plan. Its ``gates`` are explicit
  address-equality-controlled X gates (MCX IR) for every requested address
  and every extra address in the unrestricted PUI map g. This is a transparent
  correctness oracle, not the prefix-sharing optimized tree circuit.
* ``tree`` records the recursive balanced-tree traversal and free-bit choices
  from Algorithm 2. It is used to validate L and g and is the input contract
  for a future optimized shared-prefix emitter.

The direct MCX lowering intentionally does not claim the paper's optimized
repeated-PUI Toffoli bound. ``mcx_ladder_cost`` reports the paper's AND-ladder
accounting separately from a fully coherent Toffoli compute/uncompute circuit.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from collections.abc import Mapping, Iterable
from fractions import Fraction

from .gates import CX, MCX, PrimitiveGate, Toffoli, X, invert_sequence
from .simulator import simulate_basis_state


class PUIValidationError(ValueError):
    """Invalid address interval, gate map, or wire assignment."""


@dataclass(frozen=True, slots=True)
class PUINode:
    """One node in the recursive binary-address traversal.

    ``interval`` is inclusive. ``free_bits`` are address-bit positions whose
    values are ignored by the unrestricted recursion on the path to this node.
    """

    interval: tuple[int, int]
    branch: str
    depth: int
    free_bits: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class PUIPlan:
    """PUI semantics, extra-address map, recursive trace and exact MCX oracle."""

    kind: str
    address_width: int
    interval: tuple[int, int]  # inclusive, as in the paper
    address_wires: tuple[int, ...]
    target_map: tuple[tuple[int, tuple[int, ...]], ...]
    address_to_unitary: tuple[tuple[int, int], ...]
    extra_address_map: tuple[tuple[int, int], ...]
    tree: tuple[PUINode, ...]
    gates: tuple[PrimitiveGate, ...]
    paper_max_ancillas: int

    @property
    def unitary_map(self) -> dict[int, tuple[int, ...]]:
        return dict(self.target_map)

    @property
    def address_map(self) -> dict[int, int]:
        return dict(self.address_to_unitary)

    @property
    def extra_map(self) -> dict[int, int]:
        return dict(self.extra_address_map)

    @property
    def semantic_auxiliary_wires(self) -> int:
        """The MCX oracle uses no ancillas; optimized tree uses <= w-1."""
        return 0

    def inverse_gates(self) -> tuple[PrimitiveGate, ...]:
        return invert_sequence(self.gates)

    def apply(self, state: str) -> str:
        return simulate_basis_state(state, self.gates)


@dataclass(frozen=True, slots=True)
class RepeatedPUIBound:
    """Paper's Equation (7)/(8) repeated-interval upper bound."""

    kind: str
    sparse_size: int
    address_width: int
    address_space: int
    interval_size: int
    interval_count: int
    toffoli_bound: Fraction
    max_ancillas: int


def repeated_pui_cost_bound(
    *, sparse_size: int, address_width: int, interval_size: int, kind: str
) -> RepeatedPUIBound:
    """Return the paper's repeated-interval PUI bound (Equations 7 and 8).

    The paper's partial-size argument assumes ``2**(w-1) < s <= 2**w``;
    ``interval_size`` must be a power of two no larger than the address space.
    ``kind='unrestricted'`` uses Eq. (7), while ``kind='restricted'`` uses Eq. (8).
    This analytical bound is separate from the non-optimized MCX semantic oracle
    emitted by ``build_pui_plan``.
    """
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (sparse_size, address_width, interval_size)):
        raise PUIValidationError("sparse_size, address_width and interval_size must be integers")
    if address_width < 1:
        raise PUIValidationError("address_width must be positive")
    address_space = 1 << address_width
    if not (address_space // 2 < sparse_size <= address_space):
        raise PUIValidationError("paper bound requires 2**(w-1) < sparse_size <= 2**w")
    if interval_size < 1 or interval_size & (interval_size - 1) or interval_size > address_space:
        raise PUIValidationError("interval_size must be a power of two no larger than the address space")
    if kind not in ("restricted", "unrestricted"):
        raise PUIValidationError("kind must be 'restricted' or 'unrestricted'")
    exponent = interval_size.bit_length() - 1
    prefix_width = address_width - exponent
    interval_count = (sparse_size + interval_size - 1) // interval_size
    internal = Fraction(prefix_width, 1) if kind == "restricted" else Fraction(prefix_width, 2)
    per_interval = Fraction(interval_size, 1) + internal - 2
    return RepeatedPUIBound(
        kind=kind,
        sparse_size=sparse_size,
        address_width=address_width,
        address_space=address_space,
        interval_size=interval_size,
        interval_count=interval_count,
        toffoli_bound=interval_count * per_interval,
        max_ancillas=max(0, address_width - 1),
    )


@dataclass(frozen=True, slots=True)
class MCXLadderCost:
    controls: int
    clean_ancillas: int
    compute_toffolis: int
    action_toffolis: int
    measurement_uncompute_toffolis: int
    paper_accounted_toffolis: int
    coherent_uncompute_toffolis: int
    coherent_toffolis: int


def _validate_interval(address_width: int, interval: tuple[int, int]) -> tuple[int, int]:
    if isinstance(address_width, bool) or not isinstance(address_width, int) or address_width < 1:
        raise PUIValidationError("address_width must be a positive integer")
    try:
        lo, hi = interval
    except Exception as exc:
        raise PUIValidationError("interval must be an inclusive (lo, hi) pair") from exc
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (lo, hi)):
        raise PUIValidationError("interval endpoints must be integers")
    limit = 1 << address_width
    if lo < 0 or hi < lo or hi >= limit:
        raise PUIValidationError(f"interval must satisfy 0 <= lo <= hi < {limit}")
    return lo, hi


def _bits(value: int, width: int) -> tuple[int, ...]:
    return tuple(int(c) for c in format(value, f"0{width}b"))


def _normalise_target_map(
    target_by_address: Mapping[int, Iterable[int]],
    interval: tuple[int, int],
    address_wires: tuple[int, ...],
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    lo, hi = interval
    normalized: dict[int, tuple[int, ...]] = {}
    for addr, raw_targets in target_by_address.items():
        if isinstance(addr, bool) or not isinstance(addr, int) or not lo <= addr <= hi:
            raise PUIValidationError("target_by_address keys must lie inside the requested interval")
        targets = tuple(raw_targets)
        if any(isinstance(t, bool) or not isinstance(t, int) or t < 0 for t in targets):
            raise PUIValidationError("target wires must be non-negative integers")
        if len(set(targets)) != len(targets):
            raise PUIValidationError(f"duplicate target wire for address {addr}")
        if set(targets).intersection(address_wires):
            raise PUIValidationError("target wires must be disjoint from address wires")
        normalized[addr] = targets
    # Missing addresses mean U_i = identity, which is useful for sparse target maps.
    for addr in range(lo, hi + 1):
        normalized.setdefault(addr, ())
    return tuple(sorted(normalized.items()))


def _walk_pui_tree(
    address_width: int,
    interval: tuple[int, int],
    unrestricted: bool,
) -> tuple[tuple[PUINode, ...], dict[int, int]]:
    """Implement Algorithm 2's interval-overlap recursion and g construction."""
    lo, hi = interval
    trace: list[PUINode] = []
    extras: dict[int, int] = {}

    def visit(node_lo: int, node_hi: int, free: tuple[int, ...]) -> None:
        depth = address_width - (node_hi - node_lo + 1).bit_length() + 1
        # All recursive nodes are power-of-two intervals.
        if node_lo == node_hi:
            trace.append(PUINode((node_lo, node_hi), "leaf", depth, free))
            if unrestricted and free:
                base = _bits(node_lo, address_width)
                # Every non-empty assignment on ignored/free bits gives an
                # extra address; all fixed positions retain the leaf's bits.
                for assignment in product((0, 1), repeat=len(free)):
                    if not any(assignment):
                        continue
                    candidate = list(base)
                    for bit_index, bit_value in zip(free, assignment):
                        candidate[bit_index] = bit_value
                    address = int("".join(str(b) for b in candidate), 2)
                    if address <= hi:
                        raise PUIValidationError(
                            "Algorithm 2 free-bit expansion produced an address not above r; "
                            "inspect interval/tree invariants"
                        )
                    prior = extras.get(address)
                    if prior is not None and prior != node_lo:
                        raise PUIValidationError("unrestricted PUI g map is not single-valued")
                    extras[address] = node_lo
            return

        mid = (node_lo + node_hi) // 2
        left_hit = not (mid < lo or node_lo > hi)
        right_hit = not (node_hi < lo or mid + 1 > hi)
        bit_index = depth
        if left_hit and right_hit:
            branch = "both"
            trace.append(PUINode((node_lo, node_hi), branch, depth, free))
            visit(node_lo, mid, free)
            visit(mid + 1, node_hi, free)
        elif left_hit:
            if unrestricted:
                branch = "left_free"
                next_free = tuple(sorted((*free, bit_index)))
            else:
                branch = "left_restricted"
                next_free = free
            trace.append(PUINode((node_lo, node_hi), branch, depth, next_free))
            visit(node_lo, mid, next_free)
        elif right_hit:
            branch = "right"
            trace.append(PUINode((node_lo, node_hi), branch, depth, free))
            visit(mid + 1, node_hi, free)
        else:
            return

    visit(0, (1 << address_width) - 1, ())
    return tuple(trace), extras


def build_pui_plan(
    *,
    address_width: int,
    interval: tuple[int, int],
    target_by_address: Mapping[int, Iterable[int]],
    address_wires: Iterable[int] | None = None,
    kind: str = "unrestricted",
) -> PUIPlan:
    """Build an exact PUI plan and an MCX-per-address semantic circuit.

    Args:
        address_width: Number of big-endian address bits.
        interval: Inclusive paper interval ``[l, r]``.
        target_by_address: Address ``i`` -> target wire indices toggled by U_i.
            Only X target operations are modelled in this initial sparse-state
            PUI layer. Missing keys mean identity.
        address_wires: Actual IR wire indices for address bits. Defaults to
            ``range(address_width)``.
        kind: ``"restricted"`` or ``"unrestricted"``.

    For unrestricted PUI, the returned ``extra_address_map`` is the paper's
    ``g: L -> [l,r]`` map. The ``g``-mapped target Xs are also emitted in the
    exact MCX reference circuit.
    """
    lo, hi = _validate_interval(address_width, interval)
    if kind not in ("restricted", "unrestricted"):
        raise PUIValidationError("kind must be 'restricted' or 'unrestricted'")
    wires = tuple(range(address_width)) if address_wires is None else tuple(address_wires)
    if len(wires) != address_width:
        raise PUIValidationError("address_wires length must equal address_width")
    if any(isinstance(w, bool) or not isinstance(w, int) or w < 0 for w in wires):
        raise PUIValidationError("address wire indices must be non-negative integers")
    if len(set(wires)) != len(wires):
        raise PUIValidationError("address wires must be distinct")
    target_map = _normalise_target_map(target_by_address, (lo, hi), wires)

    tree, extras = _walk_pui_tree(address_width, (lo, hi), kind == "unrestricted")
    address_to_unitary = {addr: addr for addr in range(lo, hi + 1)}
    if kind == "unrestricted":
        address_to_unitary.update(extras)

    unitary_map = dict(target_map)
    gates: list[PrimitiveGate] = []
    for actual_address, unitary_address in sorted(address_to_unitary.items()):
        control_values = _bits(actual_address, address_width)
        for target in unitary_map[unitary_address]:
            gates.append(MCX(wires, target, control_values))

    return PUIPlan(
        kind=kind,
        address_width=address_width,
        interval=(lo, hi),
        address_wires=wires,
        target_map=target_map,
        address_to_unitary=tuple(sorted(address_to_unitary.items())),
        extra_address_map=tuple(sorted(extras.items())),
        tree=tree,
        gates=tuple(gates),
        paper_max_ancillas=max(0, address_width - 1),
    )


def mcx_ladder_cost(control_count: int) -> MCXLadderCost:
    """Report the MCX AND-ladder cost under two cleanup accounting models.

    For k>=2, k-2 clean ancillas compute the conjunction of the first k-1
    controls, and one final Toffoli applies the target. The paper's Appendix A
    measurement-based adjoint AND has zero *additional Toffoli* cost. A fully
    coherent unitary uncompute instead reverses the k-2 compute Toffolis.
    """
    if isinstance(control_count, bool) or not isinstance(control_count, int) or control_count < 1:
        raise PUIValidationError("control_count must be a positive integer")
    if control_count == 1:
        return MCXLadderCost(1, 0, 0, 0, 0, 0, 0, 0)
    compute = control_count - 2
    action = 1
    measured_cleanup = 0
    coherent_cleanup = compute
    return MCXLadderCost(
        controls=control_count,
        clean_ancillas=control_count - 2,
        compute_toffolis=compute,
        action_toffolis=action,
        measurement_uncompute_toffolis=measured_cleanup,
        paper_accounted_toffolis=compute + action,
        coherent_uncompute_toffolis=coherent_cleanup,
        coherent_toffolis=compute + action + coherent_cleanup,
    )


def compile_mcx_coherent(
    controls: Iterable[int],
    target: int,
    ancilla_wires: Iterable[int],
    control_values: Iterable[int] | None = None,
) -> tuple[PrimitiveGate, ...]:
    """Compile a multi-controlled X into a clean-ancilla coherent Toffoli ladder.

    This is a fully unitary reference decomposition: all ancillas are returned
    to zero using reverse Toffolis. Negative controls are implemented by X
    conjugation. It is intentionally distinct from the paper's measurement-
    based zero-cost AND adjoint accounting.
    """
    ctrls = tuple(controls)
    anc = tuple(ancilla_wires)
    vals = (1,) * len(ctrls) if control_values is None else tuple(control_values)
    if not ctrls:
        raise PUIValidationError("at least one control is required")
    if len(vals) != len(ctrls) or any(v not in (0, 1) for v in vals):
        raise PUIValidationError("control_values must contain one bit per control")
    if any(isinstance(w, bool) or not isinstance(w, int) or w < 0 for w in (*ctrls, target, *anc)):
        raise PUIValidationError("wire indices must be non-negative integers")
    if len(set((*ctrls, target, *anc))) != len(ctrls) + 1 + len(anc):
        raise PUIValidationError("controls, target and ancillas must all be distinct")
    need = max(0, len(ctrls) - 2)
    if len(anc) < need:
        raise PUIValidationError(f"{len(ctrls)} controls require at least {need} clean ancillas")

    gates: list[PrimitiveGate] = []
    negative = [wire for wire, value in zip(ctrls, vals) if value == 0]
    gates.extend(X(w) for w in negative)

    if len(ctrls) == 1:
        gates.append(CX(ctrls[0], target))
    elif len(ctrls) == 2:
        gates.append(Toffoli(ctrls[0], ctrls[1], target))
    else:
        used = anc[:need]
        compute_gates: list[Toffoli] = [Toffoli(ctrls[0], ctrls[1], used[0])]
        for index in range(2, len(ctrls) - 1):
            compute_gates.append(Toffoli(used[index - 2], ctrls[index], used[index - 1]))
        gates.extend(compute_gates)
        gates.append(Toffoli(used[-1], ctrls[-1], target))
        gates.extend(reversed(compute_gates))

    gates.extend(X(w) for w in reversed(negative))
    return tuple(gates)
