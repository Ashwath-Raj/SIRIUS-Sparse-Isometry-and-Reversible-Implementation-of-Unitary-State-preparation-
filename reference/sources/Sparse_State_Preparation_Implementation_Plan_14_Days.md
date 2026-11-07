# Two-Week Execution Plan — Sparse Quantum State Preparation

## AI-assisted implementation, hardware-aware validation, and reproducible research report

**Primary paper:** Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost* (2026).  
**Paper:** <https://quantum-journal.org/papers/q-2026-09-10-2208/>  
**Official research artifact:** <https://zenodo.org/records/18234600>  
**Plan duration:** exactly 14 consecutive calendar days.  
**Planned focused effort:** **58 hours** across 11 productive workdays.  
**Flexibility:** 3 full buffer days, reserved for dependency failures, debugging, compute access and result verification.  
**Primary development machine:** Acer Nitro V laptop, CUDA-capable NVIDIA RTX 3050 6 GB VRAM, 16 GB system RAM, Ubuntu. CUDA is the primary local accelerator for suitable parallel kernels; CPU execution remains the correctness reference and fallback.  
**Online accelerator:** Kaggle Notebooks, using whichever GPU accelerator is actually available to the account/session.  
**Optional short-run resources:** RTX 5060 Ti workstation (64 GB system RAM) and SRM AP NVIDIA DGX-1 (eight Tesla V100 GPUs), subject to physical access and permissions.

---

# 0. Executive decision

This plan uses an **AI-assisted candidate implementation workflow**. A coding agent (Claude) may generate and revise code, tests, scripts and report drafts. The generated implementation is a candidate, not ground truth. It becomes an accepted baseline only after it passes independently designed correctness tests, source-level checks and reproducible benchmark runs.

The later human-led implementation must remain a separate effort and must not copy the candidate implementation. This two-week plan is for building and validating a strong, portable candidate and collecting evidence that a later independent implementation can be compared against.

## 0.1 Research objective

Independently implement and validate the sparse-isometry construction from Rupprecht and Wölk, compare it with the Malvetti et al. baseline and the authors' reference artifact, then measure how the actual emitted resource counts depend on support structure, sparsity, register width and PUI variant.

**Primary research question:**

> For controlled sparse supports and register sizes, does an independently implemented batched-isometry construction reproduce the paper's basis-state mapping and resource behaviour, and which input structures cause its practical Toffoli count to approach or depart from the observed near-s behaviour?

## 0.2 What success means

The result must be reproducible by another engineer. A successful submission contains:

1. An isolated copy of the authors' official artifact, unchanged.
2. A separate candidate implementation with a documented architecture.
3. A transparent reversible-gate representation and resource counter.
4. Tests for the Malvetti baseline, restricted/unrestricted PUI and batched isometry.
5. Algorithm 3 sign-fixing support, or an explicitly scoped and tested partial implementation if a correctness-critical branch cannot be completed.
6. Small-instance exact correctness checks and controlled performance experiments.
7. Raw benchmark records, generated plots and a technical report that labels every result as measured, derived, inferred or not run.

**No implementation receives a “100% accurate” label merely because an agent says it is complete or a small test suite passes.** The acceptance standard is evidence: exact mapping checks, edge-case coverage, reproducible commands, source-aligned derivations and honest reporting of failed or unavailable runs.

---

# 1. Hardware strategy and execution responsibilities

The RTX 3050 laptop is the primary development machine and supports CUDA. The project must use its CUDA capability for workloads that benefit from parallel execution, while retaining a CPU reference/fallback path for portability and correctness. Kaggle is the accessible online GPU tier. The RTX 5060 Ti workstation and SRM AP DGX-1 are optional high-end comparison resources that should be used only when a specific experiment justifies the access overhead.

## 1.1 Hardware priority order

| Priority | Environment | Role in this project | Dependency status |
|---|---|---|---|
| 1 | **Acer Nitro V: CUDA-capable RTX 3050, 6 GB VRAM, 16 GB RAM** | Main development; primary local CUDA testing for suitable kernels; CPU reference/fallback; unit tests; small exact simulations; normal benchmark runs | Required and always available |
| 2 | **Kaggle GPU Notebook** | Accessible online GPU capacity for larger independent batches, CUDA portability, longer benchmark sweeps and clean-environment replication | Optional; use when local VRAM/session limits justify it |
| 3 | **RTX 5060 Ti workstation, 64 GB RAM** | Short targeted comparison, larger CPU-memory experiments and one representative GPU profile | Optional; use only when access is convenient |
| 4 | **SRM AP NVIDIA DGX-1: eight Tesla V100 GPUs** | Final institutional HPC experiment: one-GPU baseline first, then carefully chosen multi-GPU workloads | Optional; permission and scheduling required |

## 1.2 What the DGX-1 facility description means for our project

The SRM AP facility description supplied for this plan identifies the DGX-1 as a high-throughput deep-learning system with **eight Tesla V100 GPUs** connected through a **hybrid cube-mesh NVLink topology**. It quotes an aggregate bidirectional NVLink bandwidth of **up to 300 GB/s per GPU** and describes this as more than nine times PCIe Gen3 x16 bandwidth.

Use those figures as the facility's stated peak interconnect specification, not as a promise of application throughput. Actual transfer and benchmark performance depend on the installed DGX-1 configuration, GPU memory size, CUDA/NCCL versions, topology, software, workload partitioning and system contention.

Important engineering distinctions:

- Eight V100s are eight separate GPUs with separate device-memory pools. NVLink provides fast communication; it does **not** automatically merge the eight VRAM capacities into one transparent allocation.
- Do not assume whether the installed V100s have 16 GB or 32 GB each. Record the actual model and memory using `nvidia-smi` once access is granted.
- The PUI recursion and parts of the tableau update are branch-heavy and may be sequential. They will not automatically become eight times faster on eight GPUs.
- DGX-1 multi-GPU work should focus on workloads that can genuinely be partitioned: independent support instances, independent random seeds, batches of truth-table checks, or independent benchmark configurations. Do not split one sequential tableau algorithm across GPUs unless a measured implementation justifies the communication and synchronization cost.
- First benchmark one V100. Only then test 2/4/8 GPUs for a workload with enough independent parallelism.

The DGX-1 is a final validation tier, not the development machine and not a blocker for the report.

## 1.3 Kaggle strategy

Kaggle is the online GPU environment. The plan must detect the accelerator that the session actually receives rather than hard-code a GPU model.

At plan preparation time, Kaggle staff had announced the retirement of the Tesla P100 option effective 15 September 2026 and stated that T4 x2 remained available. The actual options, quota, queue time and session limits must still be checked in the Kaggle UI at the moment of use. Do not assume a particular accelerator is guaranteed.

Kaggle should be used for:

- Confirming that the same CUDA backend installs and runs in a second, hosted GPU environment outside the local laptop.
- Running a benchmark suite on the detected GPU.
- Comparing data-parallel throughput for independent test instances or support-generation workloads.
- Testing checkpointing and result export from a hosted notebook.

Kaggle should **not** be used for:

- Long uninterrupted runs without checkpointing.
- Assuming GPU acceleration will benefit every part of this algorithm.
- Claiming a T4 x2 session is one 32 GB GPU. Each accelerator is a distinct device and needs explicit multi-GPU code.
- Storing the only copy of raw benchmark data in a temporary runtime directory.

Every Kaggle run must save its configuration, notebook/session hardware report, logs and results to a durable output (downloaded artifact, Kaggle output/dataset or the project repository as appropriate).

## 1.4 The RTX 3050 is the primary CUDA development device, with a strict memory budget

The main laptop has a CUDA-capable RTX 3050 with 6 GB VRAM and 16 GB system RAM. Use CUDA as the primary local accelerator for suitable data-parallel workloads, but design every operation to remain memory-bounded. The CPU implementation is the independent correctness reference and automatic fallback, not the only intended execution path:

