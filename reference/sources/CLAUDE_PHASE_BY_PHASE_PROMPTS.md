# Claude Phase-by-Phase Prompt Pack

## Sparse Quantum State Preparation with Improved Toffoli Cost

**Purpose:** Drive the AI-assisted candidate implementation in small, reviewable phases. This is not a one-shot build prompt. The user will inspect, download, run and validate each phase before authorizing the next one.

**Controlling sources in the Claude Project Files area:**

1. `q-2026-09-10-2208.pdf` — scientific authority for equations, algorithms, figures, assumptions and claims.
2. `Sparse_Quantum_State_Preparation_Master_Guide.md` and its HTML rendering — explanatory support, not a replacement for the paper.
3. `Sparse_State_Preparation_Implementation_Plan_14_Days.md` — authority for scope, phases, hour budgets, hardware roles, buffers and deliverables.
4. Claude Project Instructions — persistent operating, safety, time and Git rules.

If filenames differ slightly, identify the matching uploaded files by title and content. Never assume an unavailable file was read.

---

# 0. Non-negotiable operating protocol

Paste the prompt for **one phase only**. Claude must finish that phase, report its exit gate and stop. The user will download the handoff, run the specified commands locally, inspect the code and commit history, and provide logs. Do not start the next phase until the user explicitly authorizes it.

## 0.1 Phase gates

For every phase:

1. Read the controlling roadmap section and the exact relevant PDF pages before editing code.
2. Inspect the existing workspace and Git state before making changes.
3. Confirm the phase's hour budget from the roadmap. Track actual focused time in `WORKLOG.md`; do not invent elapsed time.
4. Implement only the scope of the requested phase. Do not quietly pull later phases forward.
5. Add tests alongside each implementation slice. Prefer multiple small, coherent, reviewable changes.
6. Run the tests that are actually available in the current environment. Clearly distinguish tests run by Claude from commands the user must run on their RTX 3050, Kaggle, workstation or DGX-1.
7. Inspect `git diff --check`, staged changes and repository status. Do not stage unrelated files, generated caches, credentials, virtual environments, large datasets or user files.
8. Make local Git commits for completed, tested milestones. Multiple meaningful commits per phase are encouraged; meaningless commits created only to inflate the count are prohibited.
9. Create a phase handoff that preserves the code **and its Git history**. Prefer a verified Git bundle plus a source archive. If Git/bundle creation is unavailable, state that clearly and provide patches; never claim history was preserved when it was not.
10. Report the phase's exit-gate status, tests, known gaps, actual time used, remaining roadmap budget, local commit hashes and downloadable handoff files.
11. Stop. Do not proceed to another phase without explicit user approval.

## 0.2 Absolute Git restrictions

- **Local commits only. Never push.**
- Never run `git push`, `git push --force`, `git pull`, `gh pr create`, or any command that uploads or changes a remote repository.
- Never open a pull request, publish a branch, create a release, or alter remotes.
- Never amend, squash, rebase or rewrite existing commits.
- Never run `git reset --hard`, `git clean -fd`, or destructive checkout/restore commands.
- Preserve all existing history, branches, tags and user changes.
- Do not invent Git name/email. If commit identity is missing, ask the user to configure it; do not bypass the issue.
- Before the first change, inspect `pwd`, `git status --short --branch`, `git log --oneline -5`, and `git remote -v` (read-only).
- Use a dedicated working branch if a repository already exists and a safe branch can be created without disturbing user work. If there is no repository, initialize only in the intended project root after confirming it contains no unrelated user files.
- Commit subjects should describe real changes, e.g. `docs: record source hashes`, `test: add basis-state mapping fixtures`, `feat: add reversible gate IR`, `fix: preserve unrestricted PUI side effects`.

### Preserve commit history for download

After the phase's commits are complete:

- Create a full local bundle, for example `git bundle create handoff/phase-01.bundle --all`.
- Verify it with `git bundle verify handoff/phase-01.bundle`.
- Also create a source snapshot archive for convenient browsing, excluding secrets, virtual environments, caches, datasets and temporary outputs.
- Do not put credentials or local machine configuration in either artifact.
- Include a `HANDOFF.md` with clone instructions, commit range/log, tests and commands for the user's local machine.
- If creating bundles in the same repository causes a packaging issue, put the bundle outside the tracked source tree or in the downloadable artifact area.

