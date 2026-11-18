from __future__ import annotations

import json
from pathlib import Path
import tempfile

from scripts.run_ubuntu_campaign import build_jobs, collect_completed_job_ids, job_identity, select_stratified_jobs


def test_default_pilot_is_bounded_separate_and_stratified():
    jobs, _ = build_jobs()
    assert len(jobs) == 62 <= 64
    assert sum(j["track"] == "paper_reproduction" for j in jobs) == 14
    assert sum(j["track"] == "symmetry_structured_sparse_supports" for j in jobs) == 48
    selected = select_stratified_jobs(jobs, 62, 19)
    assert selected == select_stratified_jobs(jobs, 62, 19)
    assert {j["track"] for j in selected} == {"paper_reproduction", "symmetry_structured_sparse_supports"}
    assert len({job_identity(j) for j in selected}) == 62
    assert {j.get("ordering") for j in selected if j["track"] == "symmetry_structured_sparse_supports"} == {"lexicographic", "seeded_shuffled"}


def test_truncated_selection_round_robins_strata_and_is_deterministic():
    jobs, _ = build_jobs()
    a = select_stratified_jobs(jobs, 32, 2026)
    b = select_stratified_jobs(jobs, 32, 2026)
    assert a == b
    assert len(a) == 32
    assert len({job_identity(j) for j in a}) == 32
    assert {j["track"] for j in a} == {"paper_reproduction", "symmetry_structured_sparse_supports"}
    assert len({(j["track"], j["algorithm_id"], j["n"], j["s"], j["support_family"], j.get("ordering")) for j in a}) >= 24


def test_resume_reads_job_ids_without_repeating_or_rewriting_records():
    job = build_jobs()[0][0]
    record = {"job_id": job_identity(job), "status": "failed"}
    with tempfile.TemporaryDirectory() as temp:
        raw = Path(temp) / "run.jsonl"
        raw.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\nnot-json\n")
        before = raw.read_bytes()
        completed = collect_completed_job_ids([raw])
        assert completed == {job_identity(job)}
        assert raw.read_bytes() == before

