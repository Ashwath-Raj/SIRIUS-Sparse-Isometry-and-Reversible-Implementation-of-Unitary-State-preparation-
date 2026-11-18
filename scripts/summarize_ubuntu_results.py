#!/usr/bin/env python3
"""Validate and summarize canonical per-machine Ubuntu raw result lanes."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "benchmarking/schemas/ubuntu-attempt.schema.json"
PLAN_ID = "sirius-ubuntu-laptop-pilot-v1"


def load_records(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    import jsonschema
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    rows, invalid = [], []
    for path in paths:
        for line_no, line in enumerate(path.read_text().splitlines(), 1):
            try:
                row = json.loads(line)
                errs = [e.message for e in validator.iter_errors(row)]
                if errs:
                    invalid.append({"path": str(path), "line": line_no, "errors": errs})
                else:
                    rows.append(row)
            except Exception as exc:
                invalid.append({"path": str(path), "line": line_no, "errors": [f"{type(exc).__name__}: {exc}"]})
    return rows, invalid


def summarize_track(rows: list[dict], track: str, base: Path) -> dict:
    selected = [r for r in rows if r.get("track") == track]
    counts = Counter(r.get("status", "invalid") for r in selected)
    gpu_counts = Counter(r.get("gpu", {}).get("status", "not_requested") for r in selected)
    exact_counts = Counter(r.get("correctness", {}).get("statevector_status", "not_run") for r in selected)
    valid = [r for r in selected if r.get("status") == "completed"]
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    if track == "paper_reproduction":
        keys = ("algorithm_id", "n", "s", "support_family", "coefficient_family", "sign_profile")
    else:
        keys = ("algorithm_id", "n", "k", "s", "support_family", "ordering", "coefficient_family", "sign_profile")
    for row in valid:
        problem = row.get("problem", {})
        grouped[tuple(row.get(k, problem.get(k)) for k in keys)].append(row)
    metric_rows = []
    for group_key, group in sorted(grouped.items(), key=lambda x: str(x[0])):
        metrics = {}
        for metric, getter in (
            ("construction_wall_ms", lambda r: r.get("timings", {}).get("construction_wall_ms")),
            ("paper_accounted_toffoli", lambda r: r.get("resources", {}).get("paper_accounted_toffoli")),
            ("coherent_toffoli", lambda r: r.get("resources", {}).get("coherent_toffoli")),
            ("emitted_operation_count", lambda r: r.get("resources", {}).get("emitted_operation_count")),
            ("peak_process_rss_bytes", lambda r: r.get("timings", {}).get("peak_process_rss_bytes")),
            ("gpu_kernel_ms", lambda r: r.get("gpu", {}).get("gpu_kernel_ms")),
        ):
            values = [float(v) for row in group if isinstance((v := getter(row)), (int, float))]
            metrics[metric] = {"sample_count": len(values), "median": statistics.median(values) if values else None,
                               "mean": statistics.mean(values) if values else None,
                               "minimum": min(values) if values else None, "maximum": max(values) if values else None,
                               "standard_deviation": statistics.stdev(values) if len(values) > 1 else None,
                               "uncertainty_interval": None if len(values) < 5 else None}
        metric_rows.append({**dict(zip(keys, group_key)), "attempt_count": len(group), "distinct_seed_count": len({r["seed"] for r in group}), "metrics": metrics})
    return {"track": track, "machine_id": selected[0].get("machine_id") if selected else None,
            "attempt_count": len(selected), "status_counts": {s: counts.get(s, 0) for s in ("completed", "failed", "skipped", "timed_out", "invalid")},
            "gpu_lane_status_counts": dict(gpu_counts), "statevector_status_counts": dict(exact_counts),
            "completed_measurements_only": True, "grouping_keys": list(keys), "groups": metric_rows}


def write_csv(path: Path, records: list[dict], track: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["track", "run_id", "job_id", "algorithm_id", "status", "n", "k", "s", "seed", "support_family", "ordering",
               "canonical_mathematical_instance_sha256", "ordered_input_sha256", "paper_accounted_toffoli", "coherent_toffoli",
               "emitted_operation_count", "construction_wall_ms", "construction_process_cpu_ms", "peak_process_rss_bytes", "gpu_status",
               "gpu_kernel_ms", "gpu_basis_batch_wall_ms", "correctness_summary", "failure_reason"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in records:
            if row.get("track") != track:
                continue
            problem, resources, times, correctness, gpu = row.get("problem", {}), row.get("resources", {}), row.get("timings", {}), row.get("correctness", {}), row.get("gpu", {})
            writer.writerow({"track": track, "run_id": row.get("run_id"), "job_id": row.get("job_id"), "algorithm_id": row.get("algorithm_id"), "status": row.get("status"),
                "n": problem.get("n"), "k": problem.get("k"), "s": problem.get("s"), "seed": row.get("seed"), "support_family": problem.get("support_family"), "ordering": problem.get("ordering"),
                "canonical_mathematical_instance_sha256": row.get("input_identity", {}).get("canonical_mathematical_instance_sha256"),
                "ordered_input_sha256": row.get("input_identity", {}).get("ordered_input_sha256"), "paper_accounted_toffoli": resources.get("paper_accounted_toffoli"),
                "coherent_toffoli": resources.get("coherent_toffoli"), "emitted_operation_count": resources.get("emitted_operation_count"),
                "construction_wall_ms": times.get("construction_wall_ms"), "construction_process_cpu_ms": times.get("construction_process_cpu_ms"),
                "peak_process_rss_bytes": times.get("peak_process_rss_bytes"), "gpu_status": gpu.get("status"), "gpu_kernel_ms": gpu.get("gpu_kernel_ms"),
                "gpu_basis_batch_wall_ms": gpu.get("gpu_basis_batch_wall_ms"), "correctness_summary": json.dumps(correctness, sort_keys=True), "failure_reason": row.get("failure_reason")})


def write_symmetry_contrasts(path: Path, records: list[dict]) -> None:
    """Emit per-seed matched contrasts; no independent timer subsamples are used."""
    rows = [r for r in records if r.get("track") == "symmetry_structured_sparse_supports" and r.get("status") == "completed"]
    ix = {}
    for row in rows:
        p = row["problem"]
        key = (row["algorithm_id"], p["n"], p["k"], p["s"], row["seed"], p["coefficient_family"], p["sign_profile"], p["ordering"])
        ix[(key, p["support_family"])] = row
    fields = ["contrast", "algorithm_id", "n", "k", "s", "seed", "left_ordered_sha256", "right_ordered_sha256",
              "same_canonical_instance", "left_value", "right_value", "difference_right_minus_left", "ratio_right_over_left", "metric"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for (key, family), left in sorted(ix.items(), key=lambda x: str(x[0])):
            if family != "seeded_random": continue
            alg, n, k, s, seed, coeff, sign, order = key
            right = next((r for r in rows if r.get("algorithm_id") == alg and r.get("seed") == seed
                          and r.get("problem", {}).get("n") == n and r.get("problem", {}).get("k") == k and r.get("problem", {}).get("s") == s
                          and r.get("problem", {}).get("support_family") == "fixed_hamming_weight"
                          and r.get("problem", {}).get("ordering") == order
                          and r.get("problem", {}).get("coefficient_family") == coeff
                          and r.get("problem", {}).get("sign_profile") == sign), None)
            if right:
                for metric, getter in (("construction_wall_ms", lambda r: r.get("timings", {}).get("construction_wall_ms")),
                                       ("paper_accounted_toffoli", lambda r: r.get("resources", {}).get("paper_accounted_toffoli")),
                                       ("coherent_toffoli", lambda r: r.get("resources", {}).get("coherent_toffoli"))):
                    a, b = getter(left), getter(right)
                    if isinstance(a, (int,float)) and isinstance(b, (int,float)):
                        writer.writerow({"contrast": "random_vs_fixed_hamming_weight", "algorithm_id": alg, "n": n, "k": right.get("problem", {}).get("k"), "s": s, "seed": seed,
                            "left_ordered_sha256": left.get("input_identity", {}).get("ordered_input_sha256"), "right_ordered_sha256": right.get("input_identity", {}).get("ordered_input_sha256"),
                            "same_canonical_instance": left.get("input_identity", {}).get("canonical_mathematical_instance_sha256") == right.get("input_identity", {}).get("canonical_mathematical_instance_sha256"),
                            "left_value": a, "right_value": b, "difference_right_minus_left": b-a, "ratio_right_over_left": b/a if a else None, "metric": metric})
        for left in rows:
            p = left["problem"]
            if p.get("support_family") != "fixed_hamming_weight" or p.get("ordering") != "lexicographic": continue
            right = next((r for r in rows if r.get("algorithm_id") == left.get("algorithm_id") and r.get("seed") == left.get("seed")
                          and r.get("problem", {}).get("n") == p.get("n") and r.get("problem", {}).get("k") == p.get("k")
                          and r.get("problem", {}).get("s") == p.get("s") and r.get("problem", {}).get("support_family") == "fixed_hamming_weight"
                          and r.get("problem", {}).get("ordering") == "seeded_shuffled"))
            if not right: continue
            for metric, getter in (("construction_wall_ms", lambda r: r.get("timings", {}).get("construction_wall_ms")),
                                   ("paper_accounted_toffoli", lambda r: r.get("resources", {}).get("paper_accounted_toffoli")),
                                   ("coherent_toffoli", lambda r: r.get("resources", {}).get("coherent_toffoli"))):
                a, b = getter(left), getter(right)
                if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                    writer.writerow({"contrast":"lexicographic_vs_seeded_shuffled", "algorithm_id":left.get("algorithm_id"), "n":p.get("n"), "k":p.get("k"), "s":p.get("s"), "seed":left.get("seed"),
                        "left_ordered_sha256":left.get("input_identity",{}).get("ordered_input_sha256"), "right_ordered_sha256":right.get("input_identity",{}).get("ordered_input_sha256"),
                        "same_canonical_instance":left.get("input_identity",{}).get("canonical_mathematical_instance_sha256")==right.get("input_identity",{}).get("canonical_mathematical_instance_sha256"),
                        "left_value":a,"right_value":b,"difference_right_minus_left":b-a,"ratio_right_over_left":b/a if a else None,"metric":metric})


def make_figures(records: list[dict], track: str, output_dir: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    rows = [r for r in records if r.get("track") == track and r.get("status") == "completed"]
    paths = []
    if track == "symmetry_structured_sparse_supports":
        groups = defaultdict(list)
        for row in rows:
            p, t = row.get("problem", {}), row.get("timings", {})
            val = t.get("construction_wall_ms")
            if val is not None:
                cond = f"n={p.get('n')}, s={p.get('s')}\n{p.get('support_family')}\n{p.get('ordering')}"
                groups[(row["algorithm_id"], cond)].append(float(val))
        fig, ax = plt.subplots(figsize=(10, 5))
        labels = sorted({x[1] for x in groups})
        algs = sorted({x[0] for x in groups})
        positions = range(len(labels))
        for ai, alg in enumerate(algs):
            xs, ys = [], []
            for i, label in enumerate(labels):
                vals = groups.get((alg, label), [])
                xs.extend([i + (ai - (len(algs)-1)/2)*0.12] * len(vals)); ys.extend(vals)
            ax.scatter(xs, ys, label=alg, alpha=0.85)
        ax.set_xticks(list(positions), labels, rotation=0)
        ax.set_ylabel("Construction wall time (ms)"); ax.set_title("Symmetry extension pilot: per-attempt construction observations")
        ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25); fig.tight_layout()
        p = output_dir / "construction_wall_ms_by_support_condition.png"; fig.savefig(p, dpi=160); plt.close(fig); paths.append(str(p))
        fig, ax = plt.subplots(figsize=(9, 5))
        conditions = sorted({(r.get("problem", {}).get("n"), r.get("problem", {}).get("s"), r.get("problem", {}).get("support_family"), r.get("problem", {}).get("ordering")) for r in rows})
        for ai, alg in enumerate(algs):
            for ci, cond in enumerate(conditions):
                vals = [r["resources"].get("paper_accounted_toffoli") for r in rows if r["algorithm_id"] == alg and tuple(r.get("problem", {}).get(k) for k in ("n", "s", "support_family", "ordering")) == cond and isinstance(r.get("resources", {}).get("paper_accounted_toffoli"), (int,float))]
                ax.scatter([ci + (ai-(len(algs)-1)/2)*.12]*len(vals), vals, label=alg if ci == 0 else None, alpha=.8)
        labels = [f"n={n},s={s}\n{family}\n{order}" for n,s,family,order in conditions]
        ax.set_xticks(range(len(conditions)), labels, rotation=45, ha="right"); ax.set_ylabel("Paper-accounted Toffoli count"); ax.set_title("Symmetry extension pilot: logical cost by matched dimensions and support condition")
        ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25); fig.tight_layout()
        p = output_dir / "paper_toffoli_by_support_family.png"; fig.savefig(p, dpi=160); plt.close(fig); paths.append(str(p))
    else:
        groups = defaultdict(list)
        for row in rows:
            value = row.get("timings", {}).get("construction_wall_ms")
            if value is not None: groups[row["algorithm_id"]].append(float(value))
        fig, ax = plt.subplots(figsize=(8, 5))
        for i, (alg, values) in enumerate(sorted(groups.items())): ax.scatter([i]*len(values), values, label=f"{alg} (n={len(values)})")
        ax.set_xticks(range(len(groups)), list(sorted(groups)), rotation=15); ax.set_ylabel("Construction wall time (ms)")
        ax.set_title("Paper reproduction pilot observations; one measurement per job"); ax.grid(axis="y", alpha=.25); ax.legend(fontsize=8); fig.tight_layout()
        p = output_dir / "construction_wall_ms_by_algorithm.png"; fig.savefig(p, dpi=160); plt.close(fig); paths.append(str(p))
    return paths


def build_research_pilot_report(records: list[dict], manifest: dict, run_id: str, validation: dict[str, list[dict]]) -> str:
    paper = [r for r in records if r.get("track") == "paper_reproduction"]
    symmetry = [r for r in records if r.get("track") == "symmetry_structured_sparse_supports"]
    def cell(x): return "—" if x is None else str(x)
    def table(headers, rows):
        return "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + "\n".join("| " + " | ".join(map(cell, row)) + " |" for row in rows)
    aindex = {(r.get("algorithm_id"), r.get("problem", {}).get("n"), r.get("problem", {}).get("s"), r.get("seed")): r for r in paper}
    paper_rows = []
    for n in (8, 10):
        for s in (3, 5):
            for alg in ("independent_batched_isometry", "malvetti_baseline"):
                r = aindex.get((alg, n, s, 101))
                if not r: continue
                p = r["problem"]; res = r.get("resources", {}); timing = r.get("timings", {})
                paper_rows.append([n, s, alg, 101, f"{timing.get('construction_wall_ms', 0):.6f}", res.get("paper_accounted_toffoli"),
                                   res.get("coherent_toffoli"), res.get("emitted_operation_count"), r.get("gpu", {}).get("status")])
    contrast_path = ROOT / "results/tables" / manifest["machine_id"] / "extensions/symmetry_structured_sparse_supports" / f"{run_id}_matched_contrasts.csv"
    paired = defaultdict(list)
    if contrast_path.exists():
        for row in csv.DictReader(contrast_path.open()):
            paired[(row["contrast"], row["algorithm_id"], row["n"], row["k"], row["s"], row["metric"])].append(float(row["difference_right_minus_left"]))
    contrast_rows = [[*key, len(values), f"{statistics.median(values):.6f}"] for key, values in sorted(paired.items())]
    gpu_rows = []
    for label, subset in (("paper_reproduction", paper), ("symmetry_structured_sparse_supports", symmetry)):
        g = [r.get("gpu", {}) for r in subset if r.get("gpu", {}).get("status") is not None]
        times = [x["gpu_kernel_ms"] for x in g if isinstance(x.get("gpu_kernel_ms"), (int,float))]
        gpu_rows.append([label, len(g), dict(Counter(x.get("status") for x in g)), len(times), f"{statistics.median(times):.6f}" if times else "—"])
    end = next((r for r in paper if r.get("algorithm_id") == "end_to_end_state_preparation"), {})
    authors = next((r for r in paper if r.get("algorithm_id") == "authors_reference_artifact"), {})
    sw = manifest.get("software", {})
    gpu = manifest.get("gpu_devices", [{}])[0] if manifest.get("gpu_devices") else {}
    timestamps = sorted(r.get("started_at_utc") for r in records if r.get("started_at_utc"))
    finishes = sorted(r.get("ended_at_utc") for r in records if r.get("ended_at_utc"))
    return f"""# Ubuntu RTX 3050 Pilot Report