The user's intended workflow is to download the phase handoff, clone or inspect the bundle locally, run it on their own hardware, review the changes and make any additional local commits they choose. Claude must not push on the user's behalf.

## 0.3 Hardware truthfulness

- Primary development machine: Ubuntu laptop with NVIDIA RTX 3050 6 GB VRAM and 16 GB system RAM. It is CUDA-capable and is the primary local CUDA development/validation target.
- CPU implementation is the correctness reference and portable fallback, not a claim that the RTX 3050 lacks CUDA.
- Kaggle is the online GPU tier; detect the accelerator actually assigned to each session.
- RTX 5060 Ti workstation with 64 GB RAM and SRM AP DGX-1 with eight Tesla V100 GPUs are optional, permission-/access-dependent resources for selected comparison runs.
- Claude's own execution environment is not the user's laptop, Kaggle session, 5060 Ti workstation or DGX-1. Never claim those devices were tested unless real logs from those devices are supplied.
- A CUDA request that falls back to CPU must be reported as CPU execution.
- Do not assume DGX-1's eight V100 VRAM pools form one unified memory allocation. First test one GPU, then evaluate multi-GPU parallelism on independent workloads.

## 0.4 Research integrity

- The journal PDF controls scientific details. Use exact page/figure/equation references.
- Keep `reference/` immutable after artifact verification. Never edit its lockfile or copy its source into `candidate_ai/`.
- Clearly distinguish source-paper claims, mathematical derivations, measured results, implementation estimates and hypotheses.
- Never invent test results, benchmark numbers, hardware detections or performance improvements.
- Do not claim 100% accuracy. Report exactly what has been verified and what remains unverified.
- Preserve the source PDF's known internal discrepancies in a source-audit note; do not silently rewrite the paper.

---

# 1. First prompt — readiness audit only (no code)

**Use this first. Do not skip it.**

```text
Read the complete Claude Project Instructions and all uploaded project files: the 14-day implementation roadmap, the original 22-page Rupprecht–Wölk PDF, the master study guide and its HTML rendering. The roadmap controls scope, phase order, budgets, hardware priorities and buffers. The PDF controls scientific claims. The study guide is explanatory support.

Do not write or modify code yet.

First inspect the workspace and Git state using read-only commands. Report:
1. Which source files you found, their sizes and SHA-256 hashes where available.
2. The exact 14-day / 58-focused-hour phase budget and the three buffer placements from the roadmap.
3. The planned source/reference/candidate/results/report directory layout.
4. The hardware plan: RTX 3050 CUDA laptop as primary local development target; CPU as correctness reference/fallback; Kaggle as online GPU tier; RTX 5060 Ti and SRM AP eight-V100 DGX-1 as optional targeted resources.
5. The exact Git policy: frequent meaningful local commits, no pushes, no PRs, no amend/squash/rebase/history rewrites, preserve existing changes, and provide a Git bundle with each phase handoff where possible.
6. Missing prerequisites, source inconsistencies, access limitations, technical risks and what must be verified locally by the user.
7. Whether Phase 1 can begin within its four-hour budget.

Do not create a repository, branch, files, commits or code until the audit is complete and I explicitly authorize Phase 1. Do not push anything. End by waiting for my approval.
```

---

# 2. Phase 1 prompt — source audit, workspace setup and hardware probe (4 hours)

