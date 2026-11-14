"""Malvetti et al. baseline isometry used by Rupprecht & Wölk (2026).

This is the *isometry-finding* baseline from Section 2 of
"Sparse quantum state preparation with improved Toffoli cost" (Rupprecht &
Wölk, Quantum 10, 2208, 2026), recalling the method of Malvetti et al.
The input is a tableau of s target basis states on n qubits. The first
ell=ceil(log2(s)) wires are the subspace register; the remaining wires are
the non-subspace register.

The generated forward circuit G maps each input row |C_i> to
|f(i)>|0...0>. The preparation isometry is G^dagger. All operations are
classical reversible basis permutations (CX and multi-controlled X), so
complex amplitudes are preserved and need not be simulated here.

The paper's resource model counts each ell-controlled X as ell-1 Toffolis
using an AND-ladder and ell-2 clean ancillas. The worst-case isometry count
is s(ell-1); dense-state-preparation cost is separate and is NOT included.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .gates import CX, MCX, X, Gate, invert_sequence
from .model import SparseStateProblem
from .simulator import apply_gate, simulate_basis_state


@dataclass(frozen=True, slots=True)
class MalvettiStep:
    """Auditable record for one target-tableau row."""

    row_id: int
    kind: Literal["already_in_subspace", "mapped_to_subspace", "single_state"]
    state_before: str
    residual_control_wire: int | None
    chosen_label: int
    chosen_label_bits: str
    cx_targets: tuple[int, ...]
    state_after_cx: str | None
    state_after: str
    zeroing_gate: MCX | None


@dataclass(frozen=True, slots=True)
class MalvettiResourceReport:
    """Paper-aligned isometry resource accounting.

    ``cx_count`` is the number of explicit Clifford CX gates in the emitted
    basis-permutation circuit. ``zeroing_mcx_count`` counts symbolic
    ell-controlled-X operations. ``toffoli_count`` is the AND-ladder cost
    stated for those operations by Rupprecht & Wölk's Malvetti baseline.
    These metrics exclude dense-state preparation.
    """

    cx_count: int
    zeroing_mcx_count: int
    toffolis_per_zeroing_mcx: int
    toffoli_count: int
    worst_case_toffoli_count: int
    clean_ancillas: int


@dataclass(frozen=True, slots=True)
class MalvettiBaselineResult:
    """Result of the row-by-row Malvetti isometry-finding algorithm."""

    n: int
    s: int
    ell: int
    residual_width: int
    initial_tableau: tuple[str, ...]
    final_tableau: tuple[str, ...]
    # f[i] is the subspace address assigned to original row i.
    f: tuple[int, ...]
    steps: tuple[MalvettiStep, ...]
    # Forward G: target basis state -> compact subspace basis state.
    forward_gates: tuple[Gate, ...]
    # Inverse G^dagger: compact subspace basis state -> target basis state.
    inverse_gates: tuple[Gate, ...]
    resources: MalvettiResourceReport

    def map_row_to_subspace(self, row_id: int) -> str:
        if isinstance(row_id, bool) or not isinstance(row_id, int):
            raise TypeError("row_id must be an integer")
        if not 0 <= row_id < self.s:
            raise IndexError(f"row_id must be in [0, {self.s})")
        return format(self.f[row_id], f"0{self.ell}b") if self.ell else ""

    def verify(self) -> None:
        """Raise AssertionError if the recorded map/circuit violates its contract."""
        assert len(self.f) == self.s
        assert len(set(self.f)) == self.s, "f must be injective on the s input rows"
        assert all(0 <= label < (1 << self.ell) for label in self.f)
        assert len(set(self.final_tableau)) == self.s
        assert all(row[self.ell:] == "0" * self.residual_width for row in self.final_tableau)
        for row_id, (initial, final) in enumerate(zip(self.initial_tableau, self.final_tableau)):
            assert simulate_basis_state(initial, self.forward_gates) == final, row_id
            assert simulate_basis_state(final, self.inverse_gates) == initial, row_id
            final_label = int(final[:self.ell], 2) if self.ell else 0
            assert final_label == self.f[row_id], row_id


def _label_bits(label: int, ell: int) -> str:
    return format(label, f"0{ell}b") if ell else ""


def _subspace_labels(tableau: list[str], ell: int, residual_width: int) -> set[int]:
    """Return labels occupied by rows currently in the subspace."""
    labels: set[int] = set()
    zero = "0" * residual_width
    for row in tableau:
        if row[ell:] == zero:
            labels.add(int(row[:ell], 2) if ell else 0)
    return labels


def _choose_label(current_prefix: str, used: set[int], ell: int) -> int:
    """Prefer the row's existing prefix; otherwise choose the lowest free label.

    The paper requires an unused label but does not prescribe a unique
    selection order. This deterministic policy is an implementation choice;
    it can yield a different valid bijection from the one drawn in Figure 3.
    """
    current = int(current_prefix, 2) if ell else 0
    if current not in used:
        return current
    for label in range(1 << ell):
        if label not in used:
            return label
    raise RuntimeError("no unused subspace label remains; tableau invariant broken")


def run_malvetti_baseline(problem: SparseStateProblem) -> MalvettiBaselineResult:
    """Construct Malvetti's sequential isometry G and its inverse G^dagger.

    The subspace register is the first ell wires in the project's big-endian
    convention. The residual register is the remaining n-ell wires. Each
    chosen residual control bit is the first (leftmost) 1 in the current row.
    All emitted gates are applied to the entire tableau, not just the selected
    row; this is essential because a multi-target CX and a controlled-X can
    change later rows before their turn is processed.
    """
    if not isinstance(problem, SparseStateProblem):
        raise TypeError("problem must be a SparseStateProblem")

    n = problem.n
    s = problem.s
    ell = problem.ell
    residual_width = n - ell
    initial = tuple(problem.support)

    # The one-row, zero-subspace-bit boundary is a direct bitwise X map.
    # No ell-controlled-X is needed when ell=0.
    if ell == 0:
        state = initial[0]
        gates: tuple[Gate, ...] = tuple(X(i) for i, bit in enumerate(state) if bit == "1")
        final = tuple(simulate_basis_state(row, gates) for row in initial)
        step = MalvettiStep(
            row_id=0,
            kind="single_state",
            state_before=state,
            residual_control_wire=None,
            chosen_label=0,
            chosen_label_bits="",
            cx_targets=(),
            state_after_cx=None,
            state_after=final[0],
            zeroing_gate=None,
        )
        report = MalvettiResourceReport(0, 0, 0, 0, 0, 0)
        result = MalvettiBaselineResult(
            n, s, ell, residual_width, initial, final, (0,), (step,),
            gates, invert_sequence(gates), report,
        )
        result.verify()
        return result

    tableau = list(initial)
    forward: list[Gate] = []
    steps: list[MalvettiStep] = []
    mapping: list[int | None] = [None] * s
    cx_count = 0
    zeroing_mcx_count = 0
    zero_residual = "0" * residual_width

    for row_id in range(s):
        state_before = tableau[row_id]
        prefix = state_before[:ell]
        residual = state_before[ell:]

        if residual == zero_residual:
            label = int(prefix, 2)
            if label in {x for x in mapping if x is not None}:
                raise RuntimeError("two distinct rows occupy the same subspace label")
            mapping[row_id] = label
            steps.append(MalvettiStep(
                row_id=row_id,
                kind="already_in_subspace",
                state_before=state_before,
                residual_control_wire=None,
                chosen_label=label,
                chosen_label_bits=prefix,
                cx_targets=(),
                state_after_cx=None,
                state_after=state_before,
                zeroing_gate=None,
            ))
            continue

        # A non-zero residual row has at least one 1. Select the leftmost one.
        residual_one = residual.index("1")
        control_wire = ell + residual_one

        # Existing subspace rows and all previously assigned f-values are
        # unavailable. If this row's current prefix is free, retaining it
        # avoids changing that part of the selected row. The choice among
        # other free labels is not unique in the paper; use a deterministic
        # lowest-free-label fallback.
        used = _subspace_labels(tableau, ell, residual_width)
        used.update(x for x in mapping if x is not None)
        label = _choose_label(prefix, used, ell)
        label_bits = _label_bits(label, ell)
        one_hot = "".join("1" if i == residual_one else "0" for i in range(residual_width))
        desired = label_bits + one_hot

        # One multi-target CX, represented as its exact CX decomposition.
        # Its control is the chosen non-zero residual bit. For the selected
        # row, the target list makes its state exactly |label>|e_l>.
        cx_targets = tuple(
            wire for wire in range(n)
            if wire != control_wire and state_before[wire] != desired[wire]
        )
        state_after_cx: str | None = state_before
        for target_wire in cx_targets:
            gate = CX(control_wire, target_wire)
            tableau = [apply_gate(row, gate) for row in tableau]
            forward.append(gate)
            cx_count += 1
        state_after_cx = tableau[row_id]
        if state_after_cx != desired:
            raise RuntimeError(
                f"multi-target CX construction failed for row {row_id}: "
                f"expected {desired}, got {state_after_cx}"
            )

        # Zero the lone residual 1 using an ell-controlled X on the selected
        # address. It is represented symbolically in the gate IR; the paper's
        # AND-ladder resource model is counted separately below.
        zeroing_gate = MCX(
            controls=tuple(range(ell)),
            target=control_wire,
            control_values=tuple(int(bit) for bit in label_bits),
        )
        tableau = [apply_gate(row, zeroing_gate) for row in tableau]
        forward.append(zeroing_gate)
        zeroing_mcx_count += 1

        state_after = tableau[row_id]
        if state_after != label_bits + zero_residual:
            raise RuntimeError(
                f"controlled-X failed to zero row {row_id}: got {state_after}"
            )
        mapping[row_id] = label
        steps.append(MalvettiStep(
            row_id=row_id,
            kind="mapped_to_subspace",
            state_before=state_before,
            residual_control_wire=control_wire,
            chosen_label=label,
            chosen_label_bits=label_bits,
            cx_targets=cx_targets,
            state_after_cx=state_after_cx,
            state_after=state_after,
            zeroing_gate=zeroing_gate,
        ))

        if len(set(tableau)) != s:
            raise RuntimeError("reversible gate sequence unexpectedly merged tableau rows")

    if any(label is None for label in mapping):
        raise RuntimeError("not every input row received a subspace label")

    final_tableau = tuple(tableau)
    f = tuple(int(label) for label in mapping if label is not None)
    per_mcx = max(ell - 1, 0)
    clean_ancillas = max(ell - 2, 0) if zeroing_mcx_count else 0
    resources = MalvettiResourceReport(
        cx_count=cx_count,
        zeroing_mcx_count=zeroing_mcx_count,
        toffolis_per_zeroing_mcx=per_mcx,
        toffoli_count=zeroing_mcx_count * per_mcx,
        worst_case_toffoli_count=s * per_mcx,
        clean_ancillas=clean_ancillas,
    )

    result = MalvettiBaselineResult(
        n=n,
        s=s,
        ell=ell,
        residual_width=residual_width,
        initial_tableau=initial,
        final_tableau=final_tableau,
        f=f,
        steps=tuple(steps),
        forward_gates=tuple(forward),
        inverse_gates=invert_sequence(forward),
        resources=resources,
    )
    result.verify()
    return result