- Use compact integer or packed-bit representations for bitstrings where appropriate.
- Prefer `uint64` bit-packing for bulk support matching and bitwise operations; keep a simple Python reference representation for correctness.
- Process large support arrays in chunks. Avoid materializing large pairwise distance matrices.
- Keep GPU arrays bounded and move only the needed chunks to the device. Use chunked CUDA kernels for high-volume independent tableau matching, packed-bit operations and batches of PUI truth-table checks.
- Avoid allocating a full `2^n` statevector except for very small `n`. The project is about sparse basis-state mappings; exact basis-action/permutation tests are usually the correct scalable validation tool.
- Record peak host RAM and GPU VRAM. A run that swaps heavily or causes an out-of-memory condition is a failed/aborted configuration, not a successful benchmark.
- CPU-only operation must remain fully functional as a portability/fallback mode. On the primary RTX 3050 machine, the project must pass a CUDA smoke test and at least one real CUDA benchmark. If the selected Python library cannot access the CUDA-capable GPU, diagnose and resolve the driver/runtime/library mismatch before declaring local CUDA validation complete.

## 1.5 Workload-to-hardware mapping

| Workload | RTX 3050 laptop | Kaggle GPU | RTX 5060 Ti / 64 GB | DGX-1 |
|---|---|---|---|---|
| Environment setup and Python development | Primary | Not needed | Optional | Not needed |
| Gate IR and small exact basis simulation | Primary | Not needed | Optional | Not needed |
| PUI recursive circuit generation | Primary CPU/reference implementation; CUDA only for batches of independent interval jobs | Batch many independent intervals if beneficial | Optional CPU/GPU comparison | Not a first-choice target |
| Tableau matching and bit-packed bulk operations | Primary CUDA for large independent/chunked operations; CPU reference and fallback | Online GPU throughput/portability | Short higher-memory/GPU comparison | Independent-instance parallelism |
| Exhaustive small-width PUI truth tables | CPU is the correctness oracle; CUDA accelerates batches of independent intervals/configurations | Batch many independent intervals | Optional cross-check | Parallel sweeps only if justified |
| Small statevector checks | Primary local, bounded by 6 GB VRAM/16 GB RAM; use CPU or CUDA according to size | Larger small-instance sweeps if appropriate | Convenient for larger small cases | Not the primary purpose |
| Large independent support sweeps | Small/medium local runs | Main online accelerator candidate | Good occasional resource | Strong option for distributed independent runs |
| Final report generation | Primary | Not needed | Optional faster plotting | Not needed |

## 1.6 Who does what

**Coding agent (Claude):** generate modular code, tests, scripts, documentation and candidate reports; explain design choices; revise code from actual error logs. It must not claim to have run local laptop, Kaggle, RTX 5060 Ti or DGX-1 experiments unless it receives and records real execution outputs from those environments.

**User/operator:** run commands on the laptop; select and start Kaggle accelerators; download/export results; arrange any RTX 5060 Ti or DGX-1 access; preserve credentials and institutional access securely; provide actual logs to the coding agent for debugging.

**Acceptance rule:** source code can be generated in one pass, but evidence must come from the actual device and command that ran it.

---

# 2. Scope lock

The sprint focuses on the isometry contribution and the correctness of its reversible mapping. It does not attempt to reproduce every component of the complete dense-state-preparation pipeline.

## 2.1 Mandatory core

1. Malvetti et al. sparse-isometry baseline.
2. Restricted and unrestricted Partial Unary Iteration (PUI), including Algorithm 2's recursive interval handling and exact extra-address bookkeeping `L` and `g`.
3. Rupprecht–Wölk batched isometry / Algorithm 1: normal CMX path, SWAP path, positive/negative-control Toffoli path, unrestricted-PUI side-effect propagation and final-batch correction.
4. Explicit reversible-gate IR and separate resource-accounting layer.
5. Exact basis-state action, injectivity, zero-residual and inverse checks.
6. An independently testable CPU reference backend and a working CUDA backend on the primary RTX 3050 for selected data-parallel workloads.
7. Automatic CPU fallback when CUDA is unavailable, unsupported or slower for a given operation; backend selection and actual execution device must be logged.
8. Reproducible local and Kaggle benchmark scripts.
9. Algorithm 3 real-state sign fixing: attempt full small-instance implementation; incomplete coverage must be explicitly marked and never represented as complete.
10. Technical report and reproducibility package.

## 2.2 Secondary scope, promoted only after the core passes

- Full Algorithm 3 sign-fixing support with marker ancilla initialized to `|1>` and sign-aware mapping.
- A short comparison using the RTX 5060 Ti workstation.
- A DGX-1 single-GPU and, if justified, multi-GPU run.
- Qualtran resource-count cross-check for one or more small generated circuits.

## 2.3 Explicitly out of scope

- Reimplementing all Grover–Rudolph dense-state preparation.
- Building a complete independent QROM/QROAM and phase-gradient-state stack.
- Running on a quantum processor.
- Claiming the paper's original `s = 10^7` scale has been reproduced unless it is actually measured.
- A production-grade general distributed computing framework.
- Implementing the later sublinear-T-count papers.
- Claiming a new asymptotic improvement without a proof.

---

# 3. Exact 14-day structure and effort budget

The plan spans **14 consecutive calendar days exactly**. It is intentionally not organized as a date-by-date calendar. Work is organized by phases and hours.

- **11 productive workdays** carry the planned 58 focused hours.
- **3 full buffer days** are inserted after major milestones.
- Average focused work on a productive day: approximately 5.3 hours.
- The three buffers are calendar days, not hidden extra implementation hours.
- If a buffer is not needed, keep it free; do not expand scope simply because time is available.

## 3.1 Buffer placement

| Buffer | Insert after | Use |
|---|---|---|
| Buffer A | Phase 2: reference setup and artifact inspection | Fix local dependency/Rust issues, rerun tests, or move the reference notebook to Kaggle if local environment constraints block it. |
| Buffer B | Phase 6: PUI + Algorithm 1 integration | Debug side-effect bookkeeping, difficult batch branches, final partial batches and any wrong mapping. |
| Buffer C | Phase 8: correctness and benchmark campaign | Rerun suspicious measurements, complete Kaggle export, handle optional workstation/DGX access, regenerate plots and audit report claims. |

## 3.2 Phase effort budget

| Phase | Work package | Focused hours | Primary environment | Deliverable |
|---|---|---:|---|---|
| 1 | Source audit, project setup and hardware probe | 4 h | RTX 3050 laptop | Locked sources, environment report and compute detection |
| 2 | Official artifact reproduction and code map | 4 h | Laptop; Kaggle fallback if needed | Reference test log and module map |
| 3 | Independent model, gate IR and validation harness | 5 h | RTX 3050 laptop: CUDA setup plus CPU reference | Tested data model, tableau, gates, support generators and backend parity |
| 4 | Malvetti baseline | 6 h | RTX 3050 laptop; classical baseline logic with CPU/CUDA bulk-kernel checks | Baseline mapping and cost model |
| 5 | Restricted/unrestricted PUI / Algorithm 2 | 9 h | RTX 3050 laptop: CPU reference plus CUDA batches of independent truth-table tests; Kaggle for larger sweeps | Recursive PUI, `L,g` map and exhaustive small tests |
| 6 | Batched isometry / Algorithm 1 | 8 h | RTX 3050 laptop: CPU for sequential control flow, CUDA for suitable independent matching/search kernels | Batch construction, tableau updates and inverse tests |
| 7 | Algorithm 3 real-state sign fixing | 4 h | RTX 3050 laptop: CPU reference plus CUDA for batched independent sign/marker verification where useful | Small-instance sign-fixing implementation or exact gap report |
| 8 | Correctness campaign and benchmark campaign | 10 h | Laptop + Kaggle; optional short workstation/DGX runs | Raw data, summaries and plots |
| 9 | Technical analysis, report and release | 8 h | Laptop | Reproducible repository and final report |
|  | **Total** | **58 h** |  |  |

