"""Algorithm 3: restricted batched isometry with real-sign fixing.

This module implements the paper's Algorithm 3 at basis-tableau level and
emits a reversible gate IR.  The extra marker is a physical logical wire
(initially |1>); restricted PUI blocks flip both the batch residual target and
that marker.  Input +/- signs are tracked as basis-row phases and are therefore
not represented by an ordinary X/CX gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2, sqrt
from typing import Sequence

from .gates import CX, CMX, MCX, NegativeControlToffoli, PrimitiveGate, SWAP, Toffoli, X, invert_sequence
from .model import SparseStateProblem, largest_power_of_two_at_most
from .pui import build_pui_plan, mcx_ladder_cost
from .pui_tree import compile_pui_tree
from .simulator import apply_gate, simulate_basis_state


class Algorithm3Error(RuntimeError):
    """Algorithm 3 invariant or input failure."""


@dataclass(frozen=True, slots=True)
class Algorithm3Event:
    kind: str
    interval: tuple[int, int] | None = None
    row_ids: tuple[int, ...] = ()
    detail: str = ""
    paper_toffolis: int = 0
    coherent_toffolis: int = 0
    gate_count: int = 0


@dataclass(frozen=True, slots=True)
class Algorithm3Result:
    n: int
    s: int
    ell: int
    residual_width: int
    marker_wire: int
    ancilla_wires: tuple[int, ...]
    signs: tuple[int, ...]
    phases: tuple[int, ...]
    initial_tableau: tuple[str, ...]
    final_tableau: tuple[str, ...]
    final_markers: tuple[int, ...]
    compact_labels: tuple[int, ...]
    forward_gates: tuple[PrimitiveGate, ...]
    inverse_gates: tuple[PrimitiveGate, ...]
    events: tuple[Algorithm3Event, ...]
    batch_size_limit: int
    restricted_pui_count: int
    counter_effect_cx_count: int
    marker_cx_count: int
    batch_swap_count: int
    batch_toffoli_count: int
    batch_cmx_count: int
    paper_accounted_toffolis: int
    coherent_toffolis: int
    max_pui_ancillas: int

    def verify(self) -> None:
        assert len(set(self.compact_labels)) == self.s
        assert all(0 <= x < (1 << self.ell) for x in self.compact_labels)
        assert all(row[self.ell:] == "0" * self.residual_width for row in self.final_tableau)
        assert self.final_markers == (0,) * self.s
        assert self.phases == self.signs
        emitted_toffolis = sum(isinstance(g, (Toffoli, NegativeControlToffoli)) for g in self.forward_gates)
        assert emitted_toffolis == self.coherent_toffolis
        total = self.n + 1 + len(self.ancilla_wires)
        zero_anc = "0" * len(self.ancilla_wires)
        for i, (before, after) in enumerate(zip(self.initial_tableau, self.final_tableau)):
            state_in = before + "1" + zero_anc
            got = simulate_basis_state(state_in, self.forward_gates)
            expected = after + "0" + zero_anc
            assert got == expected, (i, got, expected)
            back = simulate_basis_state(expected, self.inverse_gates)
            assert back == state_in, (i, back, state_in)
        assert total >= self.n + 1


def _one_hot(width: int, pos: int) -> str:
    if not 0 <= pos < width:
        raise Algorithm3Error(f"one-hot position {pos} outside residual width {width}")
    return "".join("1" if i == pos else "0" for i in range(width))


def _apply_all(tableau: list[str], gate: PrimitiveGate) -> None:
    out = [apply_gate(row, gate) for row in tableau]
    if len(set(out)) != len(out):
        raise Algorithm3Error(f"gate {gate!r} collapsed distinct tableau rows")
    tableau[:] = out


def _cmx_to_target(state: str, desired: str, control: int) -> CMX | None:
    if state[control] != "1" or desired[control] != "1":
        raise Algorithm3Error("CMX control must be one in source and destination")
    targets = tuple(i for i, (a, b) in enumerate(zip(state, desired)) if i != control and a != b)
    return CMX(control, targets) if targets else None


def _fresh_prefix(tableau: Sequence[str], ell: int, residual_width: int) -> int:
    zero = "0" * residual_width
    occupied = {int(row[:ell], 2) for row in tableau if row[ell:ell+residual_width] == zero}
    for value in range(1 << ell):
        if value not in occupied:
            return value
    raise Algorithm3Error("no free compact prefix remains")


def run_algorithm3(problem: SparseStateProblem, signs: Sequence[int] | None = None) -> Algorithm3Result:
    """Run Algorithm 3 and emit the forward basis-permutation circuit.

    ``signs`` is aligned with ``problem.support`` and must contain only +/-1.
    The marker wire is n; the clean PUI ancilla pool follows it. The returned
    phase vector is the exact sign multiplier accumulated for each input row.
    """
    if not isinstance(problem, SparseStateProblem):
        raise TypeError("problem must be SparseStateProblem")
    n, s, ell = problem.n, problem.s, problem.ell
    if signs is None:
        signs = problem.signs if problem.signs is not None else (1,) * s
    signs = tuple(signs)
    if len(signs) != s or any(type(x) is not int or x not in (-1, 1) for x in signs):
        raise Algorithm3Error("signs must contain exactly s values, each +1 or -1")
    if s == 1 or n == ell:
        # Degenerate cases have no residual register and no PUI batches.
        initial = tuple(problem.support)
        data_gates = tuple(X(i) for i, bit in enumerate(initial[0]) if bit == "1") if s == 1 else ()
        forward = data_gates + (X(n),)
        final = ("0" * n,) if s == 1 else initial
        result = Algorithm3Result(n, s, ell, n-ell, n, (), signs, signs, initial, final,
            (0,)*s, ((0,) if s == 1 else tuple(int(row, 2) for row in initial)), forward, invert_sequence(forward), (), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        result.verify()
        return result

    r = n - ell
    m = largest_power_of_two_at_most(r)
    marker = n
    ancillas = tuple(range(n + 1, n + 1 + max(0, ell - 1)))
    total_wires = n + 1 + len(ancillas)
    zero_anc = "0" * len(ancillas)
    tableau = [row + "1" for row in problem.support]
    initial = tuple(problem.support)
    forward: list[PrimitiveGate] = []
    events: list[Algorithm3Event] = []
    phases = [1] * s
    batch: list[int] = []
    batch_steps = 0
    swaps = toffolis = cmxs = counter_cx = marker_cx = 0
    pui_count = paper_toffolis = coherent_toffolis = max_anc = 0
    k = 0

    def append(gate: PrimitiveGate) -> None:
        _apply_all(tableau, gate)
        forward.append(gate)

    def assert_batch() -> None:
        b = len(batch)
        lo = k - b
        for pos, row_id in enumerate(batch):
            expected = format(lo + pos, f"0{ell}b") + _one_hot(r, pos) + "1"
            if tableau[row_id] != expected:
                raise Algorithm3Error(f"batch shape row {row_id}: expected {expected}, got {tableau[row_id]}")

    def flush_restricted() -> None:
        nonlocal pui_count, paper_toffolis, coherent_toffolis, max_anc
        b = len(batch)
        if not b:
            return
        assert_batch()
        labels = tuple(range(k-b, k))
        targets = {label: (ell+pos, marker) for pos, label in enumerate(labels)}
        plan = build_pui_plan(address_width=ell, interval=(labels[0], labels[-1]),
            target_by_address=targets, address_wires=tuple(range(ell)), kind="restricted")
        tree = compile_pui_tree(plan, ancilla_wires=ancillas)
        before_markers = [int(row[marker]) for row in tableau]
        before_prefixes = [int(row[:ell], 2) for row in tableau]
        batch_ids_at_flush = tuple(batch)
        for i, row in enumerate(tableau):
            transformed = simulate_basis_state(row + zero_anc, tree.gates)
            if transformed[marker+1:] != zero_anc:
                raise Algorithm3Error(f"restricted PUI left dirty ancilla on row {i}")
            tableau[i] = transformed[:n+1]
            if i in batch_ids_at_flush and before_markers[i] == 1:
                phases[i] *= signs[i]
        if len(set(tableau)) != s:
            raise Algorithm3Error("restricted PUI collapsed tableau rows")
        forward.extend(tree.gates)
        pui_count += 1
        paper_toffolis += tree.paper_accounted_toffolis
        coherent_toffolis += tree.coherent_toffolis
        max_anc = max(max_anc, tree.max_clean_ancillas)
        events.append(Algorithm3Event("restricted_pui_sign_fix", (labels[0], labels[-1]),
            batch_ids_at_flush,
            "flips batch residual target and marker; applies each affected row's +/-1 phase",
            tree.paper_accounted_toffolis, tree.coherent_toffolis, len(tree.gates)))
        batch.clear()

    while True:
        b = len(batch)
        if b == m or k == s:
            flush_restricted()
            if k == s:
                break
            b = 0

        batch_set = set(batch)
        candidates = [i for i, row in enumerate(tableau)
            if i not in batch_set and any(bit == "1" for bit in row[ell:n])]
        target_wire = ell + b

        if candidates:
            row_id = candidates[0]
            row = tableau[row_id]
            usable = [wire for wire in range(target_wire, n) if row[wire] == "1"]
            if usable:
                residual_one = usable[0]
                if residual_one != target_wire:
                    append(SWAP(residual_one, target_wire)); swaps += 1
                    events.append(Algorithm3Event("batch_swap", row_ids=(row_id,), detail=f"swap wires {residual_one},{target_wire}"))
            else:
                used = [wire for wire in range(ell, target_wire) if row[wire] == "1"]
                if not used:
                    raise Algorithm3Error(f"row {row_id} has residual support but no used one-hot bit")
                u = used[0]
                partner_id = batch[u-ell]
                partner = tableau[partner_id]
                diff = [wire for wire in range(n) if row[wire] != partner[wire]]
                if not diff:
                    raise Algorithm3Error("selected row equals its batch partner")
                v = diff[0]
                values = (1, int(row[v]))
                gate = Toffoli(u, v, target_wire) if values == (1,1) else NegativeControlToffoli((u,v), target_wire, values)
                append(gate); toffolis += 1
                events.append(Algorithm3Event("batch_distinguishing_toffoli", row_ids=(row_id, partner_id), detail=f"controls={u},{v}; values={values}"))
            desired = format(k, f"0{ell}b") + _one_hot(r, b) + "1"
            source = tableau[row_id]
            if source[target_wire] != "1":
                raise Algorithm3Error("selected row was not activated on next residual wire")
            gate = _cmx_to_target(source, desired, target_wire)
            if gate is not None:
                append(gate); cmxs += 1
            if tableau[row_id] != desired:
                raise Algorithm3Error(f"batch CMX failed: got {tableau[row_id]}, expected {desired}")
            batch.append(row_id); k += 1; batch_steps += 1
            assert_batch()
            continue

        # Algorithm 3's marker escape: no unbatched row has residual support.
        eligible = [i for i, row in enumerate(tableau) if i not in batch_set and row[marker] == "1"]
        if not eligible:
            raise Algorithm3Error("no marked unbatched row available for marker escape")
        row_id = eligible[0]
        for pos, batch_id in enumerate(batch):
            if tableau[batch_id][marker] == "1":
                control = ell + pos
                if tableau[batch_id][control] != "1":
                    raise Algorithm3Error("counter-effect control not set on batch row")
                append(CX(control, target_wire)); counter_cx += 1
                events.append(Algorithm3Event("counter_effect_cx", row_ids=(batch_id,), detail=f"control={control}, target={target_wire}"))
        append(CX(marker, target_wire)); marker_cx += 1
        events.append(Algorithm3Event("marker_controlled_cx", row_ids=(row_id,), detail=f"control={marker}, target={target_wire}"))
        source = tableau[row_id]
        desired = format(k, f"0{ell}b") + _one_hot(r, b) + "1"
        if source[target_wire] != "1":
            raise Algorithm3Error("marker escape did not activate next residual bit")
        gate = _cmx_to_target(source, desired, target_wire)
        if gate is not None:
            append(gate); cmxs += 1
        if tableau[row_id] != desired:
            raise Algorithm3Error(f"marker escape CMX failed: {tableau[row_id]} != {desired}")
        batch.append(row_id); k += 1; batch_steps += 1
        events.append(Algorithm3Event("marker_escape_batch", row_ids=(row_id,), detail="selected marked row moved into next batch"))
        assert_batch()

    final = tuple(row[:n] for row in tableau)
    markers = tuple(int(row[marker]) for row in tableau)
    labels = tuple(int(row[:ell], 2) for row in tableau)
    result = Algorithm3Result(n, s, ell, r, marker, ancillas, signs, tuple(phases), initial,
        final, markers, labels, tuple(forward), invert_sequence(forward), tuple(events), m,
        pui_count, counter_cx, marker_cx, swaps, toffolis, cmxs, paper_toffolis + toffolis,
        coherent_toffolis + toffolis, max_anc)
    result.verify()
    if tuple(phases) != signs:
        raise Algorithm3Error(f"not all input signs were encoded: got {tuple(phases)}, expected {signs}")
    return result
