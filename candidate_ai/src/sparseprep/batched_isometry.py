"""Independent Algorithm 1 implementation: Rupprecht-Wölk batched isometry.

Paper basis: Rupprecht & Wölk (2026), Algorithm 1, Section 2, pp. 5--6,
Algorithm 2 for unrestricted PUI (implemented in :mod:`pui_tree`).

This module operates on an ordered classical tableau of distinct computational-
basis strings. It emits a reversible basis-permutation circuit G such that
G|C_i> = |f(i)>_s |0>_r. The state-preparation isometry is G^dagger.

Scope and accounting:
* The tableau-finding algorithm is implemented for computational-basis input.
* PUI blocks use the independently validated Phase 5 tree emitter.
* PUI selector ANDs are emitted coherently (compute/uncompute); the paper's
  measurement-based AND-adjoint accounting is reported separately.
* The final one-hot collision cleanup follows Algorithm 1's fresh-prefix plus
  ell-controlled-X pattern. It is generalized to any one-hot residual row
  created by the restricted final PUI; the paper's single-collision Eq. (3)
  allowance is only reported when at most one repair is required.
* The final exceptional MCX is kept symbolic in the IR and its AND-ladder
  resource estimate is reported separately.
* Dense-state preparation and Algorithm 3 sign/marker handling are excluded.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2, sqrt
from typing import Literal

from .gates import (
    CMX,
    MCX,
    NegativeControlToffoli,
    PrimitiveGate,
    SWAP,
    Toffoli,
    invert_sequence,
)
from .model import SparseStateProblem, largest_power_of_two_at_most
from .pui import PUIPlan, build_pui_plan, mcx_ladder_cost
from .pui_tree import PUITreeCircuit, compile_pui_tree
from .simulator import apply_gate, simulate_basis_state


class BatchedIsometryError(RuntimeError):
    """Raised when an Algorithm 1 tableau invariant cannot be maintained."""


@dataclass(frozen=True, slots=True)
class BatchBuildStep:
    row_id: int
    label: int
    batch_position: int
    method: Literal["direct", "swap", "toffoli"]
    state_before: str
    state_after_activation: str
    swap_wires: tuple[int, int] | None
    toffoli_controls: tuple[int, int] | None
    toffoli_control_values: tuple[int, int] | None
    cmx_control: int
    cmx_targets: tuple[int, ...]
    state_after: str


@dataclass(frozen=True, slots=True)
class PUIBatchEvent:
    kind: Literal["restricted", "unrestricted"]
    interval: tuple[int, int]
    row_ids: tuple[int, ...]
    extra_address_map: tuple[tuple[int, int], ...]
    paper_accounted_toffolis: int
    coherent_toffolis: int
    clean_ancillas_used: int
    cx_count: int
    x_count: int
    gate_count: int


@dataclass(frozen=True, slots=True)
class BatchedIsometryResources:
    batch_size_limit: int
    number_of_batches: int
    batch_fallback_toffolis: int
    batch_swap_count: int
    batch_cmx_count: int
    pui_paper_accounted_toffolis: int
    pui_coherent_toffolis: int
    correction_mcx_count: int
    correction_mcx_paper_toffolis: int
    correction_mcx_coherent_toffolis: int
    total_paper_accounted_toffolis: int
    total_coherent_toffolis: int
    clean_ancilla_pool_size: int
    max_clean_ancillas_used: int
    equation_3_extra_upper_bound: float | None
    equation_1_isometry_upper_bound: float | None
    equation_1_bound_note: str
    final_collision_repair_count: int
    equation_3_bound_applicable: bool


@dataclass(frozen=True, slots=True)
class BatchedIsometryResult:
    n: int
    s: int
    ell: int
    residual_width: int
    batch_size_limit: int
    initial_tableau: tuple[str, ...]
    final_tableau: tuple[str, ...]
    # f[row_id] is the final ell-bit compact label.
    f: tuple[int, ...]
    batch_steps: tuple[BatchBuildStep, ...]
    pui_events: tuple[PUIBatchEvent, ...]
    forward_gates: tuple[PrimitiveGate, ...]
    inverse_gates: tuple[PrimitiveGate, ...]
    resources: BatchedIsometryResources
    ancilla_wires: tuple[int, ...]
    correction_labels: tuple[int, ...]
    correction_row_ids: tuple[int, ...]

    def map_row_to_subspace(self, row_id: int) -> str:
        if isinstance(row_id, bool) or not isinstance(row_id, int):
            raise TypeError("row_id must be an integer")
        if not 0 <= row_id < self.s:
            raise IndexError(f"row_id must be in [0, {self.s})")
        return format(self.f[row_id], f"0{self.ell}b") if self.ell else ""

    def verify(self) -> None:
        """Verify injectivity, zero residuals, forward action and inverse action."""
        assert len(self.f) == self.s
        assert len(set(self.f)) == self.s, "f must be injective"
        assert all(0 <= x < (1 << self.ell) for x in self.f)
        assert len(set(self.final_tableau)) == self.s
        assert all(row[self.ell:] == "0" * self.residual_width for row in self.final_tableau)
        ancilla_count = len(self.ancilla_wires)
        for row_id, (initial, final) in enumerate(zip(self.initial_tableau, self.final_tableau)):
            extended_in = initial + "0" * ancilla_count
            extended_out = simulate_basis_state(extended_in, self.forward_gates)
            assert extended_out[: self.n] == final, row_id
            assert extended_out[self.n :] == "0" * ancilla_count, row_id
            inverse_out = simulate_basis_state(final + "0" * ancilla_count, self.inverse_gates)
            assert inverse_out[: self.n] == initial, row_id
            assert inverse_out[self.n :] == "0" * ancilla_count, row_id
            final_label = int(final[: self.ell], 2) if self.ell else 0
            assert final_label == self.f[row_id], row_id


def _one_hot(width: int, position: int) -> str:
    if not 0 <= position < width:
        raise BatchedIsometryError(f"one-hot position {position} outside residual width {width}")
    return "".join("1" if j == position else "0" for j in range(width))


def _cmx_to_target(state: str, desired: str, control: int) -> CMX | None:
    if state[control] != "1" or desired[control] != "1":
        raise BatchedIsometryError("CMX control must be 1 in both current and desired row")
    targets = tuple(i for i, (a, b) in enumerate(zip(state, desired)) if i != control and a != b)
    return CMX(control, targets) if targets else None


def _apply_tableau_gate(tableau: list[str], gate: PrimitiveGate) -> None:
    for i, row in enumerate(tableau):
        tableau[i] = apply_gate(row, gate)
    if len(set(tableau)) != len(tableau):
        raise BatchedIsometryError(f"reversible gate {gate!r} collapsed two tableau rows")


def _compile_and_apply_pui(
    tableau: list[str],
    *,
    n: int,
    ell: int,
    row_ids: tuple[int, ...],
    batch_labels: tuple[int, ...],
    kind: Literal["restricted", "unrestricted"],
    ancilla_wires: tuple[int, ...],
) -> tuple[PUIPlan, PUITreeCircuit, tuple[PrimitiveGate, ...]]:
    if not row_ids:
        raise BatchedIsometryError("cannot compile an empty batch PUI")
    lo, hi = batch_labels[0], batch_labels[-1]
    if len(batch_labels) != len(row_ids) or tuple(range(lo, hi + 1)) != batch_labels:
        raise BatchedIsometryError("batch labels must be a contiguous increasing interval")
    target_by_address = {
        label: (ell + position,) for position, label in enumerate(batch_labels)
    }
    plan = build_pui_plan(
        address_width=ell,
        interval=(lo, hi),
        target_by_address=target_by_address,
        address_wires=tuple(range(ell)),
        kind=kind,
    )
    tree = compile_pui_tree(plan, ancilla_wires=ancilla_wires)
    ancilla_count = len(ancilla_wires)
    zeros = "0" * ancilla_count
    for row_index, row in enumerate(tableau):
        extended = row + zeros
        transformed = simulate_basis_state(extended, tree.gates)
        if transformed[n:] != zeros:
            raise BatchedIsometryError(
                f"PUI left non-zero clean ancilla state on tableau row {row_index}: {transformed[n:]}"
            )
        tableau[row_index] = transformed[:n]
    if len(set(tableau)) != len(tableau):
        raise BatchedIsometryError("PUI collapsed two tableau rows")
    # The same clean ancilla pool is reused by every PUI block; the tree emitter
    # returns it to |0> after each block.
    return plan, tree, tree.gates


def _fresh_prefix(tableau: list[str], ell: int) -> int:
    # Algorithm 1 only forbids a prefix already paired with an all-zero
    # residual register. A prefix paired with a distinct one-hot residual
    # pattern is still a valid fresh |k'>|0> destination.
    residual_width = len(tableau[0]) - ell
    zero_residual = "0" * residual_width
    occupied = {
        int(row[:ell], 2) if ell else 0
        for row in tableau
        if row[ell:] == zero_residual
    }
    for label in range(1 << ell):
        if label not in occupied:
            return label
    raise BatchedIsometryError("no unused compact label exists for final collision repair")


def _equation_1_upper_bound(s: int, ell: int, m: int) -> tuple[float | None, str]:
    padded = 1 << ell
    if m <= 0:
        return None, "not applicable: no residual batch width"
    if m == 1:
        return None, "not evaluated: Eq. (1) is not a useful upper bound in the m=1 boundary case"
    if m > padded:
        return None, "not evaluated: paper expression requires m <= 2^ell"
    value = ceil(s / m) * (2 * m + 0.5 * log2(padded / m) - 3.0)
    value += log2((padded ** 1.5) / (2.0 * sqrt(m)))
    return value, "paper Eq. (1), real-valued analytical upper-bound expression"


def run_batched_isometry(problem: SparseStateProblem) -> BatchedIsometryResult:
    """Construct the paper's Algorithm 1 circuit G and its inverse G^dagger.

    The input tableau is transformed in-place after every emitted operation,
    including unrestricted-PUI side effects. Batch rows are always maintained
    in the form ``|k-b+j>_s |e_j>_r`` before a PUI flush.

    ``m`` is the largest power of two no greater than ``n-ell``. The actual
    batch may be smaller in the final partial batch. The single-row boundary
    is normalized to the all-zero basis state; zero residual width uses identity.
    """
    if not isinstance(problem, SparseStateProblem):
        raise TypeError("problem must be a SparseStateProblem")

    n, s, ell = problem.n, problem.s, problem.ell
    residual_width = n - ell
    initial = tuple(problem.support)
    if s == 1:
        # With ell=0, the subspace register is empty. Normalize the sole
        # computational-basis vector to |0...0> using X gates on its 1 bits.
        from .gates import X
        forward = tuple(X(wire) for wire, bit in enumerate(initial[0]) if bit == "1")
        final = ("0" * n,)
        f = (0,)
        empty = BatchedIsometryResources(
            batch_size_limit=0, number_of_batches=0, batch_fallback_toffolis=0,
            batch_swap_count=0, batch_cmx_count=0, pui_paper_accounted_toffolis=0,
            pui_coherent_toffolis=0, correction_mcx_count=0,
            correction_mcx_paper_toffolis=0, correction_mcx_coherent_toffolis=0,
            total_paper_accounted_toffolis=0, total_coherent_toffolis=0,
            clean_ancilla_pool_size=0, max_clean_ancillas_used=0,
            equation_3_extra_upper_bound=None, equation_1_isometry_upper_bound=None,
            equation_1_bound_note="single-state boundary; only X normalization is required",
            final_collision_repair_count=0, equation_3_bound_applicable=False,
        )
        result = BatchedIsometryResult(
            n, s, ell, residual_width, 0, initial, final, f, (), (),
            forward, invert_sequence(forward), empty, (), (), (),
        )
        result.verify()
        return result

    if residual_width == 0:
        # No residual register exists, so the identity isometry is valid.
        f = tuple(int(row, 2) for row in initial)
        empty = BatchedIsometryResources(
            batch_size_limit=0, number_of_batches=0, batch_fallback_toffolis=0,
            batch_swap_count=0, batch_cmx_count=0, pui_paper_accounted_toffolis=0,
            pui_coherent_toffolis=0, correction_mcx_count=0,
            correction_mcx_paper_toffolis=0, correction_mcx_coherent_toffolis=0,
            total_paper_accounted_toffolis=0, total_coherent_toffolis=0,
            clean_ancilla_pool_size=0, max_clean_ancillas_used=0,
            equation_3_extra_upper_bound=None, equation_1_isometry_upper_bound=None,
            equation_1_bound_note="zero-residual-width boundary; batching formula not applied",
            final_collision_repair_count=0, equation_3_bound_applicable=False,
        )
        result = BatchedIsometryResult(
            n, s, ell, residual_width, 0, initial, initial, f, (), (), (), (),
            empty, (), (), (),
        )
        result.verify()
        return result

    m = largest_power_of_two_at_most(residual_width)
    ancilla_wires = tuple(range(n, n + max(0, ell - 1)))
    tableau = list(initial)
    forward: list[PrimitiveGate] = []
    batch: list[int] = []  # stable row IDs, in ascending compact-label order
    batch_steps: list[BatchBuildStep] = []
    pui_events: list[PUIBatchEvent] = []
    correction_labels: list[int] = []
    correction_row_ids: list[int] = []
    k = 0
    batch_cmx_count = 0
    batch_fallback_toffolis = 0
    batch_swap_count = 0
    correction_mcx_count = 0
    correction_mcx_paper_toffolis = 0
    correction_mcx_coherent_toffolis = 0

    def append_and_apply(gate: PrimitiveGate) -> None:
        forward.append(gate)
        _apply_tableau_gate(tableau, gate)

    def assert_batch_shape() -> None:
        b = len(batch)
        lo = k - b
        for pos, row_id in enumerate(batch):
            current = tableau[row_id]
            expected = format(lo + pos, f"0{ell}b") + _one_hot(residual_width, pos)
            if current != expected:
                raise BatchedIsometryError(
                    f"batch invariant violated for row {row_id}: expected {expected}, got {current}"
                )

    while True:
        b = len(batch)

        # Full batch: flush with unrestricted PUI. All tableau rows, not only
        # batch rows, are updated to preserve extra-address side effects.
        if b == m:
            assert_batch_shape()
            labels = tuple(range(k - b, k))
            before_ids = tuple(batch)
            plan, tree, gates = _compile_and_apply_pui(
                tableau, n=n, ell=ell, row_ids=before_ids,
                batch_labels=labels, kind="unrestricted", ancilla_wires=ancilla_wires,
            )
            forward.extend(gates)
            pui_events.append(PUIBatchEvent(
                kind="unrestricted", interval=(labels[0], labels[-1]), row_ids=before_ids,
                extra_address_map=plan.extra_address_map,
                paper_accounted_toffolis=tree.paper_accounted_toffolis,
                coherent_toffolis=tree.coherent_toffolis,
                clean_ancillas_used=tree.max_clean_ancillas,
                cx_count=tree.cx_count, x_count=tree.x_count, gate_count=len(tree.gates),
            ))
            batch.clear()
            b = 0

        batch_set = set(batch)
        remaining_in_subspace = all(
            row[ell:] == "0" * residual_width
            for row_id, row in enumerate(tableau) if row_id not in batch_set
        )

        # Final partial batch: restricted PUI avoids touching higher address
        # values. The paper includes one exceptional collision repair.
        if remaining_in_subspace:
            if b:
                assert_batch_shape()
                labels = tuple(range(k - b, k))
                before_ids = tuple(batch)
                plan, tree, gates = _compile_and_apply_pui(
                    tableau, n=n, ell=ell, row_ids=before_ids,
                    batch_labels=labels, kind="restricted", ancilla_wires=ancilla_wires,
                )
                forward.extend(gates)
                pui_events.append(PUIBatchEvent(
                    kind="restricted", interval=(labels[0], labels[-1]), row_ids=before_ids,
                    extra_address_map=plan.extra_address_map,
                    paper_accounted_toffolis=tree.paper_accounted_toffolis,
                    coherent_toffolis=tree.coherent_toffolis,
                    clean_ancillas_used=tree.max_clean_ancillas,
                    cx_count=tree.cx_count, x_count=tree.x_count, gate_count=len(tree.gates),
                ))
                batch.clear()

                # The paper gives one exceptional final collision at the last
                # address/one-hot pair. In this independent big-endian tableau
                # implementation, a pre-existing in-subspace row can be hit at
                # another address of the final interval as well. Apply the same
                # fresh-prefix + controlled-X repair to every one-hot residual
                # row left by restricted PUI. All repairs are recorded; Eq. (3)'s
                # single-collision allowance is claimed only for <=1 repair.
                while True:
                    residual_rows = [
                        i for i, row in enumerate(tableau)
                        if row[ell:] != "0" * residual_width
                    ]
                    if not residual_rows:
                        break
                    row_id = residual_rows[0]
                    current = tableau[row_id]
                    residual = current[ell:]
                    if residual.count("1") != 1:
                        raise BatchedIsometryError(
                            "final restricted-PUI left a non-one-hot residual row; "
                            f"collision repair only handles one-hot rows: {row_id}={current}"
                        )
                    residual_position = residual.index("1")
                    control = ell + residual_position
                    new_label = _fresh_prefix(tableau, ell)
                    new_prefix = format(new_label, f"0{ell}b")
                    desired = new_prefix + residual
                    cmx = _cmx_to_target(current, desired, control)
                    if cmx is not None:
                        append_and_apply(cmx)
                        batch_cmx_count += 1
                    mcx = MCX(
                        controls=tuple(range(ell)),
                        target=control,
                        control_values=tuple(int(bit) for bit in new_prefix),
                    )
                    append_and_apply(mcx)
                    expected_repaired = new_prefix + ("0" * residual_width)
                    if tableau[row_id] != expected_repaired:
                        raise BatchedIsometryError(
                            f"final collision repair failed: expected {expected_repaired}, "
                            f"got {tableau[row_id]}"
                        )
                    correction_labels.append(new_label)
                    correction_row_ids.append(row_id)
                    correction_mcx_count += 1
                    ladder = mcx_ladder_cost(ell)
                    correction_mcx_paper_toffolis += ladder.paper_accounted_toffolis
                    correction_mcx_coherent_toffolis += ladder.coherent_toffolis

            # Algorithm 1 reads the final bijection from the transformed
            # tableau. If any non-zero residual remains here, the assumed
            # terminal invariant did not hold; do not silently report success.
            bad = [(i, row) for i, row in enumerate(tableau) if row[ell:] != "0" * residual_width]
            if bad:
                raise BatchedIsometryError(
                    "final restricted-PUI branch left non-zero residual rows: "
                    + ", ".join(f"row {i}={row}" for i, row in bad[:5])
                )
            f = tuple(int(row[:ell], 2) if ell else 0 for row in tableau)
            result = _build_result(
                problem, initial, tableau, f, m, batch_steps, pui_events,
                forward, ancilla_wires, correction_labels, correction_row_ids,
                batch_fallback_toffolis, batch_swap_count, batch_cmx_count,
                correction_mcx_count, correction_mcx_paper_toffolis,
                correction_mcx_coherent_toffolis,
            )
            result.verify()
            return result

        # At least one row outside the batch has a non-zero residual register.
        candidates = [
            row_id for row_id, row in enumerate(tableau)
            if row_id not in batch_set and row[ell:] != "0" * residual_width
        ]
        if not candidates:
            raise BatchedIsometryError("no non-batch residual row, but terminal branch was not selected")
        target_wire = ell + b
        if target_wire >= n:
            raise BatchedIsometryError("batch grew beyond the available residual register")

        # Prefer a row with a 1 in the unused residual suffix; a SWAP moves it
        # to the next one-hot position. If none exists, use Algorithm 1's
        # distinguishing Toffoli between an already-used residual 1 and its
        # unique batch partner.
        chosen: tuple[int, int] | None = None
        for row_id in candidates:
            row = tableau[row_id]
            usable = [wire for wire in range(target_wire, n) if row[wire] == "1"]
            if usable:
                chosen = (row_id, usable[0])
                break

        method: Literal["direct", "swap", "toffoli"]
        selected_original_state: str
        swap_wires: tuple[int, int] | None = None
        toffoli_controls: tuple[int, int] | None = None
        toffoli_values: tuple[int, int] | None = None
        row_id: int

        if chosen is not None:
            row_id, residual_one_wire = chosen
            selected_original_state = tableau[row_id]
            if residual_one_wire == target_wire:
                method = "direct"
            else:
                method = "swap"
                swap_wires = (residual_one_wire, target_wire)
                append_and_apply(SWAP(*swap_wires))
                batch_swap_count += 1
        else:
            row_id = candidates[0]
            selected_original_state = tableau[row_id]
            method = "toffoli"
            row = tableau[row_id]
            used_ones = [wire for wire in range(ell, target_wire) if row[wire] == "1"]
            if not used_ones:
                raise BatchedIsometryError(
                    f"row {row_id} has residual support but no used one-hot position for fallback Toffoli"
                )
            u = used_ones[0]
            partner_position = u - ell
            if partner_position >= b:
                raise BatchedIsometryError("fallback Toffoli has no already-batched partner")
            partner_row_id = batch[partner_position]
            partner = tableau[partner_row_id]
            differing = [wire for wire in range(n) if row[wire] != partner[wire]]
            if not differing:
                raise BatchedIsometryError("selected row unexpectedly equals its batch partner")
            v = differing[0]
            selected_value = int(row[v])
            toffoli_controls = (u, v)
            toffoli_values = (1, selected_value)
            if toffoli_values == (1, 1):
                fallback_gate: PrimitiveGate = Toffoli(u, v, target_wire)
            else:
                fallback_gate = NegativeControlToffoli(
                    controls=(u, v), target=target_wire,
                    control_values=toffoli_values,
                )
            append_and_apply(fallback_gate)
            batch_fallback_toffolis += 1

        # Map the selected row to |k>|e_b> with a multi-target CX controlled
        # by its next one-hot residual bit. Existing batch rows have 0 there,
        # so this operation leaves them untouched.
        state_before_cmx = tableau[row_id]
        desired = format(k, f"0{ell}b") + _one_hot(residual_width, b)
        if state_before_cmx[target_wire] != "1":
            raise BatchedIsometryError(
                f"row {row_id} was not activated on next residual wire {target_wire}"
            )
        cmx = _cmx_to_target(state_before_cmx, desired, target_wire)
        cmx_targets: tuple[int, ...] = ()
        if cmx is not None:
            cmx_targets = cmx.targets
            append_and_apply(cmx)
            batch_cmx_count += 1
        state_after = tableau[row_id]
        if state_after != desired:
            raise BatchedIsometryError(
                f"batch CMX failed for row {row_id}: expected {desired}, got {state_after}"
            )
        batch_steps.append(BatchBuildStep(
            row_id=row_id, label=k, batch_position=b, method=method,
            state_before=selected_original_state,
            state_after_activation=state_before_cmx,
            swap_wires=swap_wires, toffoli_controls=toffoli_controls,
            toffoli_control_values=toffoli_values, cmx_control=target_wire,
            cmx_targets=cmx_targets, state_after=state_after,
        ))
        batch.append(row_id)
        k += 1
        assert_batch_shape()


def _build_result(
    problem: SparseStateProblem,
    initial: tuple[str, ...],
    tableau: list[str],
    f: tuple[int, ...],
    m: int,
    batch_steps: list[BatchBuildStep],
    pui_events: list[PUIBatchEvent],
    forward: list[PrimitiveGate],
    ancilla_wires: tuple[int, ...],
    correction_labels: list[int],
    correction_row_ids: list[int],
    batch_fallback_toffolis: int,
    batch_swap_count: int,
    batch_cmx_count: int,
    correction_mcx_count: int,
    correction_mcx_paper_toffolis: int,
    correction_mcx_coherent_toffolis: int,
) -> BatchedIsometryResult:
    n, s, ell = problem.n, problem.s, problem.ell
    pui_paper = sum(event.paper_accounted_toffolis for event in pui_events)
    pui_coherent = sum(event.coherent_toffolis for event in pui_events)
    batches = len(pui_events)  # Each PUI event flushes exactly one batch.
    equation_3_bound_applicable = correction_mcx_count <= 1
    eq3 = None
    if m > 0 and equation_3_bound_applicable:
        eq3 = s - ceil(s / m) + log2((1 << ell) / 2)
    if equation_3_bound_applicable:
        eq1, eq1_note = _equation_1_upper_bound(s, ell, m)
    else:
        eq1 = None
        eq1_note = (
            "not claimed: more than one final one-hot collision repair was required; "
            "the paper's Eq. (3) correction allowance is a single-collision bound"
        )
    total_paper = pui_paper + batch_fallback_toffolis + correction_mcx_paper_toffolis
    total_coherent = pui_coherent + batch_fallback_toffolis + correction_mcx_coherent_toffolis
    resources = BatchedIsometryResources(
        batch_size_limit=m,
        number_of_batches=batches,
        batch_fallback_toffolis=batch_fallback_toffolis,
        batch_swap_count=batch_swap_count,
        batch_cmx_count=batch_cmx_count,
        pui_paper_accounted_toffolis=pui_paper,
        pui_coherent_toffolis=pui_coherent,
        correction_mcx_count=correction_mcx_count,
        correction_mcx_paper_toffolis=correction_mcx_paper_toffolis,
        correction_mcx_coherent_toffolis=correction_mcx_coherent_toffolis,
        total_paper_accounted_toffolis=total_paper,
        total_coherent_toffolis=total_coherent,
        clean_ancilla_pool_size=len(ancilla_wires),
        max_clean_ancillas_used=max(
            max((event.clean_ancillas_used for event in pui_events), default=0),
            mcx_ladder_cost(ell).clean_ancillas if correction_mcx_count else 0,
        ),
        equation_3_extra_upper_bound=eq3,
        equation_1_isometry_upper_bound=eq1,
        equation_1_bound_note=eq1_note,
        final_collision_repair_count=correction_mcx_count,
        equation_3_bound_applicable=equation_3_bound_applicable,
    )
    gates = tuple(forward)
    return BatchedIsometryResult(
        n=n, s=s, ell=ell, residual_width=n - ell, batch_size_limit=m,
        initial_tableau=initial, final_tableau=tuple(tableau), f=f,
        batch_steps=tuple(batch_steps), pui_events=tuple(pui_events),
        forward_gates=gates, inverse_gates=invert_sequence(gates),
        resources=resources, ancilla_wires=ancilla_wires,
        correction_labels=tuple(correction_labels),
        correction_row_ids=tuple(correction_row_ids),
    )
