"""Independent sparse-state preparation research implementation."""
from .model import (
    ProblemValidationError, SparseStateProblem, UnsupportedConstructionError,
    bitstring_to_int, ceil_log2_positive, int_to_bitstring,
    largest_power_of_two_at_most, make_problem,
)
from .gates import (
    CMX, CX, MCX, NegativeControlToffoli, PUIKind, PUIMacro,
    SWAP, Toffoli, X, invert_sequence,
)
from .simulator import apply_gate, simulate_basis_state, simulate_support
from .tableau import Tableau, TableauRow
from .resources import ResourceCounts, count_emitted_resources
from .pui import (
    MCXLadderCost, PUIPlan, PUINode, PUIValidationError, RepeatedPUIBound,
    build_pui_plan, compile_mcx_coherent, mcx_ladder_cost, repeated_pui_cost_bound,
)

__all__ = [
    "ProblemValidationError", "SparseStateProblem", "UnsupportedConstructionError",
    "bitstring_to_int", "ceil_log2_positive", "int_to_bitstring",
    "largest_power_of_two_at_most", "make_problem", "CMX", "CX", "MCX",
    "NegativeControlToffoli", "PUIKind", "PUIMacro", "SWAP", "Toffoli", "X",
    "invert_sequence", "apply_gate", "simulate_basis_state", "simulate_support",
    "Tableau", "TableauRow", "ResourceCounts", "count_emitted_resources",
    "MCXLadderCost", "PUIPlan", "PUINode", "PUIValidationError",
    "RepeatedPUIBound", "build_pui_plan", "compile_mcx_coherent",
    "mcx_ladder_cost", "repeated_pui_cost_bound",
]