## Run identity and machine

- Run label: `{run_id}` (the suffix is an opaque label, not a timestamp); plan: `{PLAN_ID}` version 1.0.0.
- Actual record interval (UTC): `{timestamps[0] if timestamps else 'unavailable'}` through `{finishes[-1] if finishes else 'unavailable'}`.
- Git HEAD: `{sw.get('git')}`; the working tree was dirty during the pilot. Raw records capture the dirty flag but not a source-diff digest/snapshot, so the exact as-run patch cannot be reconstructed from this pilot evidence alone. The runner now records source diff and untracked-file digests for future runs. The per-run plan and machine manifest are adjacent under `results/manifests/{manifest['machine_id']}/`.
- OS: {manifest['os']['name']} {manifest['os']['version']}; kernel `{manifest['os']['kernel']}`.
- Python: {manifest['python']['version']}; CPU: {manifest['cpu']['model']} ({manifest['cpu']['physical_cores']} physical / {manifest['cpu']['logical_cores']} logical cores).
- RAM: {manifest['memory']['ram_total_bytes']} total bytes; swap: {manifest['memory']['swap_total_bytes']} bytes.
- GPU: {gpu.get('name')} ({gpu.get('memory_bytes')} bytes; compute capability {gpu.get('compute_capability')}); driver {sw.get('nvidia_driver')}; CUDA compatibility from `nvidia-smi`: {sw.get('cuda_driver_compatibility')}; CuPy runtime {sw.get('cuda_runtime')}; CuPy {sw.get('cupy')}; local `nvcc` toolkit: {sw.get('cuda_toolkit')}.