```text
BEGIN PHASE 1 ONLY: Source audit, project setup and hardware probe. Budget: 4 focused hours, per the roadmap.

Re-open the Phase 1 section of `Sparse_State_Preparation_Implementation_Plan_14_Days.md` and the relevant source PDF pages. Follow all persistent project instructions.

Scope:
1. Inspect the current workspace and Git state. Preserve existing files, history and user changes.
2. Create the agreed isolated structure only if it does not already exist:
   reference/        immutable official authors' artifact
   candidate_ai/     our AI-assisted candidate implementation
   research-notes/   source audit, derivations, decisions
   results/raw/      raw logs only
   results/figures/  generated plots
   report/           technical report
   handoff/          downloadable phase handoffs, if safe
3. Copy or identify the supplied PDF, master Markdown guide and HTML guide without modifying the originals. Record SHA-256 hashes and provenance in `research-notes/SOURCES.md`.
4. Fetch the official Zenodo artifact only if network access is available and the project plan's exact artifact URL/checksum can be verified. Keep it isolated in `reference/`. Verify the specified MD5 as a transfer-integrity check, preserve the original lockfile, and do not modify the artifact.
5. Probe the environment actually available to you. Record OS, Python, Rust/Cargo/uv versions, CPU, RAM, disk, `nvidia-smi`, GPU name, VRAM, driver and CUDA runtime visibility. Do not label your environment as the user's RTX 3050 unless it is demonstrably that hardware.
6. Generate a small hardware/environment report and a reproducible local probe script for the user to run on the RTX 3050. Include a CUDA availability smoke-test command appropriate to the chosen library, but do not install large frameworks without need.
7. Add `WORKLOG.md`, `DECISIONS.md`, `research-notes/SOURCE_AUDIT.md` and a concise `README.md` with project purpose and current phase.
8. Do not implement the quantum algorithms in this phase.

Tests/checks:
- Source hash verification.
- Directory-isolation check.
- Reference immutability check.
- Run only lightweight environment and script checks available here.
- Provide the exact commands the user should run locally to verify RTX 3050 CUDA.

Git:
- Commit each coherent setup/source-audit milestone locally after checks.
- Never push or alter remotes.
- Generate and verify `handoff/phase-01.bundle` plus a source snapshot and `HANDOFF.md`, if Git is available.

Exit gate:
- Sources identified and hashed.
- Reference artifact either verified and isolated or the precise retrieval blocker documented.
- Workspace and worklog initialized.
- Actual environment capability recorded without hardware claims by assumption.
- User-side RTX 3050 probe commands prepared.

At completion, stop. Report actual time spent against 4 hours, commits, tests, outputs and anything the user must run. Do not begin Phase 2.
```

---

# 3. Phase 2 prompt — reproduce and inspect official reference artifact (4 hours)

```text
BEGIN PHASE 2 ONLY: Reproduce and inspect the authors' official reference artifact. Budget: 4 focused hours.

Read the Phase 2 roadmap section and inspect the artifact's own README, environment instructions, module tree and test definitions. Keep `reference/` immutable except for generated ignored environments/cache outside tracked source; do not edit source files or the lockfile.

Tasks:
1. Map the reference repository structure and identify the Rust isometry finder, Qualtran Bloqs, notebook, figure-generation scripts and tests.
2. Create a module map in `research-notes/REFERENCE_CODE_MAP.md` that links each paper algorithm/figure to the corresponding artifact module or test where identifiable.
3. Reproduce installation/test commands as written by the artifact, adapting only through an external environment or isolated copy if the original lockfile/dependency warning requires it. Do not silently regenerate `uv.lock`.
4. Run Python and Rust tests only where dependencies and permissions allow. Capture exact commands, versions, stdout/stderr, exit codes and elapsed time.
5. Run the introductory notebook only if safe and supported. If notebook execution is blocked by dependencies, document the exact cause and preserve the notebook unmodified.
6. Record which modules can be called through a narrow black-box adapter for comparison. Do not copy reference source into `candidate_ai/`.
7. Create a small reference-output fixture for a valid tiny input if the artifact exposes a supported interface; record the exact input and output.

Do not implement independent algorithms yet.

Git: commit the module map, test/reproduction logs and integration notes locally. Keep raw generated environments out of Git. Create and verify the phase-02 Git bundle and source snapshot. Never push.

Exit gate: reproducibility status is evidenced; reference structure is mapped; adapter boundary is documented; reference tree/lockfile remains unchanged. Stop and wait for Phase 3 authorization.
```

---

# 4. Phase 3 prompt — independent model, gate IR and validation harness (5 hours)

