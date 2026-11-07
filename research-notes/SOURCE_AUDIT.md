# Phase 1 source audit

## Scientific source hierarchy

1. Published Rupprecht–Wölk PDF: controlling source.
2. User-supplied master Markdown guide: explanatory aid only.
3. User-supplied HTML guide: rendered explanatory aid only.
4. Implementation roadmap: controls project schedule and technical scope, not scientific truth.

## Paper identity

Felix Rupprecht and Sabine Wölk, “Sparse quantum state preparation with improved Toffoli cost”, *Quantum* 10, 2208 (2026), published 10 September 2026. DOI: `10.22331/q-2026-09-10-2208`.

## Known PDF/source issues to preserve for later review

### PDF page 6 — Equation (3) correction-cost prose

The printed prose gives the correction cost as `ceil(log2(s)) + 1` and equates it to `log2(tilde{s}/2)`. Given `tilde{s} = 2^ell` and `ell = ceil(log2(s))`, those expressions are not equal:

- `ceil(log2(s)) + 1 = ell + 1`.
- `log2(tilde{s}/2) = log2(2^(ell-1)) = ell - 1`.

This is an internal arithmetic inconsistency in the supplied PDF text. Do not silently rewrite the source. During later implementation, use the algorithm and surrounding equations/proof to establish the intended correction cost, and record the interpretation with a page/equation reference.

### PDF page 13 — Figure 9 caption algorithm labels

The Figure 9 caption appears to invert the restricted/unrestricted descriptions for Algorithms 1 and 3 relative to the surrounding prose and Algorithm 3 definition. Preserve the printed caption and separately document the interpretation established by cross-checking the main text, pseudocode and Figure 10 caption.

## Zenodo artifact caution

The Zenodo record explicitly says its `uv.lock` was manually edited to avoid installing `nbconvert <= 7.16.6` because of a disclosed vulnerability at upload time. Do not regenerate or modify the official lockfile. Do not run `uv add` in the official artifact environment. Prefer an isolated environment and inspect current dependency advisories before installing.

## Phase 1 retrieval status

The Zenodo record was inspected and the exact artifact filename and MD5 were confirmed from the record. The current agent execution container could not resolve `zenodo.org` (DNS lookup failure), so the ZIP itself was not downloaded or verified in this runtime. The included fetch script is provided for execution from the user's Ubuntu host. This is an unresolved Phase 1 gate, not a successful download claim.
