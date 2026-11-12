"""Deterministic support-family generators for small exhaustive tests and sweeps."""
from __future__ import annotations
import random
from .model import SparseStateProblem, ceil_log2_positive, int_to_bitstring


def random_support(n: int, s: int, seed: int) -> tuple[str, ...]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1: raise ValueError("n must be >= 1")
    if isinstance(s, bool) or not isinstance(s, int) or not 1 <= s <= (1 << n):
        raise ValueError("s must satisfy 1 <= s <= 2**n")
    rng = random.Random(seed)
    chosen: set[int] = set()
    # Rejection sampling avoids materializing the full 2**n state space.
    while len(chosen) < s:
        chosen.add(rng.getrandbits(n))
    return tuple(int_to_bitstring(v, n) for v in sorted(chosen))


def random_problem(n: int, s: int, seed: int) -> SparseStateProblem:
    return SparseStateProblem(n=n, support=random_support(n, s, seed), seed=seed,
                              metadata=(("family", "seeded-random"),))


def support_inside_subspace(n: int, s: int, seed: int = 0) -> SparseStateProblem:
    """Rows with zero residual suffix; useful as a baseline edge family."""
    if n < 1 or s < 1 or s > (1 << n): raise ValueError("require n >= 1 and 1 <= s <= 2**n")
    ell = ceil_log2_positive(s)
    if ell > n: raise ValueError("support does not fit in n bits")
    prefixes = random_support(ell, s, seed) if ell else ("",)
    support = tuple(prefix + "0" * (n - ell) for prefix in prefixes)
    return SparseStateProblem(n=n, support=support, seed=seed,
                              metadata=(("family", "zero-residual-subspace"),))


def support_with_repeated_prefix(n: int, s: int, seed: int = 0) -> SparseStateProblem:
    """Distinct full rows sharing the first ell bits but differing in suffix.

    This is a structural stress family. Whether it triggers a particular
    paper-algorithm branch is established later by the Phase 4/5 trace tests.
    """
    if n < 1 or s < 1: raise ValueError("require n >= 1 and s >= 1")
    ell = ceil_log2_positive(s)
    residual = n - ell
    if residual < 1 or s > (1 << residual):
        raise ValueError("need at least ceil(log2(s)) fixed prefix bits and enough suffix capacity")
    suffixes = random_support(residual, s, seed)
    prefix = "0" * ell
    support = tuple(prefix + suffix for suffix in suffixes)
    return SparseStateProblem(n=n, support=support, seed=seed,
                              metadata=(("family", "repeated-prefix-distinct-suffix"),))


def partial_final_batch_problem(n: int, s: int, batch_size: int, seed: int = 0) -> SparseStateProblem:
    if batch_size < 1: raise ValueError("batch_size must be positive")
    if s % batch_size == 0:
        raise ValueError("s must not be divisible by batch_size for a partial final batch")
    problem = random_problem(n, s, seed)
    return SparseStateProblem(n=n, support=problem.support, seed=seed,
                              metadata=(("family", "partial-final-batch-candidate"),
                                        ("batch_size", str(batch_size)),
                                        ("remainder", str(s % batch_size)),
                                        ("branch_confirmed", "false")))