```text
BEGIN PHASE 3 ONLY: Independent model, reversible gate IR and validation harness. Budget: 5 focused hours.

Read the Phase 3 roadmap section and exact PDF sections defining basis-state representation, gate conventions, tableau, isometry direction and resource accounting.

Implement in `candidate_ai/` only. Do not copy reference implementation code.

Tasks:
1. Create a minimal installable Python package `sparseprep` with clear modules for model, gates, tableau, validation and resource accounting.
2. Define explicit typed representations for n-bit basis strings, sparse supports, register splits, labels and signs. Enforce big-endian convention: for a w-bit address, `100` represents integer 4.
3. Implement explicit reversible gate operations needed by the paper: X, CX, SWAP, Toffoli, negative-control Toffoli, CMX and circuit composition/inversion. Preserve CX/CMX separately from Toffoli counts.
4. Implement a transparent circuit IR and a simulator of gate action on computational-basis states/permutations for small instances.
5. Implement tableau construction and deterministic support generators for random and structured cases.
6. Build independent test oracles and property tests. Do not test a function only against another function that shares its internal logic.
7. Set up CPU correctness reference and a modular CUDA backend interface. On this environment, test only devices actually visible. Prepare a specific RTX 3050 CUDA smoke-test script for the user if their hardware is not available here.
8. Add precise exceptions, type checks, deterministic seeds and documentation.

Avoid premature GPU work: only implement backend primitives justified by measured parallel workloads. Do not write complex multi-GPU infrastructure in this phase.

Exit gate:
- Small basis-state gate tests pass.
- Circuit inverse tests pass for supported gate IR.
- Big-endian test cases pass.
- CPU backend acts as a deterministic oracle.
- Package imports and installs in its isolated environment.
- CUDA status is reported honestly; user-side validation commands are provided.

Make several coherent local commits (model, gate IR, tableau, tests/backend scaffolding). Bundle phase history. Stop after Phase 3.
```

---

# 5. Phase 4 prompt — Malvetti baseline (6 hours)

```text
BEGIN PHASE 4 ONLY: Independent Malvetti sparse-isometry baseline. Budget: 6 focused hours.

Re-read the exact paper pages for Section 2's Malvetti construction and Appendix A/D. Confirm conventions from the PDF before coding.

Tasks:
1. Implement explicit label allocation `f_baseline` for the support states.
2. Implement the baseline algorithm mapping each target basis state into a unique compact label with zero residual register.
3. Implement the required controlled-X / MCX logic using the agreed explicit gate IR. If representing MCX as a macro, retain its control count and provide the paper-aligned AND-ladder Toffoli decomposition/resource model separately.
4. Keep logical gate macros, decomposed gate counts and analytical formula estimates as distinct fields. Never count CX/CMX as Toffolis.
5. Implement `to_subspace` with exact direction `G |C_i> = |f(i)>_s |0>_r` and `from_subspace` through the inverse `G†`.
6. Test supports with zero residual rows, repeated first-ell-bit prefixes, non-power-of-two sparsity and arbitrary distinct basis strings.
7. Verify injectivity, zero residual, exact basis action and inverse restoration.
8. Compare the baseline's emitted decomposed Toffoli count against `s(ell-1)` under the paper's assumptions. If gate-IR choices alter the decomposition, explain the model difference rather than forcing a false equality.

Do not start PUI or the batched algorithm yet.

Exit gate: independent baseline works on exhaustive small supports and randomized valid supports; all invariants pass; resource model is auditable.

Commit code and tests atomically in multiple local commits. Provide phase bundle and stop for user execution/review.
```

---

# 6. Phase 5 prompt — restricted and unrestricted PUI / Algorithm 2 (9 hours)