## Attempt and validation results

| Track | Attempts | Completed | Failed | Skipped | Timed out | Invalid | Schema-invalid lines |
|---|---:|---:|---:|---:|---:|---:|---:|
| Paper reproduction | {len(paper)} | {sum(r.get('status')=='completed' for r in paper)} | {sum(r.get('status')=='failed' for r in paper)} | {sum(r.get('status')=='skipped' for r in paper)} | {sum(r.get('status')=='timed_out' for r in paper)} | {sum(r.get('status')=='invalid' for r in paper)} | {len(validation['paper_reproduction'])} |
| Symmetry extension | {len(symmetry)} | {sum(r.get('status')=='completed' for r in symmetry)} | {sum(r.get('status')=='failed' for r in symmetry)} | {sum(r.get('status')=='skipped' for r in symmetry)} | {sum(r.get('status')=='timed_out' for r in symmetry)} | {sum(r.get('status')=='invalid' for r in symmetry)} | {len(validation['symmetry_structured_sparse_supports'])} |

Seeds: 101 and 211. Widths: n=8,10. Sparsities: s=3,5. The symmetry track used k=n//2, random support, fixed-weight lexicographic support, and fixed-weight seeded-shuffled support. Algorithms were the independent batched-isometry implementation and Malvetti baseline. One end-to-end statevector and one authors-reference run were added in the paper track. The selected design consumed 62/64 allowed attempts.

