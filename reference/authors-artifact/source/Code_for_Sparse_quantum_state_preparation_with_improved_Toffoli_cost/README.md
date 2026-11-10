<!--
SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)

SPDX-License-Identifier: Apache-2.0
-->

## Sparse quantum state preparation with improved Toffoli cost

This repository contains implementations of the algorithms in the paper "Sparse quantum state preparation with improved Toffoli cost" together with the code used for creating the figures.

The sparse state preparation circuits are given as [Qualtran](https://github.com/quantumlib/Qualtran) bloqs, where for efficiency we implement the algorithms for finding the circuits in Rust.

An [introductory notebook](examples.ipynb) is provided.

## Installation

Assuming [uv](https://docs.astral.sh/uv/) is installed, the package can be built and installed by calling `uv sync` in the project folder.

### Caution!

One of Qualtrans dependencies is [nbconvert](https://github.com/jupyter/nbconvert). 
At the date of uploading there is a publicly disclosed security vulnerability [CVE](https://github.com/advisories/GHSA-xm59-rqc7-hhvf) for ``nbconvert <= 7.16.6`` that has not yet been [resolved](https://github.com/jupyter/nbconvert/pull/2261). 

We do not use nbconvert in our code and hence manually removed it from ``uv.lock``, so it should not be installed if ``uv sync`` is run.

In case a new lockfile is created (also implicitly, e.g. via ``uv add``) an affected version of nbconvert may be installed and you should be aware of the CVE. 
At the moment the version of nbconvert is not specified in Qualtran, so once a fixed version becomes available, you should be able to upgrade it via ``uv sync --upgrade``.

## Inventory

- [figures/](figures/): Code for creating the data for the figures in the paper.
- [src/](src/): Source code.
    - [src/sparse_state_preparation/](src/sparse_state_preparation/): Python code defining Qualtran Bloqs for sparse state preparation and the necessary sub-Bloqs.
    - [src/isometry_algorithms/](src/isometry_algorithms/): Rust code implementing the computational intensive algorithm for finding the isometry in the sparse state preparation.
    - [src/lib.rs](src/lib.rs): Python-Wrapper for the Rust code. The wrapped code is required for the Bloqs ``IsometryToSubspaceViaBatching`` and consequently ``SparseStatePreparation``.

## Tests

There are tests for both the Rust and Python code.

For running the Python tests simply call `uv run pytest`, and for the Rust tests `cargo test` (assuming the [rust toolchain](https://rust-lang.org/tools/install/) is installed).

## Documentation

Documentation for the Python code can be built via [pdoc](https://pdoc.dev/) by (be aware of the information in [Caution!](#caution))
```
uv add pdoc
uv run pdoc --math sparse_state_preparation
```

## License

The sourcecode in this project is licensed under Apache License, Version 2.0 [LICENSE](LICENSES/Apache-2.0.txt).

The plots in this projects are licensed under Creative Commons Attribution 4.0 International [LICENSE](LICENSES/CC-BY-4.0.txt).


Copyright 2025 German Aerospace Center (DLR)

The direct dependencies have the following licenses:
MIT (pytest, rsmf, pyo3), Apache 2.0 (qualtran, pyo3), Zlib (wide), BSD 2 (rust-numpy)

## Acknowledgements

This work has been funded by the Ministry of Economic Affairs, Labour and Tourism Baden Württemberg through the Competence Center Quantum Computing Baden-Württemberg (KQCBW).