```text
BEGIN PHASE 5 ONLY: Restricted and unrestricted Partial Unary Iteration (Algorithm 2). Budget: 9 focused hours.

Before implementation, re-open PDF Section 3 and Appendix B. Build a notation table for the local PUI variables. Use `q = log2(m)` in explanatory derivations to avoid confusing subtree depth with the paper's subspace width ell. Preserve the paper's original symbols in source references.

Tasks:
1. Implement restricted PUI recursively over a requested address interval `[l,r]` in a w-bit big-endian address register.
2. Implement unrestricted PUI with all three recursive overlap cases. Return the emitted circuit plus exact extra-address set `L` and mapping `g`.
3. Make the API explicit about intended interval actions and unintended higher-address contributions. Never silently discard or approximate `L,g`.
4. Implement exhaustive truth-table evaluation for every address for small `w` (choose practical widths based on runtime/memory and document limits).
5. Compare each address's target-register action against an independent, direct mathematical oracle—not merely the recursive constructor's own bookkeeping.
6. Verify addresses below the interval are unchanged; intended interval addresses receive the specified `U_i`; extra addresses above the interval match `g`; all remaining addresses behave as specified by the paper.
7. Implement PUI resource formulas for the full power-of-two case and truncated `s`-address case. Keep Equations (5)–(8), actual emitted Toffoli count and any decomposition overhead distinct.
8. Add randomized and exhaustive tests for boundary intervals, single-element intervals, intervals aligned/misaligned to powers of two, full intervals and final partial intervals.
9. Batch independent truth-table sweeps for CUDA only if it actually speeds this workload. Preserve CPU oracle and test CPU/CUDA result parity.
10. Document exact recurrence, free-bit tracking, `L` and `g` examples with small diagrams/traces.

Do not implement Algorithm 1 in this phase.

Exit gate: exhaustive small-width action matches the direct oracle; `L,g` are exact; restricted/unrestricted distinction is tested; cost equations are traceable to the paper.

Use several meaningful local commits: restricted PUI, unrestricted recursion, extra-address map, cost model, exhaustive tests, backend kernels if justified. Create verified phase bundle and stop.
```

---

# 7. Phase 6 prompt — batched isometry / Algorithm 1 (8 hours)

```text
BEGIN PHASE 6 ONLY: Batched sparse-isometry construction / Algorithm 1. Budget: 8 focused hours.

Re-open PDF pages 4–6 and Algorithm 1 in Appendix C. Also inspect the matching PUI implementation from Phase 5 and its tests. Do not copy code from `reference/`.

Tasks:
1. Implement the tableau-based classical batch-finding procedure.
2. Implement normal CMX batch-element construction.
3. Implement the right-shift SWAP path.
4. Implement the difficult positive- and negative-control Toffoli path used when a suitable residual column is not directly available.
5. Apply the tested PUI compiler to zero complete batches. Do not replace PUI with a direct zeroing shortcut and claim the algorithm was implemented.
6. Propagate unrestricted PUI side effects into every affected tableau row using the exact `L,g` mapping.
7. Implement the special final-batch restricted-PUI correction and the collision handling described in the paper.
8. Derive the bijection from the final tableau and verify uniqueness.
9. Retain a detailed, optional trace of every tableau mutation and corresponding gate operation for small examples.
10. Verify `G |C_i> = |f(i)>_s |0>_r` for every row and verify inverse restoration `G†G|C_i> = |C_i>`.
11. Compare actual emitted gates and Toffoli decomposition against the analytical bounds without conflating them.
12. Add regression cases that force each branch: normal CMX, SWAP, positive-control Toffoli, negative-control Toffoli, unrestricted-PUI side effects and final restricted correction.

Do not implement Algorithm 3 yet.

Exit gate: every Algorithm 1 branch has at least one explicit regression test; exhaustive/random small supports preserve injectivity, residual-zero and inverse invariants; trace output is reproducible.

Commit each tested branch and regression suite locally. Create verified phase bundle and stop for user review.
```

---

# 8. Phase 7 prompt — Algorithm 3 real-state sign fixing (4 hours)

```text
BEGIN PHASE 7 ONLY: Algorithm 3 real-state phase-fixing isometry. Budget: 4 focused hours.

Re-open PDF Section 4, page 13 and Algorithm 3 in Appendix C. Confirm the exact sign convention and marker-ancilla behaviour.

Tasks:
1. Extend the input model to accept signs `a_i ∈ {+1,-1}` only for this algorithm. Do not treat this as arbitrary complex-phase encoding.
2. Add the marker ancilla initialized to `|1>` exactly as specified.
3. Implement restricted-PUI use and marker updates.
4. Implement counter-effect corrections for previously batched states where required by Algorithm 3.
5. Preserve and update the sign list together with the tableau.
6. Verify `G|C_i> = a_i |f(i)>_s |0>_r |0>_e` (with register order and marker output exactly as documented by the implementation and paper).
7. Test all-positive signs, mixed signs, duplicate subspace prefixes, unbatched subspace rows and partial final batches.
8. If any branch cannot be completed within the phase budget, stop at the last correct point, label the unfinished branch clearly and provide a failing/minimal reproducer. Do not label Algorithm 3 complete.

Exit gate: exact sign-aware mapping and inverse checks pass for every supported test; limitations are explicit.

Commit model, marker logic, sign correction and tests as separate meaningful local commits. Create verified phase bundle and stop.
```

