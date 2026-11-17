"""Render the current SIRIUS validation report from immutable run JSONL data."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/phase9_repair/runs/sirius_repair_validation_20261117"
REPORT = ROOT / "docs/research/FINAL_VALIDATION_REPORT.md"
METHODS = {
    "independent_batched_isometry",
    "malvetti_baseline",
    "end_to_end_state_preparation",
    "authors_reference_artifact",
}


def read_records() -> list[dict]:
    records = []
    for path in sorted((EVIDENCE / "raw").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                record["_raw_file"] = path.name
                records.append(record)
    return records


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join("| " + " | ".join(row) + " |" for row in rows)


def historical_evidence() -> dict:
    """Summarize the immutable remote Phase 9.2 evidence commit, if fetched."""
    ref = "refs/remotes/origin/research/phase9-2-evidence-20261117-174621"
    base = "research/phase9_2/runs/sirius_research_closure_20261117_164817/raw/"
    result = {"commit": "3e6ff6142e2449f2877a7345666c324a9030bc2f", "available": False}
    try:
        subprocess.check_output(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=ROOT, stderr=subprocess.DEVNULL)
        def load(name: str) -> list[dict]:
            raw = subprocess.check_output(["git", "show", f"{ref}:{base}{name}"], cwd=ROOT)
            return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        cpu, e2e, gpu, authors = (load(name) for name in ("cpu_scaling.jsonl", "end_to_end_statevector.jsonl", "gpu_basis_rows.jsonl", "authors_differential.jsonl"))
        closure = json.loads(subprocess.check_output(["git", "show", f"{ref}:{base}closure_status.json"], cwd=ROOT))
        result.update({"available": True, "cpu_rows": len(cpu), "cpu_correct": sum(r.get("correctness_status") == "passed" for r in cpu),
                       "cpu_zero_timer_rows": sum(r.get("cpu_median_ms") == 0 for r in cpu),
                       "cpu_wall_ms_min": min(r["wall_median_ms"] for r in cpu), "cpu_wall_ms_max": max(r["wall_median_ms"] for r in cpu),
                       "e2e_rows": len(e2e), "e2e_statevector_pass": sum(r.get("statevector_status") == "passed" for r in e2e),
                       "e2e_cpu_zero_timer_rows": sum(r.get("cpu_median_ms") == 0 for r in e2e),
                       "gpu_rows": len(gpu), "gpu_parity_pass": sum(r.get("exact_cpu_gpu_parity") is True for r in gpu),
                       "gpu_scope": gpu[0].get("scope", "unspecified") if gpu else "none",
                       "authors_rows": len(authors), "authors_status_counts": dict(Counter(r.get("status", "missing") for r in authors)),
                       "closure_status": closure})
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return result


def main() -> None:
    records = read_records()
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in records:
        if row.get("plan_id") != "sirius-repair-matched-smoke-v1":
            continue
        provenance = row.get("provenance", {})
        identity = row.get("input_identity", {})
        groups[(provenance.get("source_diff_sha256", ""), identity.get("sha256", ""))].append(row)
    candidates = [
        (key, rows) for key, rows in groups.items()
        if {r["algorithm_id"] for r in rows if r.get("benchmark_configuration", {}).get("gpu_enabled") is False} >= METHODS
    ]
    if not candidates:
        raise SystemExit("No complete matched smoke group found in raw records")
    key, matched_all = max(candidates, key=lambda item: max(r["provenance"]["started_at_utc"] for r in item[1]))
    matched = [r for r in matched_all if r["benchmark_configuration"].get("gpu_enabled") is False and r["algorithm_id"] in METHODS]
    gpu = [r for r in matched_all if r["algorithm_id"] == "independent_batched_isometry" and r["benchmark_configuration"].get("gpu_enabled") is True]
    if len({r["algorithm_id"] for r in matched}) != len(METHODS):
        raise SystemExit("Matched group is incomplete")

    status_counts = Counter(r.get("status", "missing") for r in records)
    env = json.loads((EVIDENCE / "machine_manifest.json").read_text(encoding="utf-8"))
    input_support = matched[0]["input_identity"]["ordered_support"]
    table_rows = []
    for r in sorted(matched, key=lambda row: row["algorithm_id"]):
        timings, resources, correctness = r.get("timings", {}), r.get("logical_resources", {}), r.get("correctness", {})
        table_rows.append([
            r["algorithm_id"],
            f"{timings.get('compile_wall_ms', '—')}",
            f"{timings.get('compile_cpu_ms', '—')}",
            str(resources.get("paper_accounted_toffoli", "—")),
            str(resources.get("resource_scope", "isometry_only")),
            correctness.get("statevector_status", "not_applicable"),
            str(correctness.get("fidelity") if correctness.get("fidelity") is not None else "—"),
            timings.get("gpu_execution_status", "not_requested"),
        ])
    test_log = (EVIDENCE / "full_test_suite.log").read_text(encoding="utf-8")
    test_summary = next((line.strip() for line in reversed(test_log.splitlines()) if re.search(r"\d+ passed", line)), "summary line unavailable")
    build_log = (EVIDENCE / "package_build.log").read_text(encoding="utf-8")
    build_status = "PASS" if "Successfully built sirius-sparseprep" in build_log else "FAIL/NOT CONFIRMED"
    all_summary = json.loads((EVIDENCE / "all_attempts_summary.json").read_text(encoding="utf-8"))
    paired_summary = json.loads((EVIDENCE / "matched_smoke_summary.json").read_text(encoding="utf-8"))
    gpu_result = gpu[-1] if gpu else None
    historic = historical_evidence()
    historic_block = "Historical Phase 9.2 remote evidence was not available for this report generation."
    if historic["available"]:
        historic_block = f"""The previously pushed evidence branch was fetched read-only after the initial repository snapshot. Its immutable commit is `{historic['commit']}`. Per-case JSONL audit shows CPU {historic['cpu_correct']}/{historic['cpu_rows']} correctness passes; however, {historic['cpu_zero_timer_rows']}/{historic['cpu_rows']} rows have a zero CPU median timer (the wall-time medians range from {historic['cpu_wall_ms_min']} to {historic['cpu_wall_ms_max']} ms), so CPU medians from that run are not reliable. End-to-end statevector checks passed {historic['e2e_statevector_pass']}/{historic['e2e_rows']}, but all {historic['e2e_cpu_zero_timer_rows']} CPU timer medians were zero. Historical GPU basis-row execution had exact CPU/GPU parity for {historic['gpu_parity_pass']}/{historic['gpu_rows']} rows with scope `{historic['gpu_scope']}`. This is historical evidence from a different checkout and RTX 5060 Ti/CUDA environment; it does not validate the repaired runner in this Linux/no-GPU checkout. The historical authors lane has {historic['authors_status_counts']} across {historic['authors_rows']} rows and closure status `{historic['closure_status']['authors_build']['status']}` because Maturin executable discovery blocked extension build. These cases are not pooled with this run."""
    source_commit = matched[0]["provenance"].get("git_commit", "unknown")
    source_diff = matched[0]["provenance"].get("source_diff_sha256", "unknown")
    report = f"""# Final SIRIUS Validation Report

