#!/usr/bin/env python3
"""Audit one canonical two-track Ubuntu run, including identities and GPU parity flags."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidate_ai/src")); sys.path.insert(0, str(ROOT))
from benchmarking.runners.run_benchmarks import compute_support_hash
from scripts.run_ubuntu_campaign import job_identity
from scripts.summarize_ubuntu_results import load_records

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--machine-id", default="ubuntu-amd-ryzen6600h-rtx3050-laptop")
    args = parser.parse_args()
    root = ROOT / "results/raw" / args.machine_id
    paths = [root / "paper_reproduction" / f"{args.run_id}.jsonl",
             root / "extensions/symmetry_structured_sparse_supports" / f"{args.run_id}.jsonl"]
    rows, schema_errors = load_records(paths)
    errors = list(schema_errors)
    if len(rows) != 62: errors.append({"error": f"expected 62 valid records, got {len(rows)}"})
    ids = [r.get("job_id") for r in rows]
    if len(ids) != len(set(ids)): errors.append({"error": "duplicate job IDs in raw records"})
    plan_path = ROOT / "results/manifests" / args.machine_id / f"{args.run_id}_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        planned = {job_identity(j) for j in plan.get("selected", [])}
        if planned != set(ids): errors.append({"error": "raw job IDs do not exactly match selected manifest jobs"})
    for r in rows:
        if r.get("job") and job_identity(r["job"]) != r.get("job_id"): errors.append({"job_id":r.get("job_id"),"error":"job identity digest mismatch"})
        p = r.get("problem", {}); ident = r.get("input_identity", {})
        support = p.get("support", []); coefficients = p.get("coefficients", []); signs = p.get("signs", [])
        if len(support) != p.get("s") or len(set(support)) != len(support): errors.append({"job_id": r.get("job_id"), "error": "support cardinality/uniqueness mismatch"})
        if any(len(x) != p.get("n") or any(c not in "01" for c in x) for x in support): errors.append({"job_id": r.get("job_id"), "error": "support width/content invalid"})
        if any(sum(int(c) for c in x) != p["k"] for x in support) if p.get("support_family") == "fixed_hamming_weight" else False:
            errors.append({"job_id": r.get("job_id"), "error": "fixed-weight support row outside Omega(n,k)"})
        if len(coefficients) != p.get("s") or len(signs) != p.get("s") or any(x not in (-1,1) for x in signs): errors.append({"job_id": r.get("job_id"), "error": "coefficient/sign vector mismatch"})
        if coefficients and abs(sum(a*a+b*b for a,b in coefficients)-1.0)>1e-9: errors.append({"job_id": r.get("job_id"), "error": "coefficient norm invalid"})
        if support and ident.get("ordered_support_sha256") != compute_support_hash(tuple(support), p["n"]): errors.append({"job_id": r.get("job_id"), "error": "ordered support digest mismatch"})
        payload = {"n":p.get("n"),"support":support,"coefficients":coefficients,"signs":signs}
        od = hashlib.sha256(json.dumps(payload,separators=(",", ":"),allow_nan=False).encode()).hexdigest()
        if ident.get("ordered_input_sha256") != od: errors.append({"job_id":r.get("job_id"),"error":"ordered input digest mismatch"})
        canonical = sorted([[row, coef, sign] for row,coef,sign in zip(support,coefficients,signs)])
        cd = hashlib.sha256(json.dumps({"n":p.get("n"),"states":canonical},separators=(",", ":"),allow_nan=False).encode()).hexdigest()
        if ident.get("canonical_mathematical_instance_sha256") != cd: errors.append({"job_id":r.get("job_id"),"error":"canonical state identity mismatch"})
        if r.get("status") == "completed" and r.get("algorithm_id") in ("independent_batched_isometry", "malvetti_baseline"):
            if not r.get("correctness",{}).get("forward_inverse_and_ancilla_clean"): errors.append({"job_id":r.get("job_id"),"error":"basis-row inverse/clean check missing"})
            if r.get("gpu",{}).get("status") != "passed": errors.append({"job_id":r.get("job_id"),"error":"eligible GPU basis-row parity absent or failed"})
    grouped = {}
    for r in rows:
        p=r.get("problem",{}); key=(r.get("algorithm_id"),p.get("n"),p.get("k"),p.get("s"),r.get("seed"),p.get("support_family"),p.get("ordering"))
        grouped[key]=r
    for r in rows:
        p=r.get("problem",{})
        if p.get("support_family")!="fixed_hamming_weight" or p.get("ordering")!="lexicographic": continue
        key=(r.get("algorithm_id"),p.get("n"),p.get("k"),p.get("s"),r.get("seed"),"fixed_hamming_weight","seeded_shuffled")
        other=grouped.get(key)
        if other:
            if r["input_identity"]["canonical_mathematical_instance_sha256"]!=other["input_identity"]["canonical_mathematical_instance_sha256"]: errors.append({"job_id":r["job_id"],"error":"order pair changed mathematical state"})
            if r["input_identity"]["ordered_input_sha256"]==other["input_identity"]["ordered_input_sha256"]: errors.append({"job_id":r["job_id"],"error":"order pair did not change ordered identity"})
    statuses={s:sum(r.get("status")==s for r in rows) for s in ("completed","failed","skipped","timed_out","invalid")}
    gpu=[r.get("gpu",{}).get("status") for r in rows if r.get("gpu",{}).get("status") is not None]
    result={"run_id":args.run_id,"records":len(rows),"status_counts":statuses,"gpu_stage_counts":{k:gpu.count(k) for k in sorted(set(gpu))},"validation_errors":errors}
    print(json.dumps(result,indent=2))
    return 1 if errors else 0

if __name__=="__main__": raise SystemExit(main())
