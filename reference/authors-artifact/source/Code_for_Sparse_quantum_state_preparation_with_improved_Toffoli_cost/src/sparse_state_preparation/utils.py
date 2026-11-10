# SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
#
# SPDX-License-Identifier: Apache-2.0

import numpy as np


def random_tableau(
    num_rows: int,
    num_columns: int,
    *,
    seed: int | None = None,
) -> np.ndarray:
    """Generate a random binary matrix with unique rows.

    The function creates a ``num_rows x num_columns`` array of ``bool`` values.
    Each row is a distinct binary vector (i.e. no two rows are identical)

    Parameters
    ----------
    - num_rows: int
        Desired number of rows in the output matrix.
    - num_columns: int
        Desired number of columns (bits) per row.
    - seed: int | None, optional (default: ``None``)
        Seed for the NumPy random generator.  Supplying a fixed integer makes
        the output deterministic, which is handy for reproducible tests.

    Returns
    -------
    - np.ndarray :
        A ``(num_rows, num_columns)`` array of type ``np.bool_`` (alias
        ``bool``).  The rows are guaranteed to be pairwise distinct.
    """

    max_unique_rows = 1 << num_columns
    assert num_columns <= max_unique_rows

    highs = []
    i = 0
    while i < num_columns:
        bits = min(8, num_columns - i)
        highs.append(1 << bits)
        i += 8

    rng = np.random.default_rng(seed)
    seen: dict[tuple[np.uint8, ...], None] = dict()
    # Use dict for remembering order allowing reproducibility

    while len(seen) < num_rows:
        batch_needed = int(np.ceil((num_rows - len(seen)) * 1.1))

        batch_rows = rng.integers(
            low=0,
            high=highs,
            size=(batch_needed, len(highs)),
            dtype=np.uint8,
        )
        seen.update({tuple(row): None for row in batch_rows})

    return np.unpackbits(
        np.array(list(seen.keys())[:num_rows]),
        bitorder="little",
        axis=1,
        count=num_columns,
    ).astype(bool)


def random_signs(num_rows, *, seed: int | None = None) -> np.ndarray:
    """Return a random boolean vector of length ``num_rows``.

    Parameters
    ----------
    - num_rows: int
        Length of the output vector.
    - seed: int | None, optional (default: ``None``)
        Seed for the NumPy random generator.  Supplying a fixed integer makes
        the output deterministic.

    Returns
    -------
    - np.ndarray :
        A one-dimensional array of shape ``(num_rows,)`` with dtype ``np.bool_``.
    """
    rng = np.random.default_rng(seed)
    return rng.random(num_rows) < 0.5