---

# 4. Phase-by-phase implementation plan

Each phase has an objective, explicit tasks, outputs and an exit gate. Do not proceed past a correctness-critical failure simply to preserve the schedule.

## Phase 1 — Source audit, project setup and hardware probe

**Budget: 4 focused hours**  
**Primary machine: RTX 3050 laptop**

### Tasks

1. Create a workspace with strict separation:

   ```text
   sparse-state-preparation/
   ├── reference/          # authors' artifact; preserve unchanged
   ├── candidate_ai/       # code generated by Claude for the AI-assisted candidate
   ├── research-notes/     # paper derivations, source audit and decisions
   ├── results/            # raw data, summaries, logs and figures
   └── report/             # report and rendered output
   ```

2. Copy the supplied 22-page paper PDF, master study guide Markdown and HTML study-guide rendering into `research-notes/sources/`.
3. Record SHA-256 hashes, file sizes and source URLs in `research-notes/SOURCES.md`.
4. Treat the journal PDF as authoritative for equations, algorithms, page numbers and figure captions. Use the study guide as explanatory material, not as a replacement for the source.
5. Download the official Zenodo artifact into `reference/` and verify the MD5 value shown on the record (`c58634ba415b4e3fb729648460f32ad7`) as a transfer-integrity check. MD5 is not a security guarantee.
6. Preserve the artifact's original `uv.lock`. The artifact record warns that its lockfile was manually handled because a dependency on an older `nbconvert` release had a disclosed vulnerability at upload time. Do not regenerate the reference lockfile or run dependency-add commands inside the reference folder.
7. Probe the laptop:

   ```bash
   uname -a
   lscpu
   free -h
   df -h
   nvidia-smi
   nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
   python3 --version
   ```

8. Record the actual GPU model, VRAM, NVIDIA driver version, CUDA runtime/toolkit details when present, compute capability when queryable, CPU model/core count, available RAM and free disk. Do not assume the laptop's GPU is visible to every Python environment: test it from the exact Python environment used by this project.
9. Define two supported installs: a portable base/CPU environment and the CUDA-enabled development environment used on the RTX 3050. Install only the selected CUDA library actually needed by the kernels (for example CuPy, PyTorch or Numba-CUDA); do not add all three without a reason. The CUDA extra is part of the normal laptop setup, while the CPU-only install remains a portability path.
10. Add a small `hardware_probe.py` that records hardware and software details in JSON without failing when a GPU library is absent. It must distinguish CUDA-capable NVIDIA hardware, driver visibility, Python-library runtime availability and successful kernel execution.
11. Add a machine-readable experiment configuration file and set deterministic default seeds.
12. Define the project's source attribution and licensing policy before the AI coding agent writes files.

### Deliverables

- `research-notes/SOURCES.md`.
- `research-notes/scope-and-assumptions.md`.
- `environment/laptop-hardware.json`.
- `environment/software-versions.txt`.
- `scripts/hardware_probe.py`.
- Workspace directory structure.

### Exit gate

All input sources are identified and hashed; the official reference artifact is isolated; the laptop hardware probe records CUDA status; the project passes a CPU reference test and a real CUDA kernel smoke test on the RTX 3050. If the installed driver/runtime/library combination initially fails, resolve the compatibility issue before treating Phase 1 as complete.

---

## Phase 2 — Reproduce and inspect the official reference artifact

**Budget: 4 focused hours**  
**Primary machine: RTX 3050 laptop; Kaggle is a fallback for dependency or RAM issues**

### Tasks

1. Read the authors' README and inspect `pyproject.toml`, `uv.lock`, Python Qualtran Bloqs, Rust sources, wrappers and tests before running commands.
2. Record the artifact's exact Python, `uv`, Rust/Cargo, Qualtran and operating-system requirements.
3. Run the official Python tests:

   ```bash
   uv --version
   python --version
   rustc --version
   cargo --version
   uv sync
   uv run pytest
   cargo test
   ```

4. Run one smallest introductory notebook example. Do not use `nbconvert` merely to export the notebook; run it in a safe notebook environment or inspect it directly.
5. Identify the files/functions for:
   - Malvetti/baseline sparse isometry;
   - batched isometry construction;
   - restricted and unrestricted PUI;
   - Algorithm 3 / sign fixing;
   - Qualtran circuit representations;
   - resource-count and figure-generation code.
6. Run one tiny reference example and preserve its input, output mapping, resource estimate and command line.
7. Produce a module map explaining which official functions can be used as a black-box comparator and which must be independently implemented in `candidate_ai/`.
8. Do not copy code from `reference/` into `candidate_ai/`. Use a narrow adapter for side-by-side comparison only, with attribution and exact version recorded.
9. If the artifact cannot build on the 16 GB laptop, preserve logs. Move only the reference reproduction job to Kaggle or a more capable machine; do not redesign the independent implementation around the reference's dependency stack.

### Deliverables

- `results/reference_test_log.txt`.
- `results/reference_smoke_test.json`.
- `research-notes/reference-artifact-map.md`.
- A documented reference environment and known dependency limitations.

### Exit gate

At least one official reference example runs and is understood. Test outcomes are recorded accurately. The original reference folder remains unmodified.

---

## Phase 3 — Independent model, gate IR and validation harness

**Budget: 5 focused hours**  
**Primary machine: RTX 3050 laptop, CUDA-enabled development with CPU reference/fallback**

### Tasks

1. Build the candidate package with a small dependency footprint. Prefer standard Python plus NumPy for the baseline; optional accelerator libraries belong in extras, not mandatory dependencies.
2. Define an immutable input model with:
   - `n`: total system qubits;
   - ordered list of distinct `n`-bit support strings;
   - optional normalized complex coefficients for small statevector tests;
   - optional signs in `{+1,-1}` for Algorithm 3;
   - random seed and test-case metadata.
3. Adopt the paper's big-endian convention: the leftmost bit is most significant; for a three-bit address register, `|100>` is integer 4.
4. Validate input support: all strings have width `n`, are distinct, and satisfy `1 <= s <= 2**n`. Treat `s=1` as a trivial one-state special case rather than applying logarithmic resource formulae blindly. For the non-trivial paper construction, explicitly validate the paper's residual-width/batch constraints. Handle unsupported boundary cases with a clear exception instead of producing `m=0` or a negative register width.
5. Compute:

   ```python
   ell = ceil(log2(s))
   tilde_s = 2**ell
   residual_width = n - ell
   m = largest_power_of_two_at_most(residual_width)
   ```

   Use integer-safe functions (`bit_length`) where possible rather than floating-point logarithms for exact powers of two.
6. Build a tableau with stable original row IDs. Keep original input strings, current row strings and phase/sign metadata separate.
7. Create a small reversible gate IR:
   - `X(target)`;
   - `CX(control, target)`;
   - `SWAP(a, b)`;
   - `Toffoli(control_a, control_b, target)`;
   - negative-control Toffoli;
   - `CMX(control, targets)`;
   - restricted/unrestricted PUI macros with explicit interval and `L,g` metadata.
8. Create a deterministic classical basis-state simulator for the gate subset. Every gate must have a defined forward action and inverse action.
9. Create a transparent resource counter. It must distinguish `X`, `CX`, `CMX`, `SWAP`, Toffoli, MCX macros and decomposed Toffoli counts. Never count `CX` or `CMX` as Toffoli.
10. Keep emitted gate counts separate from analytical upper-bound calculations.
11. Create support generators for seeded random, structured and hand-crafted edge cases.
12. On the 3050 laptop, keep data structures compact. Do not create dense `2**n` arrays for general `n`; use bitstrings/integers/packed words and small exact tests.

