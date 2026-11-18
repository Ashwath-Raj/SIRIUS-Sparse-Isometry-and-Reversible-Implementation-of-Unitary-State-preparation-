#!/usr/bin/env python3
"""Validate active Ubuntu laptop and workstation plan invariants."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidate_ai" / "src")); sys.path.insert(0, str(ROOT))
from scripts.run_ubuntu_campaign import build_jobs, MAX_ATTEMPTS
from benchmarking.extensions.symmetry_workloads import fixed_hamming_weight_support

def main() -> int:
    laptop = json.loads((ROOT / "benchmarking/config/ubuntu_laptop_pilot_v1.json").read_text())
    workstation = json.loads((ROOT / "benchmarking/config/ubuntu_workstation_campaign_v1.json").read_text())
    jobs, _ = build_jobs()
    tracks = {t: sum(j["track"] == t for j in jobs) for t in laptop["tracks"]}
    assert len(jobs) <= MAX_ATTEMPTS == laptop["max_combined_attempts"]
    assert tracks == {"paper_reproduction": 14, "symmetry_structured_sparse_supports": 48}, tracks
    ids = [json.dumps(j, sort_keys=True) for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate pilot jobs"
    for job in jobs:
        if job["support_family"] == "fixed_hamming_weight":
            fixed_hamming_weight_support(job["n"], job["k"], job["s"], job["seed"])
        else:
            assert job.get("k") is None
    assert workstation["tracks"]["paper_reproduction"]["unchanged"] is True
    print(f"Ubuntu plan validation: PASS; pilot attempts={len(jobs)}; tracks={tracks}; workstation plan loaded (definition only)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