## Research objective and paper/artifact

Validate the local SIRIUS implementation of Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, Quantum (2026), DOI `10.22331/q-2026-09-10-2208`. The official artifact archive is pinned by MD5 `c58634ba415b4e3fb729648460f32ad7`; its SHA-256 is `4aa9ccdf5a4ae25f389e93dc8c9d7cada71f404f6a64d243038f374da81f6456`. The expected MD5 matches. The authors' package build via frozen `uv` workflow and ABI3 extension import passed.

## Source and environment

- Repository: `{ROOT}`
- Branch at inspection: `cleanup/phase9-2-modernization`
- HEAD used: `{source_commit}`
- Working tree: dirty during execution; tracked source diff SHA-256: `{source_diff}`
- Machine alias: `{env['machine_id']}`; OS `{env['os']['name']} {env['os']['version']}`; Python `{env['python']['version']}`; CPU `{env['cpu']['model']}`; RAM `{env['memory']['ram_total_bytes']}` bytes.
- GPU devices: `{json.dumps(env['gpu_devices'], sort_keys=True)}`. Software manifest is in `research/phase9_repair/runs/sirius_repair_validation_20261117/machine_manifest.json`.
- The evidence branch was absent from the local Git object database at the initial snapshot. It was subsequently fetched and audited read-only; its raw records were not copied over, modified, or pooled with this validation run.

## Algorithm implementation map

The sparse input contract is in `candidate_ai/src/sparseprep/model.py`; compact-label and batching construction in `batched_isometry.py`; the Malvetti baseline in `malvetti_baseline.py`; PUI models/tree emission in `pui.py` and `pui_tree.py`; Algorithm 3 and marker logic in `algorithm3.py`; phase synthesis in `phase_synthesis.py`; complete logical state preparation and exact CPU verification in `state_preparation.py`; CPU basis-row simulation in `simulator.py`; and optional CuPy basis-row execution in `backends/cupy_simulator.py`. Detailed status and test mapping is in `FINAL_REQUIREMENT_TRACEABILITY.md`.

## Corrections made

- Support hashing now preserves exact row order, width, framing and duplicate rejection. Versioned workload identity contains ordered support, coefficients, signs, family IDs, seed and generator/configuration metadata.
- Aggregation is stratified by input families, machine/runtime, benchmark/source configuration, artifact digest and metric; seed is the independent replication unit. Paired differences/ratios require matching input, seed, environment, configuration and artifact identity.
- CuPy runner now consumes compiled SIRIUS reversible gates, checks CPU parity, separates transfer/kernel/total timings and emits explicit unavailable/unsupported/failure states.
- Authors adapter validates artifact digest and mapping invariants; invalid underflowed `usize` counts are retained as raw data but are not published as Toffoli costs.
- Exact-statevector runner now calls the implemented API correctly, preserves exceptions, enforces the existing `2e-9` verifier tolerance and handles mathematical fidelity roundoff within [0,1]. Gate-list length is no longer mislabeled as depth. End-to-end stage resource counts are split by scope.
- Raw records use schema 1.1; historical schema 1.0 records remain readable. Summary schema 2.0 records failure states and paired comparisons.