---

# 9. Phase 8 prompt — correctness campaign and hardware-aware benchmarks (10 hours)

```text
BEGIN PHASE 8 ONLY: Full correctness campaign and controlled benchmarks. Budget: 10 focused hours.

First inspect all code, tests, WORKLOG.md, DECISIONS.md, Git history and previous phase handoffs. Do not modify algorithm logic without opening a bug-fix subtask and regression test.

Correctness campaign:
1. Run the full unit/integration suite.
2. Exhaustively sweep supported small PUI widths and intervals against the direct oracle.
3. Test Algorithm 1 supports with non-power-of-two s, repeated subspace prefixes, already-in-subspace rows, sparse residual columns, swap-trigger cases, positive/negative Toffoli-trigger cases, partial batches and unrestricted-PUI side effects.
4. Test Algorithm 3 sign combinations and marker-ancilla invariants if implemented.
5. Verify injectivity, zero residual, inverse basis action and small-instance statevector fidelity. Only use full statevectors where the complete register is small enough and the implemented circuit semantics are exact.
6. Test CPU/CUDA parity for each supported kernel. The CPU result remains the correctness reference.

Benchmark campaign:
7. Start with small/medium configurations suitable for 6 GB VRAM and 16 GB system RAM. Increase `s` only after measuring memory and runtime; do not blindly force `10^5+` on the laptop.
8. Benchmark deterministic random supports and structured/difficult support families. Record seed, `n`, `s`, `m`, support family, algorithm variant, backend requested, backend actually used, runtime, peak host RAM, peak GPU VRAM, logical gate counts, emitted Toffoli count and analytical bound.
9. For GPU work, warm up kernels and run repeated measurements; report median and spread. For compilation/branch-heavy logic, compare CPU against GPU only if the work is actually parallelized.
10. On the RTX 3050, run the actual local CUDA smoke and benchmark commands only when the user supplies logs or the current execution environment demonstrably is that device.
11. Use Kaggle for a separate portability run when available. Detect and record the actual assigned accelerator and session details. Checkpoint and export raw JSONL/CSV outside ephemeral runtime storage.
12. The RTX 5060 Ti and DGX-1 are optional targeted comparisons. Do not block the phase if they are inaccessible. For DGX-1, run one V100 first and use multiple V100s only for independent workloads with measured benefit.
13. Save raw data to `results/raw/`, normalized summary to `results/summary.csv`, exceptions/failed configurations to a separate file, and figures to `results/figures/`.
14. Every plot/table claim must trace to a raw row or a shown analytical derivation. No fabricated numbers or inferred GPU timings.

Exit gate: all required correctness tests pass or have explicitly documented failures; raw data is complete; hardware/backend identity is recorded; plots are reproducible; actual gate counts are separated from analytical bounds.

Commit tests, benchmark runners, raw-data schema, analysis scripts and figures as coherent local changes. Create verified phase bundle and stop.
```

---

# 10. Phase 9 prompt — research report and release (8 hours)

```text
BEGIN PHASE 9 ONLY: Technical analysis, final report and release handoff. Budget: 8 focused hours.

Read the report requirements in the roadmap. Inspect the source paper, study guide, source audit, all implementations, tests, WORKLOG.md, DECISIONS.md, raw benchmark data, failed-run records, plots and Git history.

Write a self-contained technical report in `report/technical_report.md` and render HTML; PDF only if a reliable local renderer is available.

Required report sections:
1. Executive summary and exact scope.
2. Mathematical problem formulation and notation.
3. Baseline algorithm and its assumptions.
4. Restricted/unrestricted PUI derivation and exact `L,g` semantics.
5. Batched isometry construction, all branches and tableau traces.
6. Algorithm 3 sign fixing, including support gaps if incomplete.
7. Three-layer implementation architecture: classical algorithm, gate IR, resource accounting.
8. Correctness methodology and test matrix.
9. Hardware/software environment actually measured.
10. Benchmark results with all raw metrics and failed/omitted configurations.
11. Analytical bounds versus actual emitted counts (separate columns/plots).
12. CPU/CUDA/Kaggle/optional workstation/DGX comparisons only where real data exists.
13. Source-paper discrepancies and the exact implementation interpretation used.
14. Limitations, threats to validity and future work.
15. Reproduction instructions and exact commands.
16. Reference list with relevance to the implementation.

Reporting rules:
- Do not invent results or claim hardware that was not used.
- Do not call the implementation 100% accurate. State the exact tested domain and residual gaps.
- Distinguish measured, analytically derived, estimated, inferred and not-run data.
- Cite paper page/figure/equation numbers for algorithmic claims.
- Include commit hash/code revision for each benchmark campaign.
- Verify plots can be regenerated from saved raw data.
- Include a final release checklist and a clean-environment reproduction script where feasible.

Git and delivery:
- Commit report sections, figure generation, reproduction scripts and final audit in separate meaningful local commits.
- Never push or publish.
- Create and verify a final Git bundle preserving the full local commit history, plus a source archive and `HANDOFF.md`.
- Report all local commits, final branch, working-tree status and any user edits still recommended.

Stop after the release handoff. Do not push.
```