## Paper reproduction observations

The table reports seed-101 matched candidate and Malvetti construction runs. Construction wall time is one in-process compilation measurement; values are workload-specific and are not a significance test. Resource conventions remain distinct; operation count is not depth.

{table(['n','s','Algorithm','Seed','Construction wall ms','Paper-accounted Toffoli','Coherent Toffoli','Emitted operations','GPU lane'], paper_rows)}

End-to-end exact CPU statevector status: `{end.get('correctness',{}).get('statevector_status')}`; fidelity `{end.get('correctness',{}).get('fidelity')}`, maximum amplitude error `{end.get('correctness',{}).get('maximum_amplitude_error')}`, workspace leakage `{end.get('correctness',{}).get('workspace_leakage_probability')}`. Authors reference status: `{authors.get('resources',{}).get('reference_status')}`; mapping total/injective/row-total checks: `{authors.get('correctness')}`. The authors API does not expose primitive gates or residual-row output for independent gate-sequence comparison.

## Symmetry extension paired contrasts

Contrasts below are right-minus-left deltas computed per matched seed, then summarized by the median of the two seed differences for each (n,k,s,algorithm,metric). For family comparisons, random and fixed-weight workloads share dimension, seed strategy, and coefficient/sign generation profile, but are distinct supports and states. For order comparisons, canonical support/amplitude/sign mappings match exactly. `n=2` seed pairs are descriptive and have no confidence intervals.

