"""Immutable problem model for sparse computational-basis state preparation.

Bit convention: support strings are big-endian. Character 0 is the most
significant bit and is wire index 0 throughout the gate IR and simulators.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


class ProblemValidationError(ValueError):
    """Raised when a sparse-state problem violates its input contract."""


class UnsupportedConstructionError(ValueError):
    """Raised when a mathematically valid input is outside a construction's domain."""


def bitstring_to_int(bits: str) -> int:
    _validate_bitstring(bits, allow_empty=False)
    return int(bits, 2)


def int_to_bitstring(value: int, width: int) -> str:
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be a positive integer")
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    if value < 0 or value >= (1 << width):
        raise ValueError(f"value must fit in {width} bits")
    return format(value, f"0{width}b")


def _validate_bitstring(bits: str, *, allow_empty: bool) -> None:
    if not isinstance(bits, str):
        raise TypeError("support entries must be strings")
    if not bits and not allow_empty:
        raise ValueError("bitstrings must not be empty")
    if any(ch not in "01" for ch in bits):
        raise ValueError(f"invalid computational-basis bitstring: {bits!r}")


def ceil_log2_positive(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("value must be a positive integer")
    return (value - 1).bit_length()


def largest_power_of_two_at_most(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise UnsupportedConstructionError(
            "a positive residual width is required to define the batch power of two"
        )
    return 1 << (value.bit_length() - 1)


@dataclass(frozen=True, slots=True)
class SparseStateProblem:
    """Immutable description of an ordered sparse support.

    ``coefficients`` are optional normalized amplitudes aligned with support
    order. ``signs`` are independent +/-1 metadata (not absorbed into the
    amplitudes), intended for later real-state sign-correction experiments.
    ``metadata`` is a tuple of string key/value pairs to preserve immutability.
    """

    n: int
    support: tuple[str, ...]
    coefficients: tuple[complex, ...] | None = None
    signs: tuple[int, ...] | None = None
    seed: int | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.n, bool) or not isinstance(self.n, int) or self.n < 1:
            raise ProblemValidationError("n must be a positive integer")

        support = tuple(self.support)
        if not support:
            raise ProblemValidationError("support must contain at least one basis state")
        if len(support) > (1 << self.n):
            raise ProblemValidationError("support size cannot exceed 2**n")
        for bits in support:
            _validate_bitstring(bits, allow_empty=False)
            if len(bits) != self.n:
                raise ProblemValidationError(
                    f"support entry {bits!r} has width {len(bits)}; expected n={self.n}"
                )
        if len(set(support)) != len(support):
            raise ProblemValidationError("support entries must be distinct")
        object.__setattr__(self, "support", support)

        if self.coefficients is not None:
            coeffs = tuple(complex(c) for c in self.coefficients)
            if len(coeffs) != len(support):
                raise ProblemValidationError("coefficients length must equal support size")
            if not all(math.isfinite(c.real) and math.isfinite(c.imag) for c in coeffs):
                raise ProblemValidationError("coefficients must be finite")
            norm_sq = sum(abs(c) ** 2 for c in coeffs)
            if not math.isclose(norm_sq, 1.0, rel_tol=1e-10, abs_tol=1e-12):
                raise ProblemValidationError(
                    f"coefficients must be normalized; squared norm is {norm_sq:.16g}"
                )
            object.__setattr__(self, "coefficients", coeffs)

        if self.signs is not None:
            signs = tuple(self.signs)
            if len(signs) != len(support):
                raise ProblemValidationError("signs length must equal support size")
            if any(isinstance(x, bool) or not isinstance(x, int) or x not in (-1, 1) for x in signs):
                raise ProblemValidationError("each sign must be exactly +1 or -1")
            object.__setattr__(self, "signs", signs)

        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ProblemValidationError("seed must be an integer or None")

        metadata = tuple((str(k), str(v)) for k, v in self.metadata)
        keys = [k for k, _ in metadata]
        if len(set(keys)) != len(keys):
            raise ProblemValidationError("metadata keys must be unique")
        object.__setattr__(self, "metadata", metadata)

    @property
    def s(self) -> int:
        return len(self.support)

    @property
    def ell(self) -> int:
        """ceil(log2(s)), computed exactly with integer arithmetic."""
        return ceil_log2_positive(self.s)

    @property
    def padded_s(self) -> int:
        return 1 << self.ell

    @property
    def residual_width(self) -> int:
        return self.n - self.ell

    @property
    def batch_width(self) -> int:
        """Largest power of two not exceeding residual width.

        This is a construction parameter, not required for merely describing a
        valid problem. For dense/boundary instances with no residual qubits it
        raises instead of silently returning zero.
        """
        if self.s == 1:
            raise UnsupportedConstructionError(
                "s=1 is a trivial one-state case; do not apply the non-trivial batching formula"
            )
        return largest_power_of_two_at_most(self.residual_width)

    @property
    def metadata_dict(self) -> dict[str, str]:
        """Return a defensive dictionary copy of immutable metadata."""
        return dict(self.metadata)

    def support_as_ints(self) -> tuple[int, ...]:
        return tuple(bitstring_to_int(bits) for bits in self.support)


def make_problem(
    n: int,
    support: Iterable[str],
    *,
    coefficients: Iterable[complex] | None = None,
    signs: Iterable[int] | None = None,
    seed: int | None = None,
    metadata: Iterable[tuple[str, str]] = (),
) -> SparseStateProblem:
    """Convenience constructor that freezes iterable inputs into tuples."""
    return SparseStateProblem(
        n=n,
        support=tuple(support),
        coefficients=None if coefficients is None else tuple(coefficients),
        signs=None if signs is None else tuple(signs),
        seed=seed,
        metadata=tuple(metadata),
    )