---

# 11. User-side validation and feedback prompts

Use these after downloading a phase bundle and running it on the actual laptop or other hardware. Paste real terminal output, not a paraphrase.

## 11.1 Local run report

```text
I downloaded the Phase <N> handoff and ran it on my actual machine. Here are the exact commands, hardware output and complete logs:

[PASTE COMMANDS AND LOGS]

Please:
1. Identify which checks passed, failed or were skipped.
2. Separate environment/driver errors from implementation bugs.
3. Do not claim success for a command that did not exit successfully.
4. Find the smallest reproducible failure and add it as a regression test.
5. Propose the minimum fix within the current phase scope.
6. Do not begin the next phase.
7. If code changes are required, make a new local fix commit without rewriting earlier commits; provide a new verified bundle.
8. List the exact commands I should rerun.
```

## 11.2 Phase review / exit-gate decision

```text
Review Phase <N> against its exact roadmap exit gate. Inspect the source files, test suite, WORKLOG.md, DECISIONS.md, diff and local commit history.

Return a checklist with PASS / FAIL / NOT RUN for every exit-gate item. Explain the evidence for each item. Identify untested branches and unsupported claims. Verify that no remote push occurred and that the reference artifact is unchanged.

Do not implement the next phase. Recommend one of: ACCEPT PHASE, FIX CURRENT PHASE, or DEFER A DOCUMENTED ITEM. Wait for my decision.
```

## 11.3 Buffer-day prompt

```text
Use the currently designated buffer only for issues already identified in the roadmap or prior phase review. Do not add features or expand scope. Inspect the failure log and worklog, rank blockers by correctness impact, fix the highest-priority bounded issue, add regression tests, make local commits and provide a new handoff. Report buffer time used. Stop when the buffer task is resolved or its remaining time is exhausted. Never push.
```

## 11.4 Git handoff audit

```text
Prepare this phase for download. Do not push. Show `git status --short --branch`, `git log --oneline`, `git diff --stat`, the exact commit hashes for this phase, and the result of `git bundle verify`. Ensure the handoff includes a Git bundle preserving history, a source snapshot and HANDOFF.md with clone/run instructions. If any item cannot be produced, state why and provide the safest alternative without rewriting history.
```

---

# 12. How the user should operate the project

1. Paste **Section 1 readiness prompt** first. Claude audits only; no code.
2. Review Claude's readiness report and correct missing source/hardware assumptions.
3. Paste **Section 2 Phase 1 prompt** only after approving Phase 1.
4. Download that phase's Git bundle and source snapshot.
5. Clone/inspect the bundle locally, run the provided commands on the RTX 3050, and inspect the commit history.
6. Paste real logs using Section 11.1 if anything fails.
7. Use Section 11.2 to decide whether the phase is accepted.
8. Only then authorize the next phase prompt.
9. Keep each phase handoff as a backup. Never overwrite a previously accepted bundle.
10. At the end, inspect and edit the accumulated commits locally. The user—not Claude—decides when and where to push.

**The central rule:** Claude may implement and make local commits phase by phase. The user downloads, runs, reviews and accepts each phase. No one-shot build, no automatic push, no unreviewable monolithic commit, and no claim of verification without evidence.