### Required support families

- Seeded random distinct strings sampled without replacement.
- Power-of-two and non-power-of-two `s`.
- Initial rows already inside the subspace (zero residual register).
- Repeated first-`ell`-bit prefixes but distinct full strings.
- Cases designed to trigger the residual-bit SWAP path.
- Cases designed to trigger positive- and negative-control Toffoli paths.
- Cases with a partial final batch.
- Cases where unrestricted PUI can affect an address above the intended interval.

### Deliverables

- `candidate_ai/src/sparseprep/model.py`.
- `candidate_ai/src/sparseprep/tableau.py`.
- `candidate_ai/src/sparseprep/gates.py`.
- `candidate_ai/src/sparseprep/support_generators.py`.
- `candidate_ai/tests/test_model.py`.
- `candidate_ai/tests/test_gates.py`.
- `candidate_ai/tests/test_tableau.py`.

### Exit gate

All gate truth tables pass. Big-endian conversion tests pass. Input validation is explicit. Every support generator emits distinct strings. The reference test suite passes on CPU, and the CUDA backend passes device-discovery, a real kernel-smoke test and CPU/GPU parity tests on the RTX 3050. A CUDA setup problem must be diagnosed rather than silently downgrading the laptop workflow to CPU-only.

---

## Phase 4 — Malvetti baseline

**Budget: 6 focused hours**  
**Primary machine: RTX 3050 laptop; CUDA-enabled local development with CPU reference/fallback**

### Tasks

1. Re-read Section 2 and Figure 3 of the supplied paper, and consult reference [20] as needed.
2. Implement the baseline independently as a function that returns:
   - reversible gate sequence `G_baseline`;
   - label map `f_baseline`;
   - transformed tableau;
   - per-operation trace;
   - emitted resource counts.
3. Implement the two logical cases:
   - a row already has zero residual bits and can retain its subspace label if unoccupied;
   - a row outside the subspace is transformed to a fresh subspace label and one-hot residual state, then its remaining residual `1` is zeroed using the multi-controlled-X construction.
4. Make fresh-label selection explicit. Never assign a label that collides with an existing row that must stay distinct.
5. Implement the AND-ladder MCX-to-Toffoli cost model using the paper's stated assumptions. Keep abstract MCX and decomposed costs as separate fields.
6. Build the inverse by reversing gate order and applying inverse operations. Verify exact support-row reversibility.
7. Reproduce the paper's worst-case baseline expression:

   ```text
   T_baseline = s * (ell - 1)
   ancillas   = ell - 2   # under the paper's AND-ladder assumptions, for ell >= 2
   ```

8. Compare actual emitted counts with the worst-case expression. Do not require every instance to attain the worst case.
9. Compare the independent result against the official artifact on small cases where the output conventions are comparable.
10. Record any baseline construction convention that affects label assignment or MCX decomposition.

### Deliverables

- `candidate_ai/src/sparseprep/algorithms/malvetti.py`.
- `candidate_ai/tests/test_malvetti.py`.
- `results/baseline_smoke_tests.json`.
- `research-notes/baseline-cost-model.md`.

### Exit gate

All tested support rows map to distinct labels with zero residual bits, the inverse restores each original state, and the resource counter can explain every Toffoli in the selected decomposition.

---

## Phase 5 — Restricted and unrestricted PUI / Algorithm 2

**Budget: 9 focused hours**  
**Primary machine: RTX 3050 CUDA for batches of independent truth-table checks; CPU remains the exact reference; Kaggle is available for larger sweeps**

### Tasks

1. Re-read Section 3 and Figures 6–7. Reconstruct the full balanced-tree unary iteration before implementing the partial versions.
2. Define recursive state explicitly: current interval, split bit, inherited control, free/omitted address bits and leaf operation.
3. Implement **restricted PUI** first. It must apply `U_i` only for addresses in `[l,r]` and act trivially outside the interval.
4. Exhaustively test restricted PUI for all address values at small widths (`w` up to 5 or 6, subject to actual runtime).
5. Implement **unrestricted PUI** using Algorithm 2. Handle all three recursion cases:
   - left and right halves both intersect the requested interval;
   - only the left half intersects: omit the split-bit control and add that bit to `free`;
   - only the right half intersects: select the right half and recurse.
6. At each leaf, generate the exact extra-address set `L` and mapping `g` from the free-bit combinations. Do not approximate the side effects.
7. Exhaustively check all `2**w` addresses for every tested interval:
   - addresses in `[l,r]` receive the intended operations;
   - addresses below `l` remain untouched;
   - extra addresses above `r` receive exactly the operation prescribed by `g`;
   - all other addresses remain unchanged.
8. Provide a truth-table reference evaluator independent of the recursive circuit compiler. The circuit compiler and evaluator must not share the same branch implementation; otherwise a shared bug could pass both tests.
9. Connect PUI metadata to the tableau updater. Algorithm 1 must receive the actual effect on all rows, not just the intended batch.
10. Re-derive Equations (5)–(8) from the Hamming-weight/prefix-counting argument. Use `q = log2(m)` in the guide and code comments to distinguish the PUI subtree depth from `ell`.
11. Reconstruct Equation (1) using the paper's equations while preserving the page-6 correction-cost inconsistency. Do not silently patch a `+/-2` term.
12. Compare emitted gate counts with analytical counts only when the decomposition, controls, ancillas and measurement-based-uncomputation assumptions match.

### Hardware notes

- The independent CPU truth-table evaluator is the correctness oracle for small exhaustive PUI tables.
- The RTX 3050 CUDA backend is a required tested backend for batches of independent truth tables/intervals and parameter sets. It is not expected to accelerate the branch-heavy recursive circuit-construction control flow itself.
- On the 3050, use CUDA for batches of independent intervals and bound VRAM use. Keep the CPU reference evaluator available and compare exact outputs. Do not upload the whole experiment matrix if it can be streamed.
- On Kaggle, record the actual accelerator and export every result. Do not assume that two T4 GPUs automatically accelerate one recursive PUI instance.

### Deliverables

- `candidate_ai/src/sparseprep/pui/restricted.py`.
- `candidate_ai/src/sparseprep/pui/unrestricted.py`.
- `candidate_ai/src/sparseprep/pui/costs.py`.
- `candidate_ai/tests/test_pui_exhaustive.py`.
- `research-notes/pui-resource-derivation.md`.
- Small truth-table artifacts in `results/pui_truth_tables/`.

### Exit gate

Both PUI variants match their independent truth-table definitions for every tested address. `L` and `g` are exact and logged. Resource formulas have explicit assumptions and are not mixed with emitted gate counts.

---

## Phase 6 — Batched isometry / Algorithm 1

**Budget: 8 focused hours**  
**Primary machine: RTX 3050 CUDA for suitable independent bulk operations; CPU reference for correctness; Kaggle for larger batches if local VRAM or runtime is limiting**

### Tasks

1. Translate Algorithm 1 (PDF page 19) into a plain-language state machine before coding. Document `k`, `batch`, current batch size `b`, maximum batch size `m`, tableau and exit conditions.
2. Implement the batch-size rule: `m` is the largest power of two no greater than `n - ell`, subject to valid residual-register requirements.
3. Implement formation of structured batches:

   ```text
   (|k>_s |e_0>_r, |k+1>_s |e_1>_r, ..., |k+m-1>_s |e_(m-1)>_r)
   ```

4. Implement the first batch element using the correct multi-target controlled-X operation.
5. Implement subsequent ordinary CMX batch additions.
6. Implement the SWAP path when a required residual `1` exists further to the right.
7. Implement the difficult path when no suitable later residual `1` exists:
   - select an unprocessed state;
   - identify the appropriate batch state;
   - find a differing bit position;
   - apply the correct positive- or negative-control Toffoli;
   - apply the required CMX to create the next batch state.