{table(['Contrast','Algorithm','n','k','s','Metric','Paired seeds','Median delta'], contrast_rows)}

Observed median deltas vary across width/sparsity and algorithm. The pilot does not establish a general geometry effect or ordering benefit. Prefix and Hamming descriptors and all per-attempt values are in raw records/CSV; the figures visualize individual completed observations.

## GPU basis-row lane

{table(['Track','GPU stages','Status counts','Kernel samples','Median measured kernel ms'], gpu_rows)}

All GPU stages applied actual emitted reversible gates to uint64 computational-basis rows and checked exact output parity against the CPU basis-row simulator. This is not GPU circuit construction, complex-amplitude statevector simulation, or hardware execution. Per-job intervals are a single synchronized observation; the first CuPy use can include JIT/cache warm-up, so kernel timings are exploratory and no throughput or speedup claim is made.

## Evidence paths and rerun

- Paper raw: `results/raw/{manifest['machine_id']}/paper_reproduction/{run_id}.jsonl`
- Symmetry raw: `results/raw/{manifest['machine_id']}/extensions/symmetry_structured_sparse_supports/{run_id}.jsonl`
- Machine and plan manifests: `results/manifests/{manifest['machine_id']}/{run_id}_machine_manifest.json`, `{run_id}_plan.json`.
- CSV tables and matched contrasts: `results/tables/{manifest['machine_id']}/.../{run_id}_attempts.csv` and `{run_id}_matched_contrasts.csv`.
- Figures, logs, summaries, checkpoints and per-track reports: matching `results/figures`, `results/logs`, `results/summaries`, `results/checkpoints`, `results/reports` machine/track directories.