## Tests and packaging

- Full regression suite: `{test_summary}`. Exact output is retained in `full_test_suite.log`; two CUDA execution tests were skipped because this host has no CUDA device. CPU-only unsupported-gate and wire-index checks executed.
- Syntax compilation and JSON schema parsing: PASS (`static_validation.log`).
- SIRIUS wheel build: {build_status}; output retained in `package_build.log`.
- Official artifact build/load: PASS using the artifact's frozen `uv` build workflow; `python -m maturin --version` is absent from the runtime interpreter, but this did not block package build or extension import.

## Matched benchmark smoke and actual results

The structured records below were generated from the same ordered support `{json.dumps(input_support)}`, identical coefficient/sign arrays and seed, on the same machine. Plan: `sirius-repair-matched-smoke-v1`, `n={matched[0]['problem']['n']}`, `s={matched[0]['problem']['s']}`, seed `{matched[0]['seed']}`, one measured repetition. These are smoke observations, not a statistically powered performance comparison.

{markdown_table(['Algorithm', 'Compile wall ms', 'Compile CPU ms', 'Paper-accounted Toffoli', 'Resource scope', 'Statevector status', 'Fidelity', 'GPU lane'], table_rows)}

Matched record count: {len(matched)}; distinct full input identities: {len({r['input_identity']['sha256'] for r in matched})}; paired summary groups: {len(paired_summary['paired_comparisons'])}. The one-seed sample does not justify confidence intervals or general performance conclusions. Summary is regenerated from raw records at `matched_smoke_summary.json`.

Separate GPU request: `{gpu_result['timings'].get('gpu_execution_status') if gpu_result else 'NOT_RUN'}`. Device detail: {gpu_result['timings'].get('gpu_error', 'no GPU record') if gpu_result else 'no GPU record'}. No GPU algorithm execution, GPU parity, throughput, or statevector claim is made.

## Reference validation

Artifact integrity: PASS. Extension build/import: PASS. Mapping fixture invariants: PASS on tested supported inputs. One matched smoke reference workload completed. Reference API returns a mapping and resource upper bound, not a directly executable primitive gate sequence; therefore the report does not claim reference gate-by-gate parity. The official `BatchZeroingData::num_toffolis()` has an observed unsigned underflow path (`changing_size - 2` at size 1); raw wrapped values are marked `suspected_usize_underflow`. Resource agreement is not established across all tested fixtures.

## Audit of the immutable earlier evidence branch

{historic_block}

## All attempts, failures and omissions

Across all preserved iterations in `raw/`, there are {sum(status_counts.values())} attempted records: {status_counts.get('completed', 0)} top-level completed, {status_counts.get('failed', 0)} failed, {status_counts.get('timed_out', 0)} timed out, {status_counts.get('skipped', 0)} skipped, {status_counts.get('invalid', 0)} invalid. The aggregator identifies {len(all_summary.get('record_validation_errors', []))} schema-invalid raw record(s) and excludes them from numerical groups; the original lines remain unchanged. The failed record is the exploratory official-reference request for a valid `s=1` case outside the authors kernel's documented implementation domain; its reason remains in the raw JSONL. Earlier partial runs are retained and separated by source diff/configuration in `all_attempts_summary.json`.

The full planned smoke/scaling/stress matrix was **NOT_RUN**. GPU parity was **NOT_RUN** due no device. No quantum hardware was used. Equation (3)'s two-Toffoli inconsistency remains **UNRESOLVED**; Figure 9's caption inversion is supported by surrounding prose, algorithm description and the authors' Figure 9 source. Details are in `PAPER_INTERPRETATION_AND_DISCREPANCIES.md`.

## Reproduction commands

From repository root:

```bash
PYTHONPATH=candidate_ai/src .venv/bin/python -m pytest -o addopts= -q
PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.runners.environment_probe --machine-id local-sirius-validation --output /tmp/sirius-machine.json
for method in independent_batched_isometry malvetti_baseline end_to_end_state_preparation authors_reference_artifact; do
  PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.runners.run_benchmarks --plan research/phase9_repair/runs/sirius_repair_validation_20261117/matched_smoke_plan.json --tier smoke --methods "$method" --output /tmp/sirius-repro-raw --max-jobs 1
done
PYTHONPATH=candidate_ai/src .venv/bin/python -m benchmarking.analysis.aggregate --input /tmp/sirius-repro-raw --output /tmp/sirius-repro-summary.json
```

The separate GPU attempt adds `--enable-gpu` to the candidate command. Reproduction creates a new run ID and raw records; it does not overwrite existing evidence.

## Release-readiness decision

**RESEARCH_VALIDATION_PARTIALLY_READY.** The order-identity, aggregation, reference counter handling, statevector runner and GPU-lane defects have meaningful repairs and tests. A full benchmark campaign, CUDA execution/parity, broad resource agreement and resolution of the paper's Equation (3) discrepancy remain outstanding. This is not release-ready.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