8. Invoke the tested PUI compiler from Phase 5. Never use a placeholder that simply zeroes the batch and claim it is PUI.
9. Update every tableau row according to the **actual** PUI action, including unrestricted-PUI effects on addresses above the requested interval.
10. Implement partial final-batch handling. If non-batch rows already occupy relevant subspace labels, use the restricted final PUI/correction logic described in Section 2 rather than assuming unrestricted PUI has no side effects.
11. Extract the final bijection `f` from the final tableau.
12. Save a complete construction trace: batch members, chosen row, gate operations, PUI interval, all changed rows and final labels.
13. Build `to_subspace` and `from_subspace` APIs with unambiguous directionality:

   ```text
   G |C_i> = |f(i)>_subspace |0>_residual
   G† (|f(i)>_subspace |0>_residual) = |C_i>
   ```

### Required cases

- One complete batch.
- Multiple complete batches.
- Complete batch plus partial final batch.
- A row already in the subspace.
- Duplicate initial subspace prefixes.
- SWAP branch triggered.
- Positive-control Toffoli branch triggered.
- Negative-control Toffoli branch triggered.
- Restricted final correction branch triggered.
- An unrestricted-PUI side effect on a later address is propagated correctly.

### Deliverables

- `candidate_ai/src/sparseprep/algorithms/batched_isometry.py`.
- `candidate_ai/tests/test_batching.py`.
- `results/batch_traces/` with at least three readable traces.
- Circuit diagrams for one ordinary and one difficult batch.

### Exit gate

The final mapping is total and injective over the support, every residual register is zero, the tableau trace accounts for every row mutation, and the inverse returns every tested support state exactly.

---

## Phase 7 — Algorithm 3: real-state sign fixing

**Budget: 4 focused hours**  
**Primary machine: RTX 3050 laptop; CUDA-enabled local development with CPU reference/fallback**

### Tasks

1. Re-read the page-13 discussion and Algorithm 3 on PDF page 21.
2. Add a separate sign input `a_i` in `{+1,-1}`. Do not represent arbitrary complex phases as signs.
3. Extend the tableau with the marker ancilla initialized to `|1>` for each row as specified in Algorithm 3.
4. Use the restricted-PUI variant required by Algorithm 3.
5. Track marker changes and ensure that no row is silently skipped.
6. Implement counter-effect corrections on earlier batch rows and the marker-controlled operation for the next batch element.
7. Verify the sign-aware mapping:

   ```text
   G |C_i> = a_i |f(i)>_subspace |0>_residual
   ```

8. Test all-positive, all-negative, alternating and seeded-random sign patterns on small supports.
9. Verify inverse mapping and phase convention.
10. If the entire Algorithm 3 cannot be completed in four hours, preserve a correct subset, list the precise unimplemented branches, and mark the feature partial. Do not fake full support.

### Deliverables

- `candidate_ai/src/sparseprep/algorithms/phase_fixing.py`.
- `candidate_ai/tests/test_phase_fixing.py`.
- `research-notes/real-state-phase-fixing.md`.

### Exit gate

All implemented sign cases pass exact phase-aware basis-action tests. The report states exactly whether Algorithm 3 is complete or partial.

---

## Phase 8 — Correctness campaign and hardware-aware benchmarks

**Budget: 10 focused hours**  
**Primary environment: RTX 3050 laptop; Kaggle for GPU-portability/online benchmarks; workstation and DGX-1 only for short optional runs**

### A. Correctness campaign

For every case, verify:

1. Support strings are distinct and have exactly `n` bits.
2. `ell`, `tilde_s` and `m` are computed correctly using integer-safe logic.
3. Every batch has no more than `m` rows.
4. Every batch has the expected one-hot residual structure before PUI.
5. Restricted and unrestricted PUI match their independent truth-table specifications.
6. Every unrestricted side effect is propagated into the tableau.
7. Every final residual register is all zero.
8. The final label map is injective.
9. The inverse gate sequence exactly restores each original state.
10. Algorithm 3 preserves signs for every implemented case.
11. CPU and GPU implementations produce identical discrete outputs where a GPU kernel is implemented.
12. Statevector fidelity is reported only for small circuits and only if the simulation faithfully models all operations used. For measurement/feedforward constructions, exact basis-action/phase checks may be the more appropriate proof.

### B. Benchmark sizing policy

The paper states classical isometry-finding complexity `O(s^2 n)`. A 16 GB laptop should not be assigned an unbounded `s=10^5` campaign by default. Benchmark sizes must grow through measured checkpoints and stop when memory or runtime limits are approached.

**Correctness matrix (mandatory):**

```text
s in {4, 5, 8, 13, 16, 31, 32, 64, 100, 128, 256}
```

Choose valid `n` values that produce useful residual widths/batch sizes. Include small hand-crafted cases for all difficult branches.

**Performance matrix (progressive):**

```text
s in {256, 512, 1_000, 2_000, 5_000}
```

Attempt larger cases such as `10_000` only after the preceding run completes within a reasonable memory/time budget. Do not promise `10^5+` for the paper's `O(s^2 n)` tableau algorithm. If an optimized data-parallel subroutine scales further, report that subroutine separately from end-to-end algorithm runtime.

Run at least five deterministic seeds for selected random support configurations. Use hand-crafted structured supports in addition to random ones.

### C. Workload-specific execution plan

**RTX 3050 laptop (primary):**

- Run all unit and correctness tests against the independent CPU reference.
- Run the CUDA backend smoke tests and CPU/GPU parity suite on the RTX 3050.
- Run exhaustive small PUI truth tables on CPU, then batch independent truth-table/interval cases on CUDA.
- Run baseline and batched benchmarks through the moderate support matrix; keep sequential algorithm control flow on CPU and offload only suitable bulk kernels.
- Profile host RAM and 6 GB VRAM; chunk CUDA workloads and record transfer time separately from kernel time.
- Keep the CPU implementation as the correctness oracle and automatic fallback, not the only local backend.

**Kaggle (online GPU):**

- Run a hardware probe first and save the actual GPU model, memory, driver and package versions.
- Verify GPU availability with `nvidia-smi` and a minimal framework/kernel smoke test.
- Run the same seeded support configurations as local for CPU/GPU parity.
- Use GPU for independent support instances, bit-packed matching, batched truth-table verification and other measured parallel workloads.
- Keep a CPU reference/fallback path and compare CUDA outputs against it exactly.
- Save all outputs to persistent Kaggle artifacts or download them. Do not leave the only result copy in the ephemeral runtime.
- Record accelerator type and count for each run. Kaggle T4 x2 is two separate GPUs; multi-GPU execution must be explicit.

**RTX 5060 Ti workstation (optional short run):**

- Run the hardware probe and one matched configuration already measured on the 3050.
- Run one larger-memory/throughput configuration only if it answers a defined question.
- Save logs and raw outputs using the same schema.
- Do not move development to this machine or make it a dependency for completion.

**SRM AP DGX-1 (optional institutional run):**

- Obtain permission and a short reservation from the facility administrator/faculty in-charge.
- Before submitting jobs, record `nvidia-smi`, all eight GPU models and memory sizes, driver/CUDA versions, CPU, system RAM and device visibility.
- Start with one V100 and run a matched small/medium benchmark from the same configuration file.
- Test 2/4/8 GPUs only for workloads that can be partitioned into independent instances or independent verification batches.
- Compare scaling against one V100 and record communication/launch overhead. Do not assume linear speed-up.
- Do not use the DGX-1 to run full statevectors for large `n`; the Hilbert-space dimension remains exponential.
- If access is not granted, list DGX-1 experiments as `not run — access unavailable`. The project remains complete without DGX-1 results.