```bash
SIRIUS_PYTHON="$PWD/.venv-ubuntu-3.12/bin/python" SIRIUS_RUN_ID="new-unique-run-id" bash scripts/ubuntu/run_laptop_pilot.sh
PYTHONPATH=candidate_ai/src .venv-ubuntu-3.12/bin/python scripts/summarize_ubuntu_results.py --run-id new-unique-run-id
```

Full Phase 9.1 scaling/stress and the larger symmetry workstation campaign were **NOT_RUN** on this laptop. The full campaign definitions remain separate in `benchmarking/config/phase9_1_benchmark_plan.json` and `benchmarking/config/ubuntu_workstation_campaign_v1.json`.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-id", default="ubuntu-amd-ryzen6600h-rtx3050-laptop")
    parser.add_argument("--results-root", type=Path, default=ROOT / "results")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    base = args.results_root
    files = {
        "paper_reproduction": base / "raw" / args.machine_id / "paper_reproduction" / f"{args.run_id}.jsonl",
        "symmetry_structured_sparse_supports": base / "raw" / args.machine_id / "extensions" / "symmetry_structured_sparse_supports" / f"{args.run_id}.jsonl",
    }
    existing = {k: [v] if v.exists() else [] for k,v in files.items()}
    for track, paths in existing.items():
        rows, invalid = load_records(paths)
        summary = summarize_track(rows, track, base)
        summary["invalid_lines"] = invalid
        outdirs = {
            "paper_reproduction": base / "summaries" / args.machine_id / "paper_reproduction",
            "symmetry_structured_sparse_supports": base / "summaries" / args.machine_id / "extensions" / "symmetry_structured_sparse_supports",
        }
        outdir = outdirs[track]; outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f"{args.run_id}_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        table_dir = base / "tables" / args.machine_id / ("paper_reproduction" if track == "paper_reproduction" else "extensions/symmetry_structured_sparse_supports")
        write_csv(table_dir / f"{args.run_id}_attempts.csv", rows, track)
        if track == "symmetry_structured_sparse_supports":
            write_symmetry_contrasts(table_dir / f"{args.run_id}_matched_contrasts.csv", rows)
        figure_dir = base / "figures" / args.machine_id / ("paper_reproduction" if track == "paper_reproduction" else "extensions/symmetry_structured_sparse_supports")
        figure_dir.mkdir(parents=True, exist_ok=True)
        figures = make_figures(rows, track, figure_dir)
        report_dir = base / "reports" / args.machine_id / ("paper_reproduction" if track == "paper_reproduction" else "extensions/symmetry_structured_sparse_supports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report = [f"# {track.replace('_', ' ').title()} Pilot Report", "", f"Run: `{args.run_id}`", f"Machine: `{args.machine_id}`", "",
                  "This bounded pilot is descriptive only. No statistical significance or general speedup is claimed.", "",
                  f"Attempt statuses: `{json.dumps(summary['status_counts'], sort_keys=True)}`.",
                  f"Schema-invalid lines: {len(invalid)}.", f"Completed summary groups: {len(summary['groups'])}.", "",
                  "Performance summaries use completed jobs only. Failed, skipped, timed-out and invalid attempts remain counted in raw records.", "",
                  "The small pilot has two independent seeds for most extension strata; confidence intervals are not reported because replication is insufficient.", "",
                  "## Figures", "", *([f"- `{p}`" for p in figures] or ["- No figures generated (matplotlib unavailable or no completed measurements)."]), "",
                  "## Summary statistics", "", "See the machine-specific JSON summary and CSV attempts table. Resource metrics preserve paper-accounted Toffoli, coherent Toffoli, emitted operation count and timing as separate quantities.", ""]
        (report_dir / f"{args.run_id}_report.md").write_text("\n".join(report))
        print(f"{track}: attempts={summary['attempt_count']} statuses={summary['status_counts']} invalid_lines={len(invalid)} groups={len(summary['groups'])}")
        for key, path in (("summary", outdir / f"{args.run_id}_summary.json"), ("csv", table_dir / f"{args.run_id}_attempts.csv"), ("report", report_dir / f"{args.run_id}_report.md")):
            print(f"{key}: {path}")
        for path in figures: print(f"figure: {path}")
        if invalid: print(json.dumps(invalid, indent=2), file=sys.stderr)
    all_rows, invalid_by_file = load_records([p for group in existing.values() for p in group])
    manifest_path = base / "manifests" / args.machine_id / f"{args.run_id}_machine_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    invalid_by_track = {track: [e for e in invalid_by_file if e["path"].endswith(track + f"/{args.run_id}.jsonl")] for track in files}
    report = build_research_pilot_report(all_rows, manifest, args.run_id, invalid_by_track)
    research_report = ROOT / "docs/research/UBUNTU_3050_PILOT_REPORT.md"
    research_report.write_text(report)
    print(f"research report: {research_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
