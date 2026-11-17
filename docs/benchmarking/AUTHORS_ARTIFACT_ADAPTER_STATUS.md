# Authors' Official Artifact and Adapter Status

**Paper:** Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum (2026), DOI `10.22331/q-2026-09-10-2208`.

**Artifact:** Zenodo record 18234600, `reference/authors-artifact/official-artifact.zip`.

- Expected MD5: `c58634ba415b4e3fb729648460f32ad7`
- Verified local MD5: `c58634ba415b4e3fb729648460f32ad7`
- Local SHA-256: `4aa9ccdf5a4ae25f389e93dc8c9d7cada71f404f6a64d243038f374da81f6456`
- Official ABI3 module: loads from the extracted artifact.
- Official build: `uv run --frozen ...` built the package successfully; importing `sparse_state_preparation._isometry_algorithms` in that environment passed. `python -m maturin --version` is unavailable in the runtime interpreter because Maturin is a build backend, not an installed runtime module. This is not a current build blocker.
- The supplied 30-page audit and named Phase 9.2 evidence branch were not present in the local checkout/object database at initial inspection.

## Adapter contract

`benchmarking/adapters/authors_adapter.py` validates the artifact checksum, loads the compiled Rust extension in isolation, preserves input row order, and returns the reference's row-to-compact-label pairs. It checks that every input row occurs exactly once and compact labels are unique and in range. The reference API does not expose a primitive-gate sequence that can be directly executed by the SIRIUS CPU/GPU simulators, so no gate-by-gate parity is claimed.

The artifact kernel requires `s >= 2` and a positive residual width. Unsupported valid SIRIUS inputs are reported as reference failures with their exact reason. The full official benchmark plan includes `s=1`, so those cases cannot be counted as reference passes.

## Differential evidence and limitations

The expanded fixtures exercise power-of-two and non-power-of-two support sizes, several orders, all-positive and mixed-sign metadata, and mapping injectivity/totality. SIRIUS's basis-row forward/inverse invariants are checked by its own circuit tests; the adapter does not claim the authors' mapping is exactly the same labeling because multiple bijections are valid.

The raw resource counts are exposed under the artifact's stated upper-bound convention. They are not asserted equal to SIRIUS counts when the constructions are not configured identically. Finite small-case counts can differ because pivot choices, sign-column configuration, and algorithm variant affect emitted upper bounds. Such differences remain visible in raw results and need a carefully matched Algorithm 1/Algorithm 3 comparison before a resource-agreement claim.

The official artifact has a counter edge defect in `src/lib.rs`: `BatchZeroingData::num_toffolis()` calculates `changing_size - 2` when `fixed_len == 0`. When `operations` is empty, `next_power_of_two()` is 1 and unsigned subtraction underflows. The adapter retains the raw integer and returns `paper_accounted_toffoli: null` plus `resource_count_status: suspected_usize_underflow` when the value exceeds signed `sys.maxsize`; it does not reinterpret the wrapped result as a Toffoli count.

## Status

- Reference artifact integrity: `PASS`
- Build and extension load: `PASS`
- Mapping invariant fixtures: `PASS`
- Matched smoke reference workload: `PASS` for the one recorded workload; this is not broad paper reproduction.
- Resource equivalence: `NOT_ESTABLISHED`
- Known counter underflow: `FAIL` in the official artifact implementation for affected edge cases; preserved and reported.
- Quantum hardware execution: `NOT_RUN`

Re-run adapter checks with:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest -q tests/test_authors_adapter.py
```