### D. Required metrics

| Metric | Exact meaning | Rule |
|---|---|---|
| `toffoli_actual` | Toffoli gates in emitted circuit under declared decomposition | Measured from gate IR/resource counter |
| `toffoli_bound` | Paper analytical upper bound | Calculated separately from emitted count |
| `toffolis_per_s` | `toffoli_actual / s` | Label algorithm variant |
| `improvement_ratio` | Baseline actual / batched actual | Use comparable decomposition assumptions |
| `ancilla_count` | Maximum additional live workspace | State clean/dirty assumptions |
| `pui_calls` | Number of emitted PUI instances | Separate restricted/unrestricted |
| `batch_count` | Number of batches including final partial batch | Save final-batch size |
| `classical_compile_seconds` | Wall-clock circuit construction time | Not quantum runtime |
| `cpu_time_seconds` | CPU execution time for the selected workload | Record thread count |
| `gpu_time_seconds` | GPU kernel/workload time | Exclude or separately report transfers and compilation |
| `peak_host_ram_mb` | Measured peak host memory | Record measurement method |
| `peak_gpu_memory_mb` | Measured peak accelerator memory | Use device telemetry where available |
| `fidelity` | Small-statevector fidelity | Only when the simulated operation is faithful |
| `backend` | Actual backend used | `cpu`, `cuda:<device>`, etc.; never requested backend only |

### E. Benchmark hygiene and raw-data schema

- Fix and save random seeds.
- Record `n`, `s`, `ell`, `m`, support family, algorithm variant and exact configuration hash.
- Record OS, CPU, RAM, GPU name, VRAM, driver, CUDA version, Python/Rust version, package versions and thread count.
- Warm up GPU kernels; measure kernel time separately from host-to-device/device-to-host transfers.
- Use repeated runs and report median plus spread (min/max or interquartile range).
- Save one raw JSONL record per run under `results/raw/`.
- Generate `results/summary.csv` from raw records using a script.
- Every figure must be regenerated from raw records, never manually entered values.
- Store exceptions and OOM/timeout/unsupported-device outcomes in `results/exceptions.csv`.
- Label all result groups: measured locally, measured on Kaggle, measured on workstation, measured on DGX-1, analytically derived, or not run.

### Deliverables

- `benchmarks/configs/` with versioned exact experiment definitions.
- `results/raw/*.jsonl`.
- `results/summary.csv`.
- `results/exceptions.csv`.
- `results/figures/` including:
  - Toffolis per support size for baseline and batched algorithms;
  - improvement ratio for matched configurations;
  - actual emitted count versus Equation (1) upper bound;
  - restricted versus unrestricted PUI cost;
  - ancilla/Toffoli trade-off;
  - classical construction time versus `s`;
  - local 3050 versus Kaggle and optional workstation/DGX timing only for identical configurations.
- `tests/test_end_to_end.py`.

### Exit gate

Every plotted point maps to a raw record. Every correctness failure is fixed or listed. CPU/GPU output parity passes for implemented kernels. No empirical result is represented as a worst-case theorem, and no unexecuted device is shown as benchmarked.

---

## Phase 9 — Analysis, technical report and release

**Budget: 8 focused hours**  
**Primary machine: RTX 3050 laptop; optional report render on 5060 Ti workstation**

### A. Report title

*Independent Implementation and Hardware-Aware Resource Audit of Batched Isometry Construction for Sparse Quantum State Preparation*

### B. Report structure

Target 12–18 substantive pages. Do not inflate the report with unanalysed screenshots.

1. Executive summary.
2. Problem formulation and sparse-state notation.
3. Two-stage preparation architecture and isometry direction.
4. Malvetti baseline implementation.
5. Restricted/unrestricted PUI derivation and `L,g` bookkeeping.
6. Algorithm 1 batch construction and bit-level traces.
7. Algorithm 3 sign fixing, with tested coverage.
8. Independent software architecture and gate IR.
9. Correctness invariants and test design.
10. Hardware/software environment and memory constraints.
11. Benchmark methodology and raw-data schema.
12. Results: 3050 local, Kaggle, optional 5060 Ti and optional DGX-1 as separate measured environments.
13. Comparison with theoretical bounds and the authors' reference artifact.
14. Source-paper discrepancies and how they were handled.
15. Limitations, incomplete work and potential next experiments.
16. Brief related-work note on later sublinear-T-count papers; clearly distinguish T-count from Toffoli-count models.
17. Conclusion.

### C. Reproducibility package

Suggested final layout:

```text
sparse-state-preparation/
├── README.md
├── pyproject.toml
├── reference/                  # untouched authors' artifact
├── candidate_ai/               # candidate implementation under validation
├── research-notes/
│   ├── SOURCES.md
│   ├── scope-and-assumptions.md
│   ├── pui-resource-derivation.md
│   └── source-consistency.md
├── environment/
│   ├── laptop-hardware.json
│   ├── kaggle-hardware.json
│   ├── workstation-hardware.json    # only if run
│   └── dgx1-hardware.json           # only if run
├── benchmarks/
│   └── configs/
├── results/
│   ├── raw/
│   ├── summary.csv
│   ├── exceptions.csv
│   └── figures/
├── tests/
├── notebooks/
├── report/
│   ├── technical_report.md
│   ├── technical_report.html
│   └── technical_report.pdf          # optional if rendering succeeds
└── scripts/
    ├── hardware_probe.py
    ├── run_tests.sh
    ├── run_local_benchmarks.sh
    ├── run_kaggle_benchmarks.py
    ├── aggregate_results.py
    ├── regenerate_figures.sh
    └── final_audit.sh
```

Adjust paths to actual code; do not create empty directories merely to match the diagram.

### D. README requirements

- Full paper citation and link.
- Explicit statement that `candidate_ai/` is a candidate implementation generated with coding-agent assistance and subsequently validated; do not describe unverified features as complete.
- Clear separation between the authors' reference artifact and candidate code.
- Setup commands for the RTX 3050 CUDA-enabled environment, including the tested driver/runtime/library combination.
- A separate CPU-only fallback installation for portability and recovery.
- Kaggle notebook instructions and required uploaded/downloaded artifacts.
- Optional RTX 5060 Ti and DGX-1 run instructions.
- One-command unit test, correctness test and small benchmark procedures.
- Exact commands for regenerating plots from raw data.
- Known limitations and incomplete components.
- Source attribution and license information.

### E. Demonstration

Prepare a concise 5–8 minute demonstration:

1. Show a sparse-support input.
2. Show the Malvetti baseline mapping.
3. Show one batched-isometry run.
4. Show one restricted/unrestricted PUI interval and its side-effect bookkeeping.
5. Run the correctness checks.
6. Show actual Toffoli/ancilla comparison and one raw-data-backed plot.
7. State one limitation and one evidence-backed follow-up question.

### Exit gate

A clean environment can run the documented base tests and at least one benchmark. The report tables and plots match saved raw outputs. All claims are classified as paper statements, independent measurements, derivations, interpretations or incomplete work.

---

# 5. Architecture and coding rules

## 5.1 Three-layer software architecture

1. **Classical algorithm layer:** support parsing, tableau updates, batch formation, label allocation, interval decomposition and side-effect bookkeeping.
2. **Circuit IR layer:** explicit reversible gates and PUI macro/decomposition representation.
3. **Resource-accounting layer:** emitted gate counts, ancilla lifetimes and analytical bounds as separate outputs.

The AI coding agent must not collapse these layers into one large function. They are deliberately separated so a mismatch can be traced to algorithm logic, circuit emission or resource accounting.

## 5.2 Keep three codebases/roles separate

