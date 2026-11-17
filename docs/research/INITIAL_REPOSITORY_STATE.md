# Initial Repository State

Inspection record before task edits (2026-11-17 local environment).

- Repository root: `/home/ashwathraj/Acadimics/3.Semister3/Projects/Sparse Quantum State Preperation Reduced TOffi COst/SPeed Run`
- Branch: `cleanup/phase9-2-modernization`
- HEAD: `e90449ea7c4751ed125aad88fef8d2f142086dc6`
- Working tree: clean; no staged, unstaged, or untracked changes.
- Recent history: `e90449e` modernization; `ca297e2` Phase 9.1 design; preceding commits implement state preparation, phase synthesis, Algorithm 3, batched isometry, and PUI.
- Local branches: `cleanup/phase9-2-modernization`, `main`, `backup-dates`, `backup-before-rebase`; remotes include `origin/main` and `origin/cleanup/phase9-2-modernization`.
- At the initial snapshot, expected evidence commit `3e6ff6142e2449f2877a7345666c324a9030bc2f` was absent from local Git objects; no local `research/phase9_2/runs/...` directory or phase9_2 raw benchmark package existed. Subsequently, with user-approved read-only fetch, remote branch `research/phase9-2-evidence-20261117-174621` was fetched at that SHA and audited case by case. The evidence tree was not modified. See the historical audit in `FINAL_VALIDATION_REPORT.md`.
- `benchmarking/results` has only its README; no raw JSONL benchmark records are present in this checkout.
- Project uses `pyproject.toml`/setuptools, NumPy runtime dependency, pytest configuration, optional jsonschema/CuPy extras. No repository lockfile or GitHub Actions workflow was found.
- Source is under `candidate_ai/src/sparseprep`; tests are under `candidate_ai/tests` and root `tests`.
- The user-referenced independent 30-page audit is not present by an identifiable filename. In-repository source audit and paper study guide do cover the two noted paper inconsistencies.
- `compute_support_hash()` sorts rows, losing support order. The aggregator buckets by only algorithm, n, s, metric. `_execute_gpu_lane()` applies a separate XOR-one demo rather than SIRIUS gates. Unavailable reference jobs use a zero hash.
- The authors archive MD5 matches the expected `c58634ba415b4e3fb729648460f32ad7`; an extracted ABI3 extension exists. `python -m maturin --version` currently reports no module, though Rust/Cargo and `uv` are installed.
- Initial inspection could not validate historical Phase 9.2 totals. The later read-only audit found 300/300 CPU rows completed and correctness-passed (100 CPU median timers are zero), 90/90 end-to-end statevector checks passed (all CPU timer medians zero), 90/90 GPU basis-row rows with exact CPU/GPU parity, and 150/150 authors comparisons blocked by Maturin executable discovery. These remain historical results from the other source/environment, not validation of the current repaired runner.
