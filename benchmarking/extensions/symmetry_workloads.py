"""Deterministic symmetry-structured sparse support workloads (v1)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import random
import sys
from typing import Literal

from sparseprep.model import SparseStateProblem
from sparseprep.support_generators import random_support

Ordering = Literal["lexicographic", "seeded_shuffled"]


@dataclass(frozen=True)
class SymmetryWorkload:
    n: int
    k: int | None
    support_family: str
    seed: int
    ordering: str
    support: tuple[str, ...]
    coefficients: tuple[complex, ...]
    signs: tuple[int, ...]
    canonical_instance_sha256: str
    ordered_input_sha256: str
    geometry: dict


def fixed_hamming_weight_support(n: int, k: int, s: int, seed: int) -> tuple[str, ...]:
    """Sample unique rows from Omega(n,k), then return them lexicographically."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if isinstance(s, bool) or not isinstance(s, int) or s < 1:
        raise ValueError("s must be a positive integer")
    sector_size = math.comb(n, k)
    if s > sector_size:
        raise ValueError(f"s={s} exceeds binomial(n,k)={sector_size}")
    rng = random.Random(seed)
    if sector_size <= sys.maxsize:
        ranks = rng.sample(range(sector_size), s)
    else:
        chosen: set[int] = set()
        while len(chosen) < s:
            chosen.add(rng.randrange(sector_size))
        ranks = list(chosen)

    def unrank_lex(rank: int) -> str:
        positions = []
        start = 0
        remaining = k
        while remaining:
            for candidate in range(start, n - remaining + 1):
                block = math.comb(n - candidate - 1, remaining - 1)
                if rank < block:
                    positions.append(candidate)
                    start = candidate + 1
                    remaining -= 1
                    break
                rank -= block
        selected = set(positions)
        return "".join("1" if i in selected else "0" for i in range(n))

    return tuple(sorted(unrank_lex(rank) for rank in ranks))


def support_geometry(support: tuple[str, ...], n: int, k: int | None) -> dict:
    distances = [sum(a != b for a, b in zip(x, y)) for i, x in enumerate(support) for y in support[i + 1:]]
    prefixes = {str(depth): len({row[:depth] for row in support}) for depth in range(1, n + 1)}
    branching = {}
    for depth in range(n):
        nodes = {row[:depth] for row in support}
        branching[str(depth)] = sum(len({row[depth] for row in support if row[:depth] == node}) for node in nodes)
    density = (len(support) / math.comb(n, k)) if k is not None else None
    return {
        "pairwise_hamming_distance": {
            "count": len(distances),
            "mean": (sum(distances) / len(distances)) if distances else None,
            "min": min(distances) if distances else None,
            "max": max(distances) if distances else None,
        },
        "prefix_occupancy_distinct_prefixes_by_depth": prefixes,
        "prefix_branching_child_count_by_depth": branching,
        "sector_density": density,
        "sector_size": math.comb(n, k) if k is not None else None,
    }


def _amplitudes(s: int, seed: int, family: str) -> tuple[complex, ...]:
    rng = random.Random(seed + 2000)
    if family == "uniform_real_positive":
        return tuple(complex(1 / math.sqrt(s), 0) for _ in range(s))
    magnitudes = [rng.uniform(0.1, 1.0) for _ in range(s)]
    norm = math.sqrt(sum(x * x for x in magnitudes))
    if family == "random_real_positive":
        return tuple(complex(x / norm, 0) for x in magnitudes)
    if family == "random_complex":
        phases = [rng.uniform(-math.pi, math.pi) for _ in range(s)]
        return tuple((m / norm) * complex(math.cos(a), math.sin(a)) for m, a in zip(magnitudes, phases))
    raise ValueError(f"unknown coefficient family {family!r}")


def _signs(s: int, seed: int, profile: str) -> tuple[int, ...]:
    if profile == "all_positive":
        return (1,) * s
    if profile == "random_pm_one":
        rng = random.Random(seed + 3000)
        return tuple(rng.choice((-1, 1)) for _ in range(s))
    raise ValueError(f"unknown sign profile {profile!r}")


def make_symmetry_workload(
    *, n: int, s: int, seed: int, support_family: str,
    ordering: Ordering = "lexicographic", k: int | None = None,
    coefficient_family: str = "random_complex", sign_profile: str = "random_pm_one",
) -> SymmetryWorkload:
    """Create a workload while keeping coefficient/sign labels attached to rows."""
    if support_family == "fixed_hamming_weight":
        if k is None:
            raise ValueError("fixed_hamming_weight requires k")
        canonical_support = fixed_hamming_weight_support(n, k, s, seed)
    elif support_family == "seeded_random":
        if k is not None:
            raise ValueError("random support does not accept k")
        canonical_support = tuple(sorted(random_support(n, s, seed)))
    else:
        raise ValueError(f"unsupported symmetry workload family {support_family!r}")
    canonical_coeffs = _amplitudes(s, seed, coefficient_family)
    canonical_signs = _signs(s, seed, sign_profile)
    attached = {row: (amp, sign) for row, amp, sign in zip(canonical_support, canonical_coeffs, canonical_signs)}
    ordered = list(canonical_support)
    if ordering == "seeded_shuffled":
        random.Random(seed + 9000).shuffle(ordered)
    elif ordering != "lexicographic":
        raise ValueError(f"unsupported ordering {ordering!r}")
    support = tuple(ordered)
    coefficients = tuple(attached[row][0] for row in support)
    signs = tuple(attached[row][1] for row in support)
    canonical_rows = [
        [row, [amp.real, amp.imag], sign]
        for row, (amp, sign) in sorted(attached.items())
    ]
    canonical_digest = sha256(json.dumps({"n": n, "states": canonical_rows}, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    ordered_payload = {"n": n, "support": support, "coefficients": [[a.real, a.imag] for a in coefficients], "signs": signs}
    ordered_digest = sha256(json.dumps(ordered_payload, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    SparseStateProblem(n=n, support=support, coefficients=coefficients, signs=signs)
    return SymmetryWorkload(
        n=n, k=k, support_family=support_family, seed=seed, ordering=ordering,
        support=support, coefficients=coefficients, signs=signs,
        canonical_instance_sha256=canonical_digest, ordered_input_sha256=ordered_digest,
        geometry=support_geometry(canonical_support, n, k),
    )