- `reference/`: authors' untouched artifact.
- `candidate_ai/`: code produced by Claude and validated during this candidate sprint.
- A later human implementation: create a fresh repository or branch from a written specification; do not copy candidate source files into it.

The later human version may use the candidate's tests as externally specified test cases if their origin is disclosed, but it must implement the algorithm independently.

## 5.3 Directionality

The circuit finder constructs:

```text
G |C_i> = |f(i)>_subspace |0>_residual
```

The preparation operation applies:

```text
G† (|f(i)>_subspace |0>_residual) = |C_i>
```

Names should make the direction explicit (`to_subspace`, `from_subspace`).

## 5.4 Unrestricted-PUI bookkeeping is mandatory

An unrestricted PUI can apply operations to addresses above its intended interval. Store the extra-address set `L` and mapping `g`; test them exhaustively for small address widths; update all affected tableau rows. A routine that zeroes only the intended batch is not an implementation of unrestricted PUI.

## 5.5 Resource accounting discipline

- Never count `CX` or `CMX` as Toffoli gates.
- Keep abstract MCX separate from its AND-ladder decomposition.
- Record clean and dirty ancilla assumptions.
- Record measurement-based uncomputation assumptions.
- Do not compare a custom abstract count with a Qualtran decomposition count until the models are aligned.
- Keep classical compilation time separate from quantum resource estimates.

---

# 6. Acceptance criteria

## 6.1 Mandatory core acceptance

- [ ] Source files and official artifact version are recorded with checksums.
- [ ] Authors' artifact remains unchanged.
- [ ] RTX 3050 CUDA environment passes device discovery, a real kernel smoke test and CPU/GPU parity tests.
- [ ] CPU-only fallback installation and tests also work without CUDA.
- [ ] Baseline mapping and inverse tests pass.
- [ ] Restricted PUI truth tables pass for all tested small widths/intervals.
- [ ] Unrestricted PUI truth tables pass and `L,g` are exact.
- [ ] Algorithm 1 passes normal CMX, SWAP, positive/negative Toffoli and final partial-batch tests.
- [ ] Every final residual register is zero.
- [ ] Final label map is injective.
- [ ] Inverse operation restores all tested rows exactly.
- [ ] Algorithm 3 is either verified on stated sign cases or explicitly marked partial.
- [ ] Benchmark raw data and plot-generation scripts are saved.
- [ ] Every benchmark entry records the actual machine/backend.
- [ ] Report separates analytical bounds from measured counts.

## 6.2 Optional hardware acceptance

- [ ] Kaggle GPU smoke test and CPU/GPU parity test run successfully.
- [ ] RTX 5060 Ti matched benchmark completed, if convenient access is available.
- [ ] DGX-1 single-V100 test completed, if institutional permission is granted.
- [ ] DGX-1 multi-GPU comparison run only if the measured workload has independent parallelism.

Failure to obtain Kaggle, workstation or DGX access does not invalidate the core implementation. It must simply be documented as not run.

---

# 7. Risk register and fallback decisions

| Risk | Consequence | Response |
|---|---|---|
| 3050 VRAM or 16 GB RAM is insufficient | OOM, swapping, slow tests | Keep the CPU reference/fallback; reduce support size; chunk arrays; avoid dense statevectors; offload larger independent CUDA batches to Kaggle; use the 5060 Ti/DGX only for justified short experiments |
| CUDA driver/library mismatch | GPU backend unavailable on the laptop despite CUDA-capable hardware | Diagnose driver/runtime/library compatibility; preserve the CPU reference/fallback; record the exact environment; use Kaggle to distinguish a local setup issue from a code issue |
| Kaggle accelerator unavailable or quota exhausted | Online GPU tests delayed | Continue CPU tests locally; save experiment configs for a later Kaggle session |
| Kaggle session resets | Lost temporary output | Checkpoint often; export raw JSONL/CSV and notebook versions |
| Official artifact dependency/build failure | Reference comparison blocked | Preserve original folder; capture logs; use a separate environment or Kaggle; continue independent small-case tests |
| Qualtran API/version drift | Bloq integration consumes time | Keep the gate IR/resource counter independent; mark Qualtran cross-check secondary |
| Rust build failure | Official accelerated isometry unavailable | Record failure; use artifact's Python components where possible; do not copy Rust source into candidate code |
| Algorithm 1 corrupts tableau | Wrong mapping | Save row-by-row trace; minimize failing support; use Buffer B; fix before benchmarks |
| Unrestricted PUI map is wrong | Later batches become invalid | Exhaustively compare recursive PUI with independent truth-table evaluator |
| Algorithm 3 exceeds budget | Real-state feature incomplete | Protect Algorithm 1/2; document exact unsupported branches |
| RTX 5060 Ti access is inconvenient | No local workstation comparison | Skip without changing the plan; 3050 + Kaggle remain sufficient |
| DGX-1 permission is delayed | No institutional HPC result | Treat as optional final run; report `not run — access unavailable` |
| Multi-GPU scaling is poor | Communication overhead dominates | Report negative/neutral result; do not manufacture speed-up; use DGX for independent jobs instead |
| Page-6 equation discrepancy | Constant-term mismatch | Preserve printed source expression; count emitted gates; explain ambiguity explicitly |
| Page-13 Figure 9 label inversion | Misattribution of Algorithm 1/3 | Flag caption; use surrounding prose, Algorithm 3 pseudocode and Figure 10 as cross-check; state resolution in report |
| Benchmark variance | Unsupported conclusion | Fixed seeds, warm-up, repeated timings, thread-count record and median/spread reporting |

---

# 8. Source-specific issues to preserve

The supplied paper and study guide identify two source inconsistencies. They must be preserved in the source audit rather than silently repaired.

## 8.1 PDF page 6 — Equation (3) correction-cost mismatch

On PDF page 6, the prose states a correction cost of `ceil(log2(s)) + 1` and equates it to `log2(tilde_s / 2)`. With `tilde_s = 2^ell` and `ell = ceil(log2(s))`, that equality is arithmetically inconsistent:

```text
log2(tilde_s / 2) = ell - 1
log2(2 * tilde_s) = ell + 1
```

The left-hand expression is `ell + 1`; the printed logarithm evaluates to `ell - 1`, a difference of two. If the intended logarithm were `log2(2 * tilde_s)`, it would evaluate to `ell + 1`. Do not silently replace the printed source expression. Keep the prose claim, printed logarithm, Equation (3) and actual emitted correction-gate count separately visible in the source audit.

## 8.2 PDF page 13 — Figure 9 Algorithm 1/3 caption labels

The Figure 9 caption appears to invert the Algorithm 1 and Algorithm 3 labels. The surrounding Section 4 prose, Algorithm 3 pseudocode on page 21 and Figure 10 caption on page 14 support the interpretation:

- Algorithm 1: unrestricted-PUI batching.
- Algorithm 3: restricted-PUI phase-fixing variant.

Flag the Figure 9 caption and document why this interpretation was used.

## 8.3 Later sublinear-T-count work

The paper references later results:

- Tongyang Li et al., *Optimal T Counts under Sparsity: from QROM to State Preparation and Block Encoding*, arXiv:2607.28260.
- Jingquan Luo and Lvzhou Li, *Sparse Quantum State Preparation with Sublinear T-Count*, arXiv:2608.00414.

Mention them in related work, but do not implement them in this sprint. Their T-count results must not be numerically conflated with Rupprecht–Wölk's Toffoli-count analysis without aligning the decomposition, approximation precision, ancilla assumptions and what portion of state preparation is counted.

---

# 9. Required report tables and figures

## Tables

1. **Implementation coverage:** component, status, test coverage and remaining gaps.
2. **Correctness matrix:** support family, `(n,s,ell,m)`, row count, injectivity, zero residual, inverse check, sign check and status.
3. **Resource comparison:** baseline emitted Toffolis, batched emitted Toffolis, analytical bound, ancillas, PUI calls and batch count.
4. **Environment matrix:** laptop, Kaggle, optional workstation and optional DGX hardware/software specifications actually detected.
5. **Benchmark summary:** median runtime, spread, peak RAM/VRAM, actual backend and configuration ID.
6. **Exceptions:** OOM, unsupported accelerator, timeout, test failure and unrun optional hardware cases.

## Figures

- `Toffolis/s` versus support size for baseline and batched methods.
- Improvement ratio on matched configurations.
- Actual emitted Toffoli count versus Equation (1) analytical upper bound.
- Restricted versus unrestricted PUI count.
- Ancilla/Toffoli trade-off.
- Classical construction time versus `s`.
- Local 3050 versus Kaggle and optional workstation/DGX matched benchmark, only where configurations are identical.
- DGX-1 1/2/4/8 GPU scaling plot only if those runs actually complete.

All plots must be generated from saved raw data by scripts.

---

# 10. Reproducibility commands and operating procedure

## 10.1 Local laptop baseline

The project must make the RTX 3050 CUDA backend the normal local acceleration path, with an explicit CPU reference/fallback option. The hardware probe must verify the device and a real kernel before CUDA benchmark results are recorded:

```bash
# Environment and hardware record
python scripts/hardware_probe.py --output environment/laptop-hardware.json

# Install development dependencies and the tested CUDA extra for the RTX 3050
python -m pip install -e ".[dev,cuda]"

# Verify the RTX 3050 is visible to the selected Python CUDA library
python scripts/hardware_probe.py --check-cuda --output environment/laptop-hardware.json

# Run unit and exact correctness tests against the CPU reference
pytest -q

# Run CUDA smoke/parity tests and a small deterministic CUDA benchmark
pytest -q tests/test_cuda_backend.py tests/test_backend_parity.py
python -m sparseprep.benchmark --config benchmarks/configs/smoke.yaml --backend cuda

# Explicit CPU reference/fallback benchmark for matched comparison
python -m sparseprep.benchmark --config benchmarks/configs/smoke.yaml --backend cpu

# Aggregate raw outputs and regenerate plots
python scripts/aggregate_results.py
python scripts/regenerate_figures.py
```

The precise CLI may differ, but the README must provide equivalent working commands.

## 10.2 Kaggle run

1. Upload or clone the repository and pinned experiment configurations.
2. Select an available GPU accelerator in Notebook settings.
3. Run the hardware probe first.
4. Run a GPU smoke kernel and confirm the detected device is used.
5. Run a short parity benchmark using the same seed/config as a laptop test.
6. Run selected larger independent jobs only if the smoke test is correct and VRAM permits.
7. Export logs and result artifacts before ending the session.

## 10.3 RTX 5060 Ti workstation run

1. Run the same hardware probe.
2. Install the CUDA extra matching the detected NVIDIA driver and selected library; do not assume a system-wide CUDA toolkit is required if the chosen wheel bundles a compatible runtime.
3. Run one matched workload from the local benchmark configuration.
4. Save raw outputs with the same schema.
5. Do not modify algorithm code between the 3050 and 5060 Ti runs unless the change is separately versioned and reported.

## 10.4 DGX-1 run

1. Obtain written/recorded permission and a slot from the appropriate SRM AP facility administrator or faculty in-charge.
2. Confirm user account, job policy, data restrictions, software modules/containers, storage quota and allowed wall time.
3. Record the exact DGX configuration using `nvidia-smi`, CPU/RAM probes and CUDA/NCCL version commands.
4. Run one GPU first and validate output parity against the laptop.
5. Run 2/4/8 GPU tests only on partitionable workloads.
6. Record per-GPU utilization, per-device memory, inter-GPU communication time and total runtime if tools are available.
7. Export results securely and cite the actual facility configuration in the report.

---

# 11. Final audit checklist

Before calling this project complete:

- [ ] All source files and versions are identified and hashed.
- [ ] The reference artifact remains unchanged.
- [ ] `candidate_ai/` is separate from `reference/` and from the later human implementation.
- [ ] CUDA-enabled install and kernel smoke tests work on the RTX 3050 laptop.
- [ ] CPU-only install and tests also work as a portable fallback.
- [ ] Logs distinguish CUDA-capable hardware, driver visibility, Python runtime availability and successful kernel execution.
- [ ] All key algorithms have explicit implemented/partial/not-implemented status.
- [ ] Restricted and unrestricted PUI truth-table tests pass.
- [ ] The `L,g` extra-address bookkeeping is exact and tested.
- [ ] Algorithm 1 difficult batch branches and final-batch logic are tested.
- [ ] Algorithm 3 coverage is honestly documented.
- [ ] Every output label is injective and every residual register is zero.
- [ ] Inverse action is tested on all correctness supports.
- [ ] Theoretical bounds and emitted gate counts are separate.
- [ ] CX and CMX are not counted as Toffolis.
- [ ] Raw JSONL/CSV outputs exist and regenerate every plot.
- [ ] Every run records actual hardware and backend.
- [ ] Kaggle, workstation and DGX results are shown only if actually executed.
- [ ] The two source inconsistencies are discussed.
- [ ] The report does not conflate T-count and Toffoli-count results.
- [ ] The README reproduces at least one smoke test and benchmark from a clean environment.
- [ ] No unsupported claim of “100% accuracy”, “linear scaling”, “GPU acceleration” or “multi-GPU speed-up” remains.

---

# 12. External references used for the hardware plan

These sources supplement the equipment description supplied by the user. Hardware configurations and service availability must still be checked at runtime.

1. **Kaggle staff announcement — P100 retirement and T4 x2 availability.** Kaggle stated that P100 would be retired on 15 September 2026 and that T4 x2 would remain an accelerator option. This is why the plan detects the actual accelerator rather than assuming P100 or T4 x2 is always available.  
   <https://www.kaggle.com/product-announcements/735239>

2. **Kaggle Notebook documentation.** Explains hosted GPU notebooks, accelerator selection, session resources and the need to manage GPU usage. The exact quota and available accelerator should be checked in the account UI at run time.  
   <https://www.kaggle.com/docs/notebooks>

3. **NVIDIA DGX-1 product page.** NVIDIA describes the DGX-1 as an eight-GPU V100 system and quotes NVLink interconnect bandwidth up to 300 GB/s per GPU. This is peak interconnect specification, not a promise of this project's measured throughput.  
   <https://www.nvidia.com/en-in/data-center/dgx-1/>

4. **NVIDIA DGX-1 V100 architecture white paper.** Describes the eight-GPU hybrid cube-mesh topology and multi-GPU collective communication behaviour. Useful background for deciding which workloads are worth distributing.  
   <https://images.nvidia.com/content/pdf/dgx1-v100-system-architecture-whitepaper.pdf>

5. **Rupprecht and Wölk (2026), primary paper.** All algorithmic equations, conventions and paper-specific claims must be checked against the supplied journal PDF.  
   <https://quantum-journal.org/papers/q-2026-09-10-2208/>

6. **Official authors' code and assets.** Use as the isolated reference implementation, not as source code to copy into the candidate.  
   <https://zenodo.org/records/18234600>

---

# Final operating principle

**Develop primarily on the CUDA-capable RTX 3050. Use CUDA locally for suitable parallel kernels and retain CPU as the correctness reference/fallback. Use Kaggle for online GPU capacity when the 3050's 6 GB VRAM or runtime is limiting. Use the RTX 5060 Ti only for convenient short comparisons. Use the SRM AP DGX-1 as an optional final institutional experiment, starting with one V100 and scaling only where the workload genuinely parallelizes.**

The algorithm must remain correct and reproducible without the 5060 Ti or DGX-1. Additional hardware is useful only when it answers a defined experimental question.